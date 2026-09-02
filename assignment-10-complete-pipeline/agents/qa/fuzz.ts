/**
 * The headless half of the adversarial agent: it drives the CORE directly,
 * flat out, doing things a player would never do.
 *
 * Why a second surface at all, when the browser agent already plays the real
 * game? Throughput and reach. A browser click costs ~50ms and a wave costs
 * seconds, so a five-minute browser session sees a handful of waves; this loop
 * sees hundreds of runs and tens of thousands of hostile calls in the same time,
 * and it can reach wave 20 — where bosses unravel the loom and the market deals
 * high tiers — which is where the interesting state lives. The browser agent
 * proves a break is reachable by a real player; this one finds it.
 *
 * The strategy is not "call random methods". It is a set of named ATTACKS, each
 * aimed at a specific way this game has historically broken:
 *
 *   banish_storm      parallel arrays (offers / offerTiers) drifting apart
 *   scrap_loop        an income stream that bypasses combat
 *   hand_churn        placement legality under lift/rotate/drop at the edges
 *   merge_storm       tier ceilings and identity under forced merges
 *   expansion_abuse   the loom growing outside its envelope
 *   economy_drain     negative gold, free rerolls, upgrade caps
 *   phase_confusion   out-of-order transitions a stale UI handler could cause
 *   ult_spam          the one live input, pressed every single tick
 *   offer_index_abuse out-of-range and non-integer indices into the market
 *
 * After every attack the oracle reads the state. Nothing here decides what is
 * broken — oracle.ts does, and the browser agent is judged by the same laws.
 */
import { BUFFS, TICK_HZ, type BuffDef } from "../../core/content.js";
import { Run, UPGRADES } from "../../core/run.js";
import { Rng } from "../../core/rng.js";
import type { ClassId } from "../../core/grid.js";
import { Hand } from "../../game/hand.js";
import { playBuff, playExpansion, playMarket, playUlt } from "../../sim/policy.js";
import { contextFrom, type FindingLog } from "./report.js";
import { inspect, type Snapshot, type Violation } from "./oracle.js";

const CLASSES: ClassId[] = ["hunter", "titan", "warden"];

/**
 * What the renderer's tray can actually show. The core's `toTray` takes the
 * capacity as an argument rather than owning it, so the agent has to supply a
 * realistic one — feeding it `true` forever would manufacture a tray state no
 * player can reach, and a finding no player can hit is noise.
 */
const TRAY_CAPACITY = 5;

export function snapshotRun(run: Run, hand: Hand | null): Snapshot {
  const b = run.battle;
  return {
    phase: run.phase,
    wave: run.wave,
    gold: run.gold,
    exp: run.exp,
    level: run.level,
    beaconHp: run.beaconHp,
    beaconMax: run.beaconMax,
    freeRerolls: run.freeRerolls,
    rerollsUsed: run.rerollsUsed,
    pendingBuffChoices: run.pendingBuffChoices,
    pendingExpansionCells: run.pendingExpansionCells,
    cls: run.cls,
    env: { w: run.env.w, h: run.env.h },
    unlocked: [...run.loom.unlocked],
    relics: run.loom.relics.map((r) => ({
      uid: r.uid, defId: r.defId, tier: r.tier,
      cells: r.cells.map(([x, y]) => [x, y] as [number, number]),
      cooldownLeft: r.cooldownLeft,
    })),
    tray: run.tray.map((t) => ({ defId: t.defId, tier: t.tier })),
    offers: run.offers.map((o) => o.id),
    offerTiers: [...run.offerTiers],
    deals: run.deals,
    removed: [...run.removed],
    buffs: run.buffs.length,
    // Only read on the screen that shows them: `buffChoices()` deals the three
    // cards on first call, so asking from any other phase would deal them early
    // and change the run the agent is supposed to be observing.
    buffChoiceIds: run.phase === "buff" ? run.buffChoices().map((x) => x.id) : [],
    handDefId: hand?.held?.def.id ?? null,
    battle: b ? {
      elapsed: b.elapsed,
      beaconHp: b.beaconHp,
      enemies: b.enemies.map((e) => ({
        id: e.id, kind: e.kind, hp: e.hp, maxHp: e.maxHp,
        pos: e.pos, x: e.x, stopAt: e.stopAt,
      })),
      finished: b.finished
        ? { cleared: b.finished.cleared, goldEarned: b.finished.goldEarned,
            expEarned: b.finished.expEarned }
        : null,
      ultCooldownLeft: b.ultCooldownLeft,
      ultCasts: b.ultCasts,
    } : null,
  };
}

/**
 * Two ways to be adversarial, and the agent needs both.
 *
 * `hostile` wrecks the board on purpose — force-merging everything, scrapping
 * every offer, dropping relics at the edges. It finds breaks fast but it also
 * kills the run fast, so it never sees past about wave 12.
 *
 * `deep` packs the loom competently and only harasses the parts of the game
 * that do not depend on playing badly (banishing, out-of-range indices,
 * out-of-order transitions, the ultimate mashed every tick). That is the only
 * way to reach wave 20+, where the Disruptor unravels the loom mid-battle,
 * where the market deals Purples and Epics, and where a merged board is one
 * relic away from a dead end.
 */
type Mode = "hostile" | "deep";

interface Session {
  run: Run;
  hand: Hand;
  seed: number;
  cls: ClassId;
  mode: Mode;
  rng: Rng;
  trace: string[];
  prev: Snapshot | null;
  deepest: number;
}

export interface FuzzResult { steps: number; runs: number; deepestWave: number }

export class CoreFuzzer {
  private steps = 0;
  private runs = 0;
  private deepestWave = 0;

  constructor(private readonly log: FindingLog, private readonly verbose = false) {}

  /** Run until the wall-clock budget is spent. */
  sweep(seconds: number, seedBase = 7000): FuzzResult {
    const until = Date.now() + seconds * 1000;
    for (let i = 0; Date.now() < until; i++) {
      // One deep run in four: enough late-game coverage without giving up the
      // volume the hostile mode buys.
      this.session(seedBase + i, CLASSES[i % CLASSES.length]!, until,
                   i % 4 === 3 ? "deep" : "hostile");
      this.runs++;
    }
    return { steps: this.steps, runs: this.runs, deepestWave: this.deepestWave };
  }

  // -- one hostile run ------------------------------------------------------

  private session(seed: number, cls: ClassId, until: number, mode: Mode): void {
    const run = new Run(cls, seed);
    const s: Session = {
      run, hand: new Hand(run),
      seed, cls, mode, rng: new Rng(seed ^ 0x5eed), trace: [], prev: null, deepest: 0,
    };
    s.trace.push(`new Run("${cls}", ${seed})  [${mode}]`);

    for (let step = 0; step < 1200; step++) {
      if (Date.now() > until) return;
      if (s.run.phase === "over") return;
      this.steps++;
      if (s.run.wave > this.deepestWave) this.deepestWave = s.run.wave;

      switch (s.run.phase) {
        case "market":    this.attackMarket(s); break;
        case "buff":      this.attackBuff(s); break;
        case "expansion": this.attackExpansion(s); break;
        case "battle":    this.driveBattle(s); break;
        default:          this.act(s, "settlePhase()", () => s.run.settlePhase());
      }
      this.check(s, "mixed");
    }
  }

  // -- the attacks ----------------------------------------------------------

  private attackMarket(s: Session): void {
    const pick = s.rng.next();

    if (s.mode === "deep") {
      // Everything here leaves the board playable. A deep run that gets its
      // loom shredded is just a hostile run that took longer to die.
      if (pick < 0.30) this.banishStorm(s);
      else if (pick < 0.50) this.offerIndexAbuse(s);
      else if (pick < 0.65) this.phaseConfusion(s);
      else if (pick < 0.80) this.expansionAbuse(s);
    } else if (pick < 0.18) this.banishStorm(s);
    else if (pick < 0.30) this.offerIndexAbuse(s);
    else if (pick < 0.44) this.handChurn(s);
    else if (pick < 0.54) this.mergeStorm(s);
    else if (pick < 0.64) this.economyDrain(s);
    else if (pick < 0.72) this.scrapLoop(s);
    else if (pick < 0.78) this.phaseConfusion(s);
    else if (pick < 0.84) this.expansionAbuse(s);

    // Always leave the market by fighting, or the run never deepens and the
    // whole late game — bosses, unravelling, high-tier offers — goes untested.
    this.act(s, "playMarket(competent)", () => playMarket(s.run, "competent"));
    this.check(s, "market");
    this.act(s, "hand.cancel()", () => s.hand.cancel());
    this.act(s, "startBattle()", () => { s.run.startBattle(); });
  }

  /**
   * Banish offers, then take what is left. Banishing removes a card from the
   * shelf mid-market, which is the one operation that can shorten `offers`
   * without going through the market's own take/tray/scrap paths.
   */
  private banishStorm(s: Session): void {
    const n = 1 + Math.floor(s.rng.next() * 2);
    for (let i = 0; i < n; i++) {
      if (s.run.offers.length <= 1) break;
      const idx = Math.floor(s.rng.next() * s.run.offers.length);
      const def = s.run.offers[idx];
      if (!def) break;
      this.act(s, `removeFromPool("${def.id}")  [banish slot ${idx}]`,
               () => s.run.removeFromPool(def.id));
      this.check(s, "banish_storm");
    }
    // Now take one. If the tiers drifted, this is where a player is handed a
    // relic at a tier the card never showed.
    if (s.run.offers.length) {
      const idx = Math.floor(s.rng.next() * s.run.offers.length);
      this.act(s, `takeOffer(${idx})`, () => s.run.takeOffer(idx));
      this.check(s, "banish_storm");
    }
  }

  /** Indices a UI can produce from a stale click handler. */
  private offerIndexAbuse(s: Session): void {
    const bad = [-1, 99, 3, 1.5, Number.NaN];
    for (const i of bad) {
      this.act(s, `takeOffer(${i})`, () => s.run.takeOffer(i as number));
      this.act(s, `hand.takeOffer(${i})`, () => s.hand.takeOffer(i as number));
      this.act(s, "hand.cancel()", () => s.hand.cancel());
    }
    this.check(s, "offer_index_abuse");
  }

  /** Lift, spin and drop at and past the board's edges. */
  private handChurn(s: Session): void {
    const edge = () => Math.floor(s.rng.next() * 11) - 2;   // -2 .. 8
    for (let i = 0; i < 14; i++) {
      const r = s.rng.next();
      if (r < 0.30) {
        const x = edge(), y = edge();
        this.act(s, `hand.liftAt(${x},${y})`, () => s.hand.liftAt(x, y));
      } else if (r < 0.45) {
        this.act(s, "hand.rotate()", () => s.hand.rotate());
      } else if (r < 0.75) {
        const x = edge(), y = edge();
        this.act(s, `hand.drop(${x},${y})`, () => s.hand.drop(x, y));
      } else if (r < 0.82) {
        this.act(s, `hand.toTray(cap=${s.run.tray.length < TRAY_CAPACITY})`,
                 () => s.hand.toTray(s.run.tray.length < TRAY_CAPACITY));
      } else if (r < 0.89) {
        const idx = Math.floor(s.rng.next() * 4) - 1;
        this.act(s, `hand.fromTray(${idx})`, () => s.hand.fromTray(idx));
      } else if (r < 0.95) {
        this.act(s, "hand.scrap()", () => s.hand.scrap());
      } else {
        this.act(s, "hand.cancel()", () => s.hand.cancel());
      }
      this.check(s, "hand_churn");
    }
    this.act(s, "hand.cancel()", () => s.hand.cancel());
  }

  /** Force every pair, legal or not, including a relic against itself. */
  private mergeStorm(s: Session): void {
    const uids = s.run.loom.relics.map((r) => r.uid);
    for (const a of uids) {
      for (const b of uids) {
        this.act(s, `loom.merge(${a},${b})`, () => s.run.loom.merge(a, b));
      }
      this.act(s, `loom.merge(${a},-1)`, () => s.run.loom.merge(a, -1));
    }
    this.check(s, "merge_storm");
  }

  /** Grow the loom at, past and outside its envelope, with and without credit. */
  private expansionAbuse(s: Session): void {
    for (let i = 0; i < 24; i++) {
      const x = Math.floor(s.rng.next() * 13) - 3;   // -3 .. 9
      const y = Math.floor(s.rng.next() * 13) - 3;
      this.act(s, `expandInto(${x},${y})  [pending=${s.run.pendingExpansionCells}]`,
               () => s.run.expandInto(x, y));
    }
    this.check(s, "expansion_abuse");
  }

  /** Buy everything, reroll forever, and see whether gold can go under. */
  private economyDrain(s: Session): void {
    const before = s.run.gold;
    for (let i = 0; i < 30; i++) {
      this.act(s, "reroll()", () => s.run.reroll());
    }
    for (const up of UPGRADES) {
      for (let i = 0; i < 6; i++) {
        this.act(s, `buy("${up.id}")`, () => s.run.buy(up));
      }
    }
    this.check(s, "economy_drain");
    if (s.run.gold > before) {
      this.report(s, "economy_drain", {
        code: "GOLD_FROM_NOTHING", errorType: "economy_exploit", severity: "critical",
        system: "economy / income",
        file: "src/core/run.ts", symbol: "Run.reroll",
        expected: "rerolling and buying can only ever spend gold",
        observed: `gold went ${before} -> ${s.run.gold} across a market with no battle`,
      });
    }
  }

  /**
   * The exploit this game already had once: mint gold without fighting. It was
   * killed by making scrapping pay nothing, so this attack is a regression
   * trap — it takes every offer and destroys it, over and over.
   */
  private scrapLoop(s: Session): void {
    for (let i = 0; i < 12; i++) {
      if (!s.run.offers.length) this.act(s, "reroll()", () => s.run.reroll());
      this.act(s, "hand.takeOffer(0)", () => s.hand.takeOffer(0));
      this.act(s, "hand.scrap()", () => s.hand.scrap());
      const uid = s.run.loom.relics[0]?.uid;
      if (uid !== undefined) this.act(s, `scrap(${uid})`, () => s.run.scrap(uid));
      this.check(s, "scrap_loop");
    }
  }

  /** Transitions in the wrong order — what a stale click handler produces. */
  private phaseConfusion(s: Session): void {
    this.act(s, "settlePhase()", () => s.run.settlePhase());
    const buff = BUFFS[Math.floor(s.rng.next() * BUFFS.length)] as BuffDef;
    this.act(s, `takeBuff("${buff.id}")  [none owed]`, () => s.run.takeBuff(buff));
    this.act(s, "reconcileExpansions()", () => s.run.reconcileExpansions());
    this.check(s, "phase_confusion");
  }

  private attackBuff(s: Session): void {
    // Read the screen twice with nothing in between. If the cards move, the
    // renderer's own redraw would be a free reroll.
    const first = s.run.buffChoices().map((b) => b.id).join(",");
    this.check(s, "buff_redraw");
    const second = s.run.buffChoices().map((b) => b.id).join(",");
    this.check(s, "buff_redraw");
    if (first !== second) {
      this.report(s, "buff_redraw", {
        code: "BUFF_OFFER_REROLLED", errorType: "economy_exploit", severity: "high",
        system: "progression / buffs",
        file: "src/core/run.ts", symbol: "Run.buffChoices",
        expected: "reading the buff screen twice deals the same three cards",
        observed: `[${first}] then [${second}]`,
      });
    }
    this.act(s, "settlePhase()  [before taking anything]", () => s.run.settlePhase());
    this.check(s, "buff_redraw");
    this.act(s, "playBuff(competent)", () => playBuff(s.run, "competent"));
    this.act(s, "settlePhase()", () => s.run.settlePhase());
  }

  private attackExpansion(s: Session): void {
    this.expansionAbuse(s);
    this.act(s, "playExpansion()", () => playExpansion(s.run));
    this.act(s, "settlePhase()", () => s.run.settlePhase());
    this.check(s, "expansion_abuse");
  }

  /**
   * Fight the wave with the ultimate mashed every single tick, and watch the
   * lane while it happens. A wave that neither clears nor kills the Beacon
   * inside its time cap is a stall: something on the lane cannot be answered.
   */
  private driveBattle(s: Session): void {
    const b = s.run.battle;
    if (!b) { this.act(s, "settlePhase()", () => s.run.settlePhase()); return; }
    const mash = s.mode === "hostile" ? s.rng.next() < 0.5 : s.rng.next() < 0.25;
    s.trace.push(mash ? "battle: castUltimate() every tick" : "battle: competent ult policy");

    const limit = 600 * TICK_HZ;
    let t = 0;
    for (; t < limit && !b.finished; t++) {
      if (mash) b.castUltimate(); else playUlt(b, "competent");
      b.tick();
      if (t % 45 === 0) this.check(s, mash ? "ult_spam" : "battle");
    }
    this.check(s, mash ? "ult_spam" : "battle");

    if (!b.finished) {
      this.report(s, "battle_timeout", {
        code: "BATTLE_NEVER_ENDS", errorType: "stuck_state", severity: "critical",
        system: "battle / wave completion",
        file: "src/core/battle.ts", symbol: "Battle.tick",
        expected: "every wave either clears or kills the Beacon",
        observed: `wave ${s.run.wave} still running after 600s with ${b.enemies.length} enemies left`,
      });
    } else if (!b.finished.cleared && b.beaconHp > 0) {
      this.report(s, "battle_stall", {
        code: "WAVE_UNCLEARED_BEACON_ALIVE", errorType: "stuck_state", severity: "high",
        system: "battle / reach",
        file: "src/core/battle.ts", symbol: "Battle.fireRelics",
        expected: "a wave that ends with the Beacon standing was cleared",
        observed: `wave ${s.run.wave} ended uncleared with beaconHp=${b.beaconHp} and ${b.enemies.length} enemies left`,
      });
    }
    this.act(s, "endBattle()", () => s.run.endBattle());
    this.check(s, "battle");
  }

  // -- plumbing -------------------------------------------------------------

  /** Run one game call, record it, and turn any throw into a crash finding. */
  private act(s: Session, label: string, fn: () => unknown): void {
    s.trace.push(label);
    if (s.trace.length > 60) s.trace.splice(0, s.trace.length - 60);
    try {
      fn();
    } catch (err) {
      this.report(s, "exception", {
        code: `THROW_${label.replace(/\W+/g, "_").slice(0, 40).toUpperCase()}`,
        errorType: "crash", severity: "critical",
        system: "core / api",
        file: "src/core", symbol: label.split("(")[0] ?? label,
        expected: "a game call refuses illegal input by returning false, never by throwing",
        observed: `${label} threw: ${String(err).slice(0, 200)}`,
      });
    }
  }

  private check(s: Session, tactic: string): void {
    let snap: Snapshot;
    try {
      snap = snapshotRun(s.run, s.hand);
    } catch (err) {
      s.trace.push(`snapshot failed: ${String(err).slice(0, 80)}`);
      return;
    }
    for (const v of inspect(snap, s.prev)) {
      this.log.add(v, contextFrom(snap, "core-fuzz", tactic, s.seed, s.trace));
      if (this.verbose) console.log(`  [${v.severity}] ${v.code} — ${v.observed}`);
    }
    s.prev = snap;
  }

  private report(s: Session, tactic: string, v: Violation): void {
    const snap = snapshotRun(s.run, s.hand);
    this.log.add(v, contextFrom(snap, "core-fuzz", tactic, s.seed, s.trace));
    if (this.verbose) console.log(`  [${v.severity}] ${v.code} — ${v.observed}`);
  }
}
