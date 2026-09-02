/**
 * A run: the state machine around the battle. Pure, like the battle — the
 * simulator drives this to play whole runs headlessly, the renderer drives it
 * from clicks. Neither owns it.
 *
 * BATTLE -> MARKET (offers, reroll, remove, repack) -> [EXPANSION | BUFF] -> BATTLE
 */
import { BEACON_HP, BUFFS, CATEGORY_REACH, CLASSES, RELICS, RELIC_BY_ID, ULTIMATES,
         type BuffDef } from "./content.js";
import { Battle } from "./battle.js";
import { Loom, envelope, type ClassId } from "./grid.js";
import { Rng } from "./rng.js";
import { waveSpec } from "./waves.js";
import { MAX_TIER, type Category, type RelicDef, type Tier, type TierStats,
         type UltStats, type UltimateDef } from "./types.js";

export type Phase = "battle" | "market" | "expansion" | "buff" | "over";

/**
 * Free rerolls per market before gold is charged (economy.md). One, not two:
 * with two, a player never needed gold and simply watched it accumulate.
 */
const BASE_FREE_REROLLS = 1;
const REROLL_COST = 8;

/**
 * The upgrade shop — the other half of the economy, and the reason gold is
 * worth earning. Run-scoped like everything else: nothing survives the run,
 * so unspent gold is wasted gold.
 */
export interface Upgrade {
  readonly id: string;
  readonly label: string;
  readonly describe: (run: Run) => string;
  readonly cost: (bought: number) => number;
  readonly apply: (run: Run) => void;
  readonly max?: number;
}

export const UPGRADES: readonly Upgrade[] = [
  { id: "repair", label: "Mend",
    describe: () => "+30 hp",
    cost: (n) => 15 + n * 5,
    apply: (r) => { r.beaconHp = Math.min(r.beaconMax, r.beaconHp + 30); } },
  { id: "reinforce", label: "Reinforce",
    describe: () => "+20 max",
    cost: (n) => 30 + n * 20,
    apply: (r) => { r.beaconMax += 20; r.beaconHp += 20; } },
  { id: "reroll", label: "Shuttle",
    describe: (r) => `${r.freeRerolls}→${r.freeRerolls + 1} rerolls`,
    cost: (n) => 45 + n * 30, max: 3,
    apply: (r) => { r.freeRerolls += 1; } },
  { id: "study", label: "Study",
    describe: () => "+20% exp",
    cost: (n) => 40 + n * 25, max: 4,
    apply: (r) => { r.expBonus += 0.2; } },
];
const OFFERS = 3;
const EXP_BASE = 20;
/**
 * Waves per tier of market drift `[TUNE]`.
 *
 * At 11 a player reached a board of solid Epics by wave 31 and the game stopped
 * being about the loom — no placement left to decide, only gold to spend. The
 * inventory layer has to stay alive for most of a run, so the ladder climbs
 * about half as fast.
 */
const TIER_PACE = 19;

export class Run {
  readonly loom: Loom;
  readonly rng: Rng;
  readonly env: { w: number; h: number };
  readonly buffs: BuffDef[] = [];

  wave = 1;
  gold = 0;
  exp = 0;
  level = 1;
  beaconHp = BEACON_HP;
  beaconMax = BEACON_HP;
  freeRerolls = BASE_FREE_REROLLS;
  expBonus = 0;
  readonly bought = new Map<string, number>();
  phase: Phase = "market";

  /** Relic ids banished from the offer pool by the player (economy.md). */
  readonly removed = new Set<string>();
  offers: RelicDef[] = [];
  /** Tier each offer rolled at, parallel to `offers`. */
  offerTiers: Tier[] = [];
  rerollsUsed = 0;
  /** Alternation: expansion after odd fills, buff after even (economy.md). */
  private fills = 0;
  pendingExpansionCells = 0;

  /**
   * The tray: staging space beside the loom.
   *
   * It does two jobs with one mechanic. While packing, it is somewhere to put
   * relics so a full board can actually be rearranged — without it, repacking
   * a full loom is impossible, since every cell is occupied. And anything left
   * in it when the fight begins is scrapped, so discarding needs no separate
   * verb: you set aside what you do not want and walk away from it.
   */
  readonly tray: Array<{ defId: string; tier: Tier }> = [];

  battle: Battle | null = null;
  /** The battle whose reward has already been paid; see endBattle(). */
  private settled: Battle | null = null;
  lastDamage = new Map<number, number>();
  /**
   * Damage over the WHOLE run, by relic kind rather than by instance.
   *
   * `lastDamage` is keyed by uid and holds one battle, which is the wrong shape
   * for a score screen twice over: a run is not its final stand, and merging
   * mints a new uid, so a relic's history would reset every time it was woven.
   * Keying by defId follows the relic through its tiers.
   */
  damageByKind = new Map<string, number>();
  readonly ult: UltimateDef;

  constructor(readonly cls: ClassId, seed: number) {
    this.loom = new Loom(cls);
    this.rng = new Rng(seed);
    this.env = envelope(cls);
    // The class's starting relic and ultimate (loom-design.md): a class is
    // exactly its starting relic, its loom shape and its ultimate.
    this.ult = ULTIMATES[CLASSES[cls].ultId];
    const startId = CLASSES[cls].startRelicId;
    const def = RELIC_BY_ID.get(startId)!;
    const spot = this.loom.findSpot(def.footprint, this.env)!;
    this.loom.place(def, spot.x, spot.y, spot.rot);
    this.rollOffers();
  }

  // ---- buffs applied to a relic's stats --------------------------------
  statsFor(defId: string, tier: number): TierStats {
    const def = RELIC_BY_ID.get(defId)!;
    const base = def.tiers[tier]!;
    let dmg = base.damage, cd = base.cooldown, range = base.range;
    for (const b of this.buffs) {
      const e = b.effect;
      if (e.k === "damage" && e.category === def.category) dmg *= 1 + e.pct / 100;
      else if (e.k === "cooldown" && e.category === def.category) cd *= 1 - e.pct / 100;
      else if (e.k === "range") range *= 1 + e.pct / 100;
    }
    // Range is capped per category. Without this a stacking range buff erases
    // the one identity the categories read most clearly, and a playtest with
    // two of them had Burst relics striking the spawn line.
    range = Math.min(CATEGORY_REACH[def.category].max, range);
    // Floored at 0.05s — the same guard battle.ts's DPS estimate already
    // applies to this same value, while the real cooldown never got one.
    // Cooldown stacks multiplicatively —
    // 1-pct/100 per buff — so it only ever approaches 0, never reaches it
    // mathematically, but `.toFixed(3)` rounds anything under 0.0005 down to
    // a stored 0.000, and a relic re-arming at 0 fires every tick forever.
    // A run at wave 120+ with ~47 stacked -15% cooldown buffs hit exactly
    // this, and could no longer lose.
    return { ...base, damage: Math.round(dmg), cooldown: +Math.max(0.05, cd).toFixed(3), range };
  }

  /** The same, for the ultimate. */
  ultStatsFor(def: UltimateDef): UltStats {
    let worth = def.worthSeconds, cd = def.cooldown;
    let radius = def.radius, duration = def.duration ?? 0;
    for (const b of this.buffs) {
      const e = b.effect;
      if (e.k === "ult_damage") worth *= 1 + e.pct / 100;
      else if (e.k === "ult_cooldown") cd *= 1 - e.pct / 100;
      // Reach grows the area AND, for the knot, the time it holds the lane —
      // one buff, one idea, whichever ultimate the class happens to carry.
      else if (e.k === "ult_size") { radius *= 1 + e.pct / 100; duration *= 1 + e.pct / 100; }
    }
    // Floored at 15s so stacked cooldown buffs cannot turn the one live input
    // into a rotation. An ultimate is meant to land once or twice in a wave;
    // heavy investment buys a second cast in waves that used to allow one, not
    // a fourth in every wave.
    return { worthSeconds: worth, cooldown: Math.max(15, cd), radius, duration };
  }

  // ---- market -----------------------------------------------------------

  /**
   * Which tier an offer rolls at. Early waves are all Common; the centre of
   * the distribution walks upward roughly one tier every TIER_PACE waves.
   *
   * Without this the run dead-ends: a board full of merged relics can neither
   * place a Common (no space) nor merge one into anything (wrong tier), so
   * improvement stops permanently while the waves keep escalating. Reported
   * from play at wave 35.
   */
  private rollTier(): Tier {
    const centre = (this.wave - 1) / TIER_PACE;
    const weights: number[] = [];
    for (let t = 0; t <= MAX_TIER; t++) {
      // A bell around the current centre, and never above what the player
      // could plausibly have merged to by now.
      weights.push(centre + 0.6 < t ? 0 : Math.exp(-((t - centre) ** 2) / 1.1));
    }
    const total = weights.reduce((a, c) => a + c, 0);
    let roll = this.rng.next() * total;
    for (let t = 0; t <= MAX_TIER; t++) {
      roll -= weights[t]!;
      if (roll <= 0) return t as Tier;
    }
    return 0 as Tier;
  }
  private pool(): RelicDef[] {
    return RELICS.filter((r) => !this.removed.has(r.id));
  }

  /**
   * How many times the shelf has been dealt. Read by the adversarial oracle to
   * tell "this tier changed" apart from "these are different cards": a re-deal
   * puts the same relic back in the same slot at a different tier about 12% of
   * the time, which by looking at the shelf alone is indistinguishable from a
   * desync. It stayed invisible while a real desync existed to explain it.
   */
  deals = 0;

  rollOffers(): void {
    this.deals++;
    const pool = this.pool();
    this.offers = this.rng.shuffle(pool).slice(0, Math.min(OFFERS, pool.length));
    this.offerTiers = this.offers.map(() => this.rollTier());
  }

  get rerollCost(): number {
    if (this.rerollsUsed < this.freeRerolls) return 0;
    // Rising within a market, as the reference does: hunting a specific twin
    // should cost more the longer you hunt it.
    return REROLL_COST * (this.rerollsUsed - this.freeRerolls + 1);
  }

  upgradeCost(u: Upgrade): number {
    return u.cost(this.bought.get(u.id) ?? 0);
  }

  canBuy(u: Upgrade): boolean {
    const n = this.bought.get(u.id) ?? 0;
    if (u.max !== undefined && n >= u.max) return false;
    if (u.id === "repair" && this.beaconHp >= this.beaconMax) return false;
    return this.gold >= this.upgradeCost(u);
  }

  buy(u: Upgrade): boolean {
    if (!this.canBuy(u)) return false;
    this.gold -= this.upgradeCost(u);
    this.bought.set(u.id, (this.bought.get(u.id) ?? 0) + 1);
    u.apply(this);
    return true;
  }

  reroll(): boolean {
    const cost = this.rerollCost;
    if (this.gold < cost) return false;
    this.gold -= cost;
    this.rerollsUsed++;
    this.rollOffers();
    return true;
  }

  /**
   * Banish a relic type from all future offers. One of the real decisions.
   *
   * `offers` and `offerTiers` are parallel arrays and every read pairs them by
   * index, so a card can only leave the shelf if its tier leaves with it.
   * Filtering `offers` alone handed each surviving card the tier of the slot
   * above it — and banishing costs nothing, so a player could chain banishes to
   * walk the best rarity on the shelf down onto the last card left. Found by
   * the adversarial QA agent (LOOM-ADV-001/004/005); `drop()` had the same
   * fault fixed separately, which is why this one survived.
   */
  removeFromPool(id: string): boolean {
    if (this.pool().length <= 1) return false;
    this.removed.add(id);
    for (let i = this.offers.length - 1; i >= 0; i--) {
      if (this.offers[i]!.id === id) {
        this.offers.splice(i, 1);
        this.offerTiers.splice(i, 1);
      }
    }
    return true;
  }

  /** Take an offer and place it. Returns false if it will not fit. */
  takeOffer(index: number, at?: { x: number; y: number; rot: number }): boolean {
    const def = this.offers[index];
    if (!def) return false;
    const spot = at ?? this.loom.findSpot(def.footprint, this.env);
    if (!spot) return false;
    if (!this.loom.place(def, spot.x, spot.y, spot.rot, this.offerTiers[index] ?? 0)) return false;
    this.offers.splice(index, 1);
    this.offerTiers.splice(index, 1);
    return true;
  }

  /**
   * Scrapping frees space and pays NOTHING.
   *
   * It used to refund gold by tier, which created a second income stream that
   * bypassed combat: reroll for eight, take three high-tier offers, scrap them
   * for up to a hundred and forty, repeat forever. Reported from play, and not
   * fixable by pricing — any refund large enough to feel worthwhile exceeds a
   * reroll the moment market tiers climb. Gold comes from kills, full stop, so
   * the only way to earn is to fight.
   */
  scrap(uid: number): boolean {
    if (!this.loom.relics.some((r) => r.uid === uid)) return false;
    this.loom.remove(uid);
    return true;
  }

  // ---- progression ------------------------------------------------------
  private expToLevel(): number {
    return Math.round(EXP_BASE * Math.pow(1.25, this.level - 1));
  }

  /** Consume EXP into levels, queueing the alternating reward. */
  private drainExp(): void {
    while (this.exp >= this.expToLevel()) {
      this.exp -= this.expToLevel();
      this.level++;
      this.fills++;
      const boardFull = this.loom.unlocked.size >= this.env.w * this.env.h;
      // Alternation: buff, expansion, buff, ... When the board can grow no
      // further, expansion fills convert to buffs so no reward is ever dead.
      if (this.fills % 2 === 0 && !boardFull) this.pendingExpansionCells += 4;
      else this.pendingBuffChoices++;
    }
  }
  pendingBuffChoices = 0;

  /**
   * The three on offer. Rolled ONCE per grant and held, exactly as the market's
   * offers are.
   *
   * It used to shuffle on every call, which made it a reroll button for anyone
   * who could get the screen to redraw — clicking the speed toggle during buff
   * selection dealt three new buffs, so a player could fish for the one they
   * wanted for free.
   *
   * The worse half was invisible: the renderer calls this to draw the screen,
   * so drawing the game ADVANCED THE RUN'S RNG. The same seed and the same
   * decisions produced different runs depending on how often the UI happened to
   * redraw, which is the one thing this core may never do — the simulator's
   * verdicts are only worth anything while it and the game agree.
   */
  buffChoices(): BuffDef[] {
    if (!this.buffOffer.length) this.buffOffer = this.rng.shuffle(BUFFS).slice(0, 3);
    return this.buffOffer;
  }
  private buffOffer: BuffDef[] = [];

  /**
   * Spend one earned grant on a buff. Returns false if none is owed.
   *
   * It used to apply whatever it was handed, counting the grant down with a
   * floor at zero — so calling it against an empty queue was free permanent
   * power, and the only thing preventing that was the renderer remembering to
   * destroy the buff screen's click zones. It had already failed to once.
   * Found by the adversarial QA agent (LOOM-ADV-003).
   */
  takeBuff(b: BuffDef): boolean {
    if (this.pendingBuffChoices <= 0) return false;
    // Spent: the next grant deals a fresh three.
    this.buffOffer = [];
    if (b.effect.k === "repair") {
      this.beaconHp = Math.min(this.beaconMax, this.beaconHp + b.effect.amount);
    } else {
      this.buffs.push(b);
    }
    this.pendingBuffChoices--;
    return true;
  }

  /** Legal expansion targets right now. Empty means the board cannot grow. */
  expandableCells(): Array<[number, number]> {
    const out: Array<[number, number]> = [];
    for (let y = 0; y < this.env.h; y++)
      for (let x = 0; x < this.env.w; x++)
        if (this.loom.canExpandInto(x, y, this.env)) out.push([x, y]);
    return out;
  }

  expandInto(x: number, y: number): boolean {
    if (this.pendingExpansionCells <= 0) return false;
    if (!this.loom.canExpandInto(x, y, this.env)) return false;
    this.loom.expand(x, y);
    this.pendingExpansionCells--;
    this.reconcileExpansions();
    return true;
  }

  /**
   * A pending cell with nowhere legal to go would stall the run forever. The
   * board is full or unreachable: convert what is left into buff choices,
   * which is the same rule the alternation already applies at grant time.
   */
  reconcileExpansions(): void {
    if (this.pendingExpansionCells > 0 && this.expandableCells().length === 0) {
      this.pendingBuffChoices += this.pendingExpansionCells;
      this.pendingExpansionCells = 0;
    }
  }

  // ---- phase transitions -------------------------------------------------
  startBattle(onEvent?: (e: import("./battle.js").BattleEvent) => void): Battle {
    // Anything still in the tray is left behind for good.
    this.tray.length = 0;
    this.phase = "battle";
    this.battle = new Battle(
      waveSpec(this.wave), this.loom, this.rng, this.env, this.beaconHp, onEvent,
      // Buffs live on the run, so the battle asks rather than knows.
      (id, tier) => this.statsFor(id, tier),
      this.ult,
      (d) => this.ultStatsFor(d),
    );
    return this.battle;
  }

  /** Called when the battle reports finished. Advances the run. */
  endBattle(): void {
    const b = this.battle;
    if (!b || !b.finished) return;
    // Settle each battle exactly once. A second call paid the wave's gold and
    // EXP again and advanced past a wave that was never fought — the reward
    // doubled and the next wave skipped. Nothing in the game calls this twice
    // on purpose; a click handler that outlives its phase does, which is how
    // the adversarial QA agent reached it (LOOM-ADV-002).
    if (this.settled === b) return;
    this.settled = b;
    this.beaconHp = b.beaconHp;
    this.gold += b.finished.goldEarned;
    this.exp += Math.round(b.finished.expEarned * (1 + this.expBonus));
    this.lastDamage = b.finished.damageByRelic;
    for (const [uid, dealt] of b.finished.damageByRelic) {
      const relic = this.loom.relics.find((r) => r.uid === uid);
      if (!relic) continue;   // merged or unravelled mid-battle; its total is lost
      this.damageByKind.set(relic.defId,
        (this.damageByKind.get(relic.defId) ?? 0) + dealt);
    }
    if (!b.finished.cleared) { this.phase = "over"; return; }
    this.wave++;
    this.drainExp();
    this.reconcileExpansions();
    this.rerollsUsed = 0;
    this.rollOffers();
    this.phase = this.pendingBuffChoices > 0 ? "buff"
      : this.pendingExpansionCells > 0 ? "expansion" : "market";
  }

  /**
   * Advance out of a reward phase once its queue is empty. A no-op from any
   * other phase — without this, a stale UI handler calling it mid-battle
   * (a leaked buff-pick click zone did exactly this) could force `phase`
   * straight to "market" out from under a battle in progress.
   */
  settlePhase(): void {
    if (this.phase !== "buff" && this.phase !== "expansion") return;
    if (this.pendingBuffChoices > 0) this.phase = "buff";
    else if (this.pendingExpansionCells > 0) this.phase = "expansion";
    else this.phase = "market";
  }
}
