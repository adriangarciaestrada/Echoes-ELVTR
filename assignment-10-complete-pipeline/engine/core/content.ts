/**
 * The content tables. Every number traces to a loom-vault contract and is
 * marked TUNE there; the simulator owns the final values.
 *
 * Anchor (relic-contract.md): a tier-1 relic is 10 damage / 1.2 s ~= 8.3 dps,
 * and the ladder rises ~1.7x per tier — never 2x, which is law 1: merging
 * buys space and effects, never raw damage.
 */
import type { ClassId } from "./grid.js";
import type { Category, EnemyDef, RelicDef, TierStats, UltimateDef, UltimateId } from "./types.js";

/** Law 1 made mechanical: five tiers rising 1.7x, so 2 merged < 2 separate. */
const TIER_GROWTH = 1.7;
const COOLDOWN_GAIN = 0.9;

function ladder(
  damage: number, cooldown: number, range: number,
  extra: Partial<Record<number, Partial<TierStats>>> = {},
): TierStats[] {
  const out: TierStats[] = [];
  // An effect is STICKY once a tier grants it. Written as a plain per-tier
  // override, every relic silently lost its effect at tier 4 — the highest one —
  // because `extra` only ever named tiers 2 and 3. Upgrading to the top rarity
  // took the pierce, burn, knock or slow away, which no one decided and nothing
  // checked. A tier may still REPLACE the effect (burst_bomb trades slow for
  // stun at 3); it can no longer drop it by omission.
  let effect: TierStats["effect"] | undefined;
  for (let t = 0; t < 5; t++) {
    if (extra[t]?.effect) effect = extra[t]!.effect;
    out.push({
      damage: Math.round(damage * TIER_GROWTH ** t),
      cooldown: +(cooldown * COOLDOWN_GAIN ** t).toFixed(3),
      range,
      ...(effect ? { effect } : {}),
      ...extra[t],
    });
  }
  return out;
}

/**
 * Nine relics: three Bolt, three Burst, three Construct, and inside each
 * category a SMALL, a MEDIUM and a LARGE footprint. The roster was 4/4/2 and
 * lopsided — Construct was thin enough that a build committing to it starved on
 * offers, while Bolt and Burst each carried an in-between relic the crew's own
 * reviewer kept describing as "sitting between" two others without creating a
 * decision. A shape a player cannot tell apart from another shape is a slot,
 * not a choice.
 */
export const RELICS: readonly RelicDef[] = [
  // --- Bolts: direct, single target -------------------------------------
  { id: "bolt_needle", category: "Bolt", stacking: "stacks",
    footprint: [[0, 0]],
    tiers: ladder(10, 1.2, 0.88, { 2: { effect: "pierce" }, 3: { effect: "pierce" } }) },
  { id: "bolt_long", category: "Bolt", stacking: "stacks",
    footprint: [[0, 0], [1, 0], [2, 0]],
    tiers: ladder(38, 2.2, 1.00, { 2: { effect: "armor_shred" }, 3: { effect: "armor_shred" } }) },
  { id: "bolt_heavy", category: "Bolt", stacking: "stacks",
    footprint: [[0, 0], [1, 0], [0, 1], [1, 1]],
    tiers: ladder(52, 2.6, 0.85, { 2: { effect: "knock" }, 3: { effect: "knock" } }) },

  // --- Bursts: area -------------------------------------------------------
  { id: "burst_bomb", category: "Burst", stacking: "stacks",
    footprint: [[0, 0]],
    tiers: ladder(10, 1.6, 0.47, {
      0: { spread: 0.22 }, 1: { spread: 0.25 },
      2: { spread: 0.28, effect: "slow_20" }, 3: { spread: 0.31, effect: "stun_10" },
      4: { spread: 0.34 } }) },
  { id: "burst_arc", category: "Burst", stacking: "stacks",
    footprint: [[0, 0], [1, 0], [0, 1]],
    tiers: ladder(22, 2.0, 0.55, {
      0: { spread: 0.26 }, 1: { spread: 0.29 },
      2: { spread: 0.32, effect: "burn" }, 3: { spread: 0.35, effect: "burn" },
      4: { spread: 0.38 } }) },
  { id: "burst_field", category: "Burst", stacking: "stacks",
    footprint: [[0, 0], [1, 0], [1, 1], [2, 1]],
    tiers: ladder(34, 2.8, 0.50, {
      0: { spread: 0.32 }, 1: { spread: 0.35 },
      2: { spread: 0.39, effect: "burn" }, 3: { spread: 0.42, effect: "burn" },
      4: { spread: 0.46 } }) },

  // Produced by the relic crew (assignment 03) and accepted by it: gate clean,
  // net +3.0 waves against a duplicate of construct_turret, 100% pick rate.
  // It TRADES with the turret rather than beating it — 4.5 damage-per-cell
  // against 5.71, and reach at the band floor — and buys one thing: it fits
  // where two cells will not.
  { id: "construct_node", category: "Construct", stacking: "stacks",
    footprint: [[0, 0]],
    tiers: ladder(10, 2.2, 0.60) },
  // --- Constructs: summons -------------------------------------------------
  // one_of: the orbiter's slow does not stack (reference: bouncing blade)
  // "The orbiter strikes what it passes" (combat-model.md). It sweeps a ring,
  // which is what its five cells and its floor-of-the-band damage-per-cell were
  // always priced for; it just never did it.
  { id: "construct_orbit", category: "Construct", stacking: "one_of", pattern: "ring",
    footprint: [[1, 0], [0, 1], [1, 1], [2, 1], [1, 2]],
    tiers: ladder(12, 1.0, 0.60, { 2: { effect: "slow_20" }, 3: { effect: "slow_20" } }) },
  { id: "construct_turret", category: "Construct", stacking: "stacks",
    footprint: [[0, 0], [1, 0]],
    tiers: ladder(16, 1.4, 0.72, { 2: { effect: "pierce" }, 3: { effect: "pierce" } }) },
];

export const RELIC_BY_ID = new Map(RELICS.map((r) => [r.id, r]));

/**
 * Enemy anchors (wave-contract.md). `stopAt` obeys the REACH LAW: no enemy
 * halts beyond the shortest tier-1 relic range. Verified by a core test.
 */
export const ENEMIES: Record<string, EnemyDef> = {
  walker:   { kind: "walker",   hp: 20,  crossSeconds: 10, stopAt: 0,    damage: 5,  attackInterval: 1.0, isBoss: false },
  // The gunner stays squishy on purpose. Armouring it was tried against the
  // Beacon sitting untouched for 91% of every run, and it failed: it moved the
  // collapse earlier and shortened the run without changing the shape. The
  // fault was never this statline but the wave-1 gap between player throughput
  // and enemy health — see the floor in waves.ts.
  gunner:   { kind: "gunner",   hp: 15,  crossSeconds: 11, stopAt: 0.34, damage: 3,  attackInterval: 1.5, isBoss: false },
  // Boss damage per hit is cut roughly threefold from where it started, because
  // "arrives" and "kills" were fused: the only way to stop bosses ending runs
  // from full health was to stop them crossing at all. Low damage on a higher
  // health curve makes a boss wave cost Beacon health instead of the run.
  bulwark:  { kind: "bulwark",  hp: 400, crossSeconds: 18, stopAt: 0,    damage: 6,  attackInterval: 1.4, isBoss: true },
  splitter: { kind: "splitter", hp: 260, crossSeconds: 14, stopAt: 0,    damage: 4,  attackInterval: 1.2, isBoss: true },
  disruptor:{ kind: "disruptor",hp: 300, crossSeconds: 15, stopAt: 0.30, damage: 3,  attackInterval: 1.6, isBoss: true },
};

/**
 * How far each category reaches, and the CAP no buff may push it past.
 *
 * Reach is the categories' clearest identity and for a long time it did not
 * exist. Bolt ran 0.75-1.00 and Burst 0.70-0.80, so `burst_arc` at 0.80 out-
 * ranged `bolt_needle` at 0.75 — the bands overlapped almost entirely. A
 * playtest then took the range buff twice and had Burst relics hitting the
 * spawn line, which is Bolt's whole job.
 *
 * Bolt is the long arm. Construct holds the middle. Burst works at the wall,
 * and that is what makes it the category that wants an ultimate able to buy
 * distance back — the Titan's knockback is the answer to standing this close.
 *
 * The cap is what makes it a law rather than a starting value: buffs raise a
 * relic toward its category's limit and stop there.
 */
export const CATEGORY_REACH: Record<Category, { max: number }> = {
  Bolt:      { max: 1.00 },
  Construct: { max: 0.78 },
  Burst:     { max: 0.55 },
};


/**
 * Half the lane's width, in the same units as `pos`. The lane is drawn 560 by
 * 464, so it is about 1.2 deep-units wide and half of that is 0.6.
 *
 * Remnants have a real lateral position now. It used to be decoration derived
 * from the enemy id purely in the renderer, which is why every area weapon had
 * to hit the lane's full width: there was no across-the-lane to miss in.
 */
// Burst damage returned to roughly its original values when the cone shipped.
// It had been cut twice to pay for a slab that spanned the lane's full width —
// the geometry was the fault, not the numbers, and the cone limits the category
// honestly enough that the damage no longer has to.

/** The shortest reach anything in the pool has. Everything below derives from it. */
export const RELIC_MIN_REACH = Math.min(...RELICS.map((r) => r.tiers[0]!.range));

/**
 * Half the lane's width, in the same units as distance from the Beacon.
 *
 * It is not a free number. Reach is a RADIUS — the cone is a true sector, so a
 * Remnant is in reach when its distance from the Beacon is within range, not
 * when its depth is. A walker comes to rest against the wall at distance |x|,
 * so any walker resting further out than the shortest reach in the pool could
 * never be answered: it would grind the Beacon down where nothing could shoot
 * back. Tying the lane's width to that reach makes the failure impossible to
 * introduce by tuning.
 */
export const LANE_HALF_WIDTH = RELIC_MIN_REACH;

/**
 * How far across the lane a kind may spawn, given where it comes to rest.
 *
 * A walker rests at distance |x|. A gunner rests at |x| offset from a halt
 * 0.34 down the lane, so it rests at hypot(0.34, x) — further out than a walker
 * at the same column, and therefore allowed less room. Derived, so lowering any
 * relic's reach narrows the lane instead of quietly stranding an enemy outside
 * it.
 */
export function spawnSpanFor(stopAt: number): number {
  const room = RELIC_MIN_REACH ** 2 - stopAt ** 2;
  if (room <= 0) {
    throw new Error(
      `an enemy halting at ${stopAt} rests beyond the shortest reach ` +
      `(${RELIC_MIN_REACH}); it could never be shot`);
  }
  return Math.sqrt(room) * 0.94;   // a sliver of margin off the boundary
}

export const BEACON_HP = 100;
export const TICK_HZ = 30;

// ---------------------------------------------------------------------------
// Buffs — the EXP-bar rewards. Category-targeted, because the buff system IS
// the category system (economy.md). No trap picks: every buff stays live at
// every depth, which is why there is no EXP-gain buff and no level cap.
// ---------------------------------------------------------------------------
export type BuffKind =
  | { k: "damage"; category: Category; pct: number }
  | { k: "cooldown"; category: Category; pct: number }
  | { k: "range"; pct: number }
  | { k: "repair"; amount: number }
  | { k: "ult_damage"; pct: number }
  | { k: "ult_cooldown"; pct: number }
  | { k: "ult_size"; pct: number };

export interface BuffDef {
  readonly id: string;
  readonly label: string;
  readonly text: string;
  readonly effect: BuffKind;
}

const cat = (c: Category) => c;
export const BUFFS: readonly BuffDef[] = [
  { id: "dmg_bolt",  label: "Taut Thread",   text: "Bolt damage +25%",     effect: { k: "damage",   category: cat("Bolt"),      pct: 25 } },
  { id: "dmg_burst", label: "Wide Weft",     text: "Burst damage +25%",    effect: { k: "damage",   category: cat("Burst"),     pct: 25 } },
  { id: "dmg_con",   label: "Bound Servant", text: "Construct damage +25%",effect: { k: "damage",   category: cat("Construct"), pct: 25 } },
  { id: "cd_bolt",   label: "Quick Shuttle", text: "Bolt cooldown -15%",   effect: { k: "cooldown", category: cat("Bolt"),      pct: 15 } },
  { id: "cd_burst",  label: "Loose Knot",    text: "Burst cooldown -15%",  effect: { k: "cooldown", category: cat("Burst"),     pct: 15 } },
  { id: "cd_con",    label: "Restless Gear", text: "Construct cooldown -15%", effect: { k: "cooldown", category: cat("Construct"), pct: 15 } },
  { id: "range",     label: "Long Reach",    text: "Relic range +12%, to each category's limit", effect: { k: "range",    pct: 12 } },
  // The ultimate's own three. They stay live at every depth for the same
  // reason the others do: the ultimate is denominated in seconds of arsenal,
  // so a percentage of it never stops being worth a percentage.
  { id: "ult_dmg",   label: "Deep Draw",     text: "Ultimate damage +30%",   effect: { k: "ult_damage",   pct: 30 } },
  { id: "ult_cd",    label: "Short Tether",  text: "Ultimate cooldown -18%", effect: { k: "ult_cooldown", pct: 18 } },
  { id: "ult_size",  label: "Wide Cast",     text: "Ultimate reach +25%",    effect: { k: "ult_size",     pct: 25 } },
  { id: "repair",    label: "Mending",       text: "Repair the Beacon by 25", effect: { k: "repair", amount: 25 } },
];

// ---------------------------------------------------------------------------
// The three ultimates. Anchors only — the simulator owns the final values.
// ---------------------------------------------------------------------------
export const ULTIMATES: Record<UltimateId, UltimateDef> = {
  // Hunter. A handful of blades thrown down the lane, each landing on its own
  // fuse and bursting where it falls. Spread damage, and the only ultimate
  // that keeps working on enemies that are still far away.
  barrage: {
    id: "barrage", label: "Blade Barrage",
    text: "Five blades fall down the lane and burst where they land",
    // Blast radius 0.15, not 0.10. The cast's damage pool is SHARED by what a
    // blade catches, so a narrow blade dumps its whole share into one Remnant
    // and wastes the overkill. Widening spends the same pool on more of them.
    // Measured: Hunter's median depth 51 to 53.5, and flat again by 0.20 —
    // past that the blades are catching everything already.
    cooldown: 26, worthSeconds: 7, radius: 0.15, shots: 5, fuse: 0.5,
  },
  // Titan. A wave rolling out from the Beacon and up most of the lane,
  // throwing back everything it passes. The only ultimate that buys TIME
  // rather than only dealing damage.
  //
  // Its reach was 0.38 in the first build and the measurement was damning: the
  // competent bot cast it ZERO times on most waves, because the ability was
  // gated on Remnants being near the Beacon and the entire rest of the game
  // exists to stop that happening. An ultimate that only good play can never
  // use is not a defensive option, it is dead weight on the class carrying it.
  wave: {
    id: "wave", label: "Riven Wave",
    text: "A wave breaks from the Beacon and throws back what it passes",
    cooldown: 24, worthSeconds: 7, radius: 0.85, knockback: 0.20,
  },
  // Warden. A knot in the lane that drags the Remnants together and grinds
  // them for a few seconds. Worth the most damage of the three, but it pays
  // out over time rather than at once — and gathering the lane into one point
  // is what every Burst relic on the loom wants.
  vortex: {
    id: "vortex", label: "Knot",
    text: "A knot drags the lane together and grinds it for four seconds",
    cooldown: 28, worthSeconds: 7, radius: 0.14, duration: 4, pull: 0.05,
  },
};


// ---------------------------------------------------------------------------
// The classes. A class is exactly three things (loom-design.md): a starting
// relic, a loom shape, and an ultimate. Kept here rather than inline in the
// Run so the class-select screen and the run it starts cannot disagree about
// what a class is — the geometry lives in grid.ts and is read from there.
// ---------------------------------------------------------------------------
export interface ClassDef {
  readonly label: string;
  /** What the class asks the player to be good at. */
  readonly blurb: string;
  readonly startRelicId: string;
  readonly ultId: UltimateId;
}

export const CLASSES: Record<ClassId, ClassDef> = {
  hunter: {
    label: "Hunter", startRelicId: "bolt_needle", ultId: "barrage",
    blurb: "A tall loom and a single thread. Reaches the whole lane and kills what is furthest away first.",
  },
  titan: {
    label: "Titan", startRelicId: "burst_arc", ultId: "wave",
    blurb: "A wide loom and a heavy opening. Answers a crowd at the wall rather than preventing it.",
  },
  warden: {
    label: "Warden", startRelicId: "construct_turret", ultId: "vortex",
    blurb: "A square loom that wastes no rotation, and the smallest board of the three. Holds ground instead of clearing it.",
  },
};
