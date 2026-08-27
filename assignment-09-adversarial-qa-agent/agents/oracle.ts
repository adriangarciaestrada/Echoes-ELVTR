/**
 * What "broken" means, written down.
 *
 * The agent's whole strategy rests on this file. A fuzzer that only watches for
 * exceptions finds crashes and nothing else — and this game's worst historical
 * bugs never threw: a desynced pair of parallel arrays, a buff screen that
 * rerolled itself when the UI redrew, a scrap loop that minted gold. Each of
 * those is invisible to a "did it throw" check and obvious to an invariant.
 *
 * So the oracle is a set of statements that must hold over a SNAPSHOT of the
 * running game, plus a few that compare consecutive snapshots. The two surfaces
 * — the headless core fuzzer and the browser agent — both produce the same
 * snapshot shape, so both are judged by exactly the same laws.
 *
 * Deliberately NOT here: anything about balance. "The Warden is weak" is a
 * design question the simulator already answers. This file only asks whether
 * the game's own rules are being violated.
 */
import { ENEMIES, LANE_HALF_WIDTH, RELIC_BY_ID, RELICS } from "../../core/content.js";
import { MAX_TIER } from "../../core/types.js";

// ---------------------------------------------------------------------------
// The snapshot: everything the oracle is allowed to look at.
// ---------------------------------------------------------------------------

export interface RelicSnap {
  uid: number;
  defId: string;
  tier: number;
  cells: Array<[number, number]>;
  cooldownLeft: number;
}

export interface EnemySnap {
  id: number;
  kind: string;
  hp: number;
  maxHp: number;
  pos: number;
  x: number;
  stopAt: number;
}

export interface BattleSnap {
  elapsed: number;
  beaconHp: number;
  enemies: EnemySnap[];
  finished: null | { cleared: boolean; goldEarned: number; expEarned: number };
  ultCooldownLeft: number;
  ultCasts: number;
}

export interface Snapshot {
  /**
   * Identity of the Run this snapshot came from. Restarting drops the wave
   * counter back to 1, which is correct and must not be read as a regression,
   * so the consecutive-snapshot laws only apply within one token.
   */
  runToken?: number;
  phase: string;
  wave: number;
  gold: number;
  exp: number;
  level: number;
  beaconHp: number;
  beaconMax: number;
  freeRerolls: number;
  rerollsUsed: number;
  pendingBuffChoices: number;
  pendingExpansionCells: number;
  cls: string;
  env: { w: number; h: number };
  unlocked: string[];
  relics: RelicSnap[];
  tray: Array<{ defId: string; tier: number }>;
  offers: string[];
  offerTiers: number[];
  removed: string[];
  buffs: number;
  /** The three cards currently on the buff screen, in order. */
  buffChoiceIds: string[];
  /** What the player is carrying, if anything. Browser surface only. */
  handDefId: string | null;
  battle: BattleSnap | null;
}

export type Severity = "critical" | "high" | "medium" | "low";

export interface Violation {
  /** Stable identifier — the report dedupes on this plus the system. */
  code: string;
  /** The taxonomy a developer triages by. */
  errorType:
    | "state_desync"
    | "invariant_break"
    | "boundary_break"
    | "stuck_state"
    | "economy_exploit"
    | "crash"
    | "rule_violation";
  severity: Severity;
  /** Where in the GAME, not where in the file. */
  system: string;
  /** Where in the code — file plus the symbol that owns the rule. */
  file: string;
  symbol: string;
  expected: string;
  observed: string;
}

const PHASES = new Set(["battle", "market", "expansion", "buff", "over"]);
const EPS = 1e-6;

const finite = (n: unknown): boolean => typeof n === "number" && Number.isFinite(n);

/** Cells that a 4-cell expansion grant could legally still be spent on. */
export function expandableCount(snap: Snapshot): number {
  const open = new Set(snap.unlocked);
  let n = 0;
  for (let y = 0; y < snap.env.h; y++) {
    for (let x = 0; x < snap.env.w; x++) {
      if (open.has(`${x},${y}`)) continue;
      const touches = [[1, 0], [-1, 0], [0, 1], [0, -1]].some(
        ([dx, dy]) => open.has(`${x + (dx ?? 0)},${y + (dy ?? 0)}`));
      if (touches) n++;
    }
  }
  return n;
}

/**
 * The longest a relic of this kind can ever be re-arming for, used as the
 * ceiling on `cooldownLeft`. Buffs only ever shorten cooldowns, so the
 * unbuffed tier-0 value is a safe upper bound for every tier and every run.
 */
const MAX_COOLDOWN = new Map(
  RELICS.map((r) => [r.id, Math.max(...r.tiers.map((t) => t.cooldown))]));

// ---------------------------------------------------------------------------
// The laws.
// ---------------------------------------------------------------------------

export function inspect(snap: Snapshot, prev: Snapshot | null): Violation[] {
  const v: Violation[] = [];
  const say = (x: Violation) => v.push(x);

  // -- the market's two parallel arrays -------------------------------------
  // `offers[i]` and `offerTiers[i]` are read together by every consumer. Any
  // path that shortens one without the other silently re-tiers every card
  // below it, and the desync survives until the next reroll.
  if (snap.offers.length !== snap.offerTiers.length) {
    say({
      code: "OFFER_TIER_DESYNC", errorType: "state_desync", severity: "high",
      system: "market / relic offers",
      file: "src/core/run.ts", symbol: "Run.removeFromPool",
      expected: "offers and offerTiers stay the same length; offerTiers[i] is the tier of offers[i]",
      observed: `offers=${snap.offers.length} (${snap.offers.join(",")}) but offerTiers=${snap.offerTiers.length} (${snap.offerTiers.join(",")})`,
    });
  }
  for (const t of snap.offerTiers) {
    if (!Number.isInteger(t) || t < 0 || t > MAX_TIER) {
      say({
        code: "OFFER_TIER_RANGE", errorType: "invariant_break", severity: "medium",
        system: "market / relic offers",
        file: "src/core/run.ts", symbol: "Run.rollTier",
        expected: `every offer tier is an integer in 0..${MAX_TIER}`,
        observed: `offerTiers=[${snap.offerTiers.join(",")}]`,
      });
      break;
    }
  }
  for (const id of snap.offers) {
    if (snap.removed.includes(id)) {
      say({
        code: "BANISHED_RELIC_OFFERED", errorType: "rule_violation", severity: "high",
        system: "market / banish",
        file: "src/core/run.ts", symbol: "Run.removeFromPool",
        expected: "a banished relic never appears in an offer again",
        observed: `${id} is banished and on offer`,
      });
      break;
    }
  }

  // -- the loom -------------------------------------------------------------
  const open = new Set(snap.unlocked);
  const seenCell = new Map<string, number>();
  const seenUid = new Set<number>();
  let occupied = 0;
  for (const r of snap.relics) {
    if (seenUid.has(r.uid)) {
      say({
        code: "RELIC_UID_DUPLICATE", errorType: "state_desync", severity: "high",
        system: "loom / placement",
        file: "src/core/grid.ts", symbol: "Loom.place",
        expected: "every placed relic carries a unique uid",
        observed: `uid ${r.uid} appears twice`,
      });
    }
    seenUid.add(r.uid);

    if (!Number.isInteger(r.tier) || r.tier < 0 || r.tier > MAX_TIER) {
      say({
        code: "RELIC_TIER_RANGE", errorType: "invariant_break", severity: "high",
        system: "loom / merge",
        file: "src/game/hand.ts", symbol: "Hand.drop",
        expected: `a relic's tier stays in 0..${MAX_TIER}`,
        observed: `${r.defId} (uid ${r.uid}) is at tier ${r.tier}`,
      });
    }

    const def = RELIC_BY_ID.get(r.defId);
    if (!def) {
      say({
        code: "RELIC_UNKNOWN_DEF", errorType: "invariant_break", severity: "critical",
        system: "loom / placement",
        file: "src/core/grid.ts", symbol: "Loom.place",
        expected: "every placed relic names a relic that exists in the content table",
        observed: `uid ${r.uid} has defId "${r.defId}"`,
      });
    } else if (r.cells.length !== def.footprint.length) {
      say({
        code: "RELIC_FOOTPRINT_MISMATCH", errorType: "invariant_break", severity: "high",
        system: "loom / placement",
        file: "src/core/grid.ts", symbol: "Loom.putDown",
        expected: `${r.defId} occupies exactly ${def.footprint.length} cells`,
        observed: `uid ${r.uid} occupies ${r.cells.length}`,
      });
    }

    const ceiling = MAX_COOLDOWN.get(r.defId) ?? Infinity;
    if (!finite(r.cooldownLeft) || r.cooldownLeft > ceiling + EPS) {
      say({
        code: "RELIC_COOLDOWN_INVALID", errorType: "invariant_break", severity: "medium",
        system: "battle / relic firing",
        file: "src/core/battle.ts", symbol: "Battle.fireRelics",
        expected: `cooldownLeft is finite and never above the relic's own longest cooldown (${ceiling}s)`,
        observed: `${r.defId} (uid ${r.uid}) cooldownLeft=${r.cooldownLeft}`,
      });
    }

    for (const [x, y] of r.cells) {
      occupied++;
      if (x < 0 || y < 0 || x >= snap.env.w || y >= snap.env.h) {
        say({
          code: "RELIC_OUTSIDE_ENVELOPE", errorType: "boundary_break", severity: "critical",
          system: "loom / placement",
          file: "src/core/grid.ts", symbol: "Loom.canPlace",
          expected: `every relic cell sits inside the ${snap.env.w}x${snap.env.h} envelope`,
          observed: `${r.defId} (uid ${r.uid}) occupies (${x},${y})`,
        });
      }
      if (!open.has(`${x},${y}`)) {
        say({
          code: "RELIC_ON_LOCKED_CELL", errorType: "boundary_break", severity: "critical",
          system: "loom / placement",
          file: "src/core/grid.ts", symbol: "Loom.canPlace",
          expected: "a relic only occupies cells the player has unlocked",
          observed: `${r.defId} (uid ${r.uid}) occupies locked cell (${x},${y})`,
        });
      }
      const other = seenCell.get(`${x},${y}`);
      if (other !== undefined) {
        say({
          code: "RELIC_OVERLAP", errorType: "invariant_break", severity: "critical",
          system: "loom / placement",
          file: "src/core/grid.ts", symbol: "Loom.canPlace",
          expected: "no two relics share a cell",
          observed: `uid ${other} and uid ${r.uid} both occupy (${x},${y})`,
        });
      }
      seenCell.set(`${x},${y}`, r.uid);
    }
  }
  if (occupied > snap.unlocked.length) {
    say({
      code: "CELL_BUDGET_EXCEEDED", errorType: "invariant_break", severity: "critical",
      system: "loom / placement",
      file: "src/core/grid.ts", symbol: "Loom.freeCellCount",
      expected: "relics never occupy more cells than the loom has unlocked",
      observed: `${occupied} cells occupied, ${snap.unlocked.length} unlocked`,
    });
  }
  if (snap.unlocked.length > snap.env.w * snap.env.h) {
    say({
      code: "LOOM_OVERGROWN", errorType: "boundary_break", severity: "high",
      system: "loom / expansion",
      file: "src/core/grid.ts", symbol: "Loom.canExpandInto",
      expected: `the loom never grows past ${snap.env.w * snap.env.h} cells`,
      observed: `${snap.unlocked.length} cells unlocked`,
    });
  }
  for (const cell of snap.unlocked) {
    const [sx, sy] = cell.split(",");
    const x = Number(sx), y = Number(sy);
    if (x < 0 || y < 0 || x >= snap.env.w || y >= snap.env.h) {
      say({
        code: "UNLOCKED_OUTSIDE_ENVELOPE", errorType: "boundary_break", severity: "critical",
        system: "loom / expansion",
        file: "src/core/grid.ts", symbol: "Loom.canExpandInto",
        expected: "expansion never unlocks a cell outside the envelope",
        observed: `cell (${x},${y}) is unlocked`,
      });
      break;
    }
  }

  // -- resources ------------------------------------------------------------
  const numbers: Array<[string, number]> = [
    ["gold", snap.gold], ["exp", snap.exp], ["level", snap.level],
    ["wave", snap.wave], ["beaconHp", snap.beaconHp], ["beaconMax", snap.beaconMax],
    ["pendingBuffChoices", snap.pendingBuffChoices],
    ["pendingExpansionCells", snap.pendingExpansionCells],
  ];
  for (const [name, value] of numbers) {
    if (!finite(value)) {
      say({
        code: "NON_FINITE_STATE", errorType: "invariant_break", severity: "critical",
        system: "run / state",
        file: "src/core/run.ts", symbol: "Run",
        expected: `${name} is always a finite number`,
        observed: `${name}=${value}`,
      });
    }
  }
  if (snap.gold < 0 || snap.exp < 0 || snap.level < 1 || snap.wave < 1 ||
      snap.pendingBuffChoices < 0 || snap.pendingExpansionCells < 0) {
    say({
      code: "NEGATIVE_RESOURCE", errorType: "invariant_break", severity: "high",
      system: "economy / run state",
      file: "src/core/run.ts", symbol: "Run.buy",
      expected: "gold, exp, level, wave and the pending reward queues never go negative",
      observed: `gold=${snap.gold} exp=${snap.exp} level=${snap.level} wave=${snap.wave} ` +
                `buffQ=${snap.pendingBuffChoices} expandQ=${snap.pendingExpansionCells}`,
    });
  }
  if (snap.beaconHp > snap.beaconMax + EPS) {
    say({
      code: "BEACON_OVERHEAL", errorType: "invariant_break", severity: "medium",
      system: "economy / beacon upgrades",
      file: "src/core/run.ts", symbol: "UPGRADES.repair",
      expected: "the Beacon is never repaired past its maximum",
      observed: `beaconHp=${snap.beaconHp} beaconMax=${snap.beaconMax}`,
    });
  }
  if (snap.phase !== "over" && snap.phase !== "battle" && snap.beaconHp <= 0) {
    say({
      code: "DEAD_BEACON_STILL_PLAYING", errorType: "invariant_break", severity: "high",
      system: "run / phase machine",
      file: "src/core/run.ts", symbol: "Run.endBattle",
      expected: "a run whose Beacon is at zero is over",
      observed: `phase="${snap.phase}" with beaconHp=${snap.beaconHp}`,
    });
  }

  // -- the phase machine ----------------------------------------------------
  if (!PHASES.has(snap.phase)) {
    say({
      code: "PHASE_UNKNOWN", errorType: "invariant_break", severity: "critical",
      system: "run / phase machine",
      file: "src/core/run.ts", symbol: "Run.phase",
      expected: `phase is one of ${[...PHASES].join(", ")}`,
      observed: `phase="${snap.phase}"`,
    });
  }
  if (snap.phase === "battle" && !snap.battle) {
    say({
      code: "BATTLE_PHASE_WITHOUT_BATTLE", errorType: "state_desync", severity: "critical",
      system: "run / phase machine",
      file: "src/core/run.ts", symbol: "Run.startBattle",
      expected: "the battle phase always has a battle behind it",
      observed: "phase=battle, run.battle=null",
    });
  }
  if (snap.phase !== "battle" && snap.battle && !snap.battle.finished) {
    say({
      code: "LIVE_BATTLE_OUTSIDE_BATTLE", errorType: "state_desync", severity: "high",
      system: "run / phase machine",
      file: "src/core/run.ts", symbol: "Run.settlePhase",
      expected: "leaving the battle phase means the battle has finished",
      observed: `phase="${snap.phase}" with an unfinished battle at t=${snap.battle.elapsed.toFixed(2)}s`,
    });
  }
  if (snap.phase === "market" && snap.pendingBuffChoices > 0) {
    say({
      code: "REWARD_QUEUE_SKIPPED", errorType: "state_desync", severity: "high",
      system: "progression / reward queue",
      file: "src/core/run.ts", symbol: "Run.settlePhase",
      expected: "the market is only reached once every earned reward has been taken",
      observed: `phase=market with ${snap.pendingBuffChoices} buff choices still owed`,
    });
  }
  if (snap.phase === "market" && snap.pendingExpansionCells > 0 && expandableCount(snap) > 0) {
    say({
      code: "REWARD_QUEUE_SKIPPED", errorType: "state_desync", severity: "high",
      system: "progression / reward queue",
      file: "src/core/run.ts", symbol: "Run.settlePhase",
      expected: "the market is only reached once every earned expansion cell has been placed",
      observed: `phase=market with ${snap.pendingExpansionCells} expansion cells owed and ${expandableCount(snap)} legal targets`,
    });
  }
  if (snap.phase === "expansion" && snap.pendingExpansionCells > 0 && expandableCount(snap) === 0) {
    say({
      code: "EXPANSION_DEADLOCK", errorType: "stuck_state", severity: "critical",
      system: "progression / expansion",
      file: "src/core/run.ts", symbol: "Run.reconcileExpansions",
      expected: "an expansion phase always has at least one legal cell, or converts itself to buffs",
      observed: `${snap.pendingExpansionCells} cells owed, nowhere legal to put them`,
    });
  }
  if (snap.phase === "buff" && snap.buffChoiceIds.length !== 3) {
    say({
      code: "BUFF_SCREEN_EMPTY", errorType: "stuck_state", severity: "high",
      system: "progression / buffs",
      file: "src/core/run.ts", symbol: "Run.buffChoices",
      expected: "the buff screen always deals exactly three cards",
      observed: `${snap.buffChoiceIds.length} cards: [${snap.buffChoiceIds.join(",")}]`,
    });
  }

  // -- the tray -------------------------------------------------------------
  // "Anything left in it when the fight begins is scrapped" is how discarding
  // works at all; a tray that survives into a battle means the relics the
  // player walked away from are still theirs.
  if (snap.phase === "battle" && snap.tray.length > 0) {
    say({
      code: "TRAY_SURVIVED_INTO_BATTLE", errorType: "rule_violation", severity: "medium",
      system: "market / tray",
      file: "src/core/run.ts", symbol: "Run.startBattle",
      expected: "the tray is emptied when a fight starts",
      observed: `${snap.tray.length} relics still in the tray during wave ${snap.wave}`,
    });
  }

  // -- the lane -------------------------------------------------------------
  if (snap.battle) {
    for (const e of snap.battle.enemies) {
      const def = ENEMIES[e.kind];
      if (!finite(e.pos) || !finite(e.x) || !finite(e.hp)) {
        say({
          code: "ENEMY_NON_FINITE", errorType: "invariant_break", severity: "critical",
          system: "battle / lane",
          file: "src/core/battle.ts", symbol: "Battle.moveEnemies",
          expected: "an enemy's position and health stay finite",
          observed: `${e.kind} #${e.id} pos=${e.pos} x=${e.x} hp=${e.hp}`,
        });
        continue;
      }
      if (e.pos > 1 + 1e-3 || e.pos < e.stopAt - 1e-3) {
        say({
          code: "ENEMY_OUT_OF_LANE", errorType: "boundary_break", severity: "high",
          system: "battle / lane",
          file: "src/core/battle.ts", symbol: "Battle.runUltimate",
          expected: "an enemy stays between the spawn line (1) and where its kind halts",
          observed: `${e.kind} #${e.id} at pos=${e.pos.toFixed(4)} (halts at ${e.stopAt})`,
        });
      }
      if (Math.abs(e.x) > LANE_HALF_WIDTH + 1e-3) {
        say({
          code: "ENEMY_OUT_OF_LANE", errorType: "boundary_break", severity: "high",
          system: "battle / lane",
          file: "src/core/battle.ts", symbol: "Battle.runUltimate",
          expected: `an enemy stays inside the lane (|x| <= ${LANE_HALF_WIDTH.toFixed(3)})`,
          observed: `${e.kind} #${e.id} at x=${e.x.toFixed(4)}`,
        });
      }
      // The reach law: nothing may come to rest where no relic in the roster
      // could ever answer it, because that is a Beacon ground down by something
      // the player cannot shoot back at.
      if (def && Math.abs(e.pos - e.stopAt) < 1e-6 &&
          Math.hypot(e.x, e.pos) > LANE_HALF_WIDTH + 1e-3) {
        say({
          code: "UNREACHABLE_ATTACKER", errorType: "boundary_break", severity: "critical",
          system: "battle / reach law",
          file: "src/core/content.ts", symbol: "spawnSpanFor",
          expected: "nothing comes to rest further from the Beacon than the shortest reach in the roster",
          observed: `${e.kind} #${e.id} rests at distance ${Math.hypot(e.x, e.pos).toFixed(3)}`,
        });
      }
      if (e.hp > e.maxHp + EPS) {
        say({
          code: "ENEMY_OVERHEAL", errorType: "invariant_break", severity: "low",
          system: "battle / lane",
          file: "src/core/battle.ts", symbol: "Battle.spawn",
          expected: "an enemy never has more health than it spawned with",
          observed: `${e.kind} #${e.id} hp=${e.hp} maxHp=${e.maxHp}`,
        });
      }
    }
    if (!finite(snap.battle.ultCooldownLeft)) {
      say({
        code: "ULT_COOLDOWN_NON_FINITE", errorType: "invariant_break", severity: "medium",
        system: "battle / ultimate",
        file: "src/core/battle.ts", symbol: "Battle.castUltimate",
        expected: "the ultimate's cooldown stays a finite number of seconds",
        observed: `ultCooldownLeft=${snap.battle.ultCooldownLeft}`,
      });
    }
  }

  // -- laws that need two snapshots ----------------------------------------
  if (prev) {
    if (snap.wave < prev.wave) {
      say({
        code: "WAVE_REGRESSION", errorType: "invariant_break", severity: "high",
        system: "run / progression",
        file: "src/core/run.ts", symbol: "Run.endBattle",
        expected: "a run's wave counter only ever climbs",
        observed: `wave went ${prev.wave} -> ${snap.wave}`,
      });
    }
    // Gold comes from kills, full stop. A market that ends richer than it
    // started is the scrap-refund loop coming back in some new disguise.
    if (prev.phase !== "battle" && snap.phase !== "battle" &&
        snap.wave === prev.wave && snap.gold > prev.gold) {
      say({
        code: "GOLD_FROM_NOTHING", errorType: "economy_exploit", severity: "critical",
        system: "economy / income",
        file: "src/core/run.ts", symbol: "Run.scrap",
        expected: "gold is only ever earned by killing something",
        observed: `gold went ${prev.gold} -> ${snap.gold} inside wave ${snap.wave} without a battle`,
      });
    }
    // The buff screen is dealt once and held. If the three cards change while
    // the player still owes the same choice, something is redrawing the screen
    // into a free reroll.
    if (prev.phase === "buff" && snap.phase === "buff" &&
        prev.pendingBuffChoices === snap.pendingBuffChoices &&
        prev.buffs === snap.buffs &&
        prev.buffChoiceIds.length === 3 && snap.buffChoiceIds.length === 3 &&
        prev.buffChoiceIds.join(",") !== snap.buffChoiceIds.join(",")) {
      say({
        code: "BUFF_OFFER_REROLLED", errorType: "economy_exploit", severity: "high",
        system: "progression / buffs",
        file: "src/core/run.ts", symbol: "Run.buffChoices",
        expected: "the three buff cards are dealt once per grant and held until one is taken",
        observed: `[${prev.buffChoiceIds.join(",")}] became [${snap.buffChoiceIds.join(",")}] with the same choice still owed`,
      });
    }
    // Taking an offer must move the card that was clicked. The tier a player
    // was shown is the tier they must get.
    if (prev.phase === "market" && snap.phase === "market" &&
        prev.offers.length === prev.offerTiers.length &&
        snap.offers.length === snap.offerTiers.length &&
        prev.offers.length === snap.offers.length) {
      for (let i = 0; i < snap.offers.length; i++) {
        if (snap.offers[i] === prev.offers[i] &&
            snap.offerTiers[i] !== prev.offerTiers[i]) {
          say({
            code: "OFFER_TIER_MUTATED", errorType: "state_desync", severity: "high",
            system: "market / relic offers",
            file: "src/core/run.ts", symbol: "Run.removeFromPool",
            expected: "an offer's tier does not change while the offer stays on the shelf",
            observed: `${snap.offers[i]} in slot ${i} went tier ${prev.offerTiers[i]} -> ${snap.offerTiers[i]}`,
          });
          break;
        }
      }
    }
  }

  return v;
}
