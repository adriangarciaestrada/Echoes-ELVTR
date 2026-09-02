/** Data contracts. Mirrors loom-vault/relic-contract.md and wave-contract.md. */

export type Category = "Bolt" | "Burst" | "Construct";
export type Stacking = "stacks" | "one_of";

/** Five tiers: White Common → Green → Blue → Purple → Yellow Epic. */
export const TIERS = ["White", "Green", "Blue", "Purple", "Yellow"] as const;
export type Tier = 0 | 1 | 2 | 3 | 4;
export const MAX_TIER: Tier = 4;

/** Cell offsets from an anchor. Rotation is the player's, never baked in. */
export type Footprint = ReadonlyArray<readonly [number, number]>;

export interface TierStats {
  readonly damage: number;
  readonly cooldown: number;   // seconds
  readonly range: number;      // fraction of lane length
  /** Ultimates only: blast radius in lane units, measured in two dimensions. */
  readonly radius?: number;
  /**
   * Burst only: HALF-ANGLE of the cone, in radians. Burst fires a cone whose
   * tip is the Beacon, so it widens with distance the way a shot leaving a
   * barrel does. It replaced a slab that spanned the lane's whole width at a
   * fixed depth — geometry that made Burst hit nearly everything at its range
   * and was the single largest cause of the category dominating.
   */
  readonly spread?: number;
  readonly effect?: string;
}

/**
 * Who a shot lands on. `combat-model.md` gives Construct "its own spec — the
 * orbiter strikes what it passes; the turret picks like a Bolt", and neither
 * half of that was implemented: every non-Burst relic hit exactly one enemy, so
 * a five-cell orbiter did a one-cell relic's job.
 *
 *   single  the chosen target, and nothing else
 *   cone    a sector with its tip at the Beacon (Burst)
 *   ring    everything within reach, no aim — the orbiter's sweep
 *   line    the target and whatever stands behind it (pierce)
 */
export type HitPattern = "single" | "cone" | "ring" | "line";

export interface RelicDef {
  readonly id: string;
  readonly category: Category;
  readonly footprint: Footprint;
  readonly stacking: Stacking;
  readonly tiers: readonly TierStats[];
  /** Overrides the pattern implied by category and effect. */
  readonly pattern?: HitPattern;
}

export type EnemyKind = "walker" | "gunner" | "bulwark" | "splitter" | "disruptor";

export interface EnemyDef {
  readonly kind: EnemyKind;
  readonly hp: number;
  readonly crossSeconds: number;   // lane traversal at base speed
  readonly stopAt: number;         // 0 = the Beacon; >0 halts that far up the lane
  readonly damage: number;
  readonly attackInterval: number; // seconds
  readonly isBoss: boolean;
}

export interface SpawnGroup {
  readonly kind: EnemyKind;
  readonly count: number;
  readonly fromS: number;
  readonly overS: number;
}

export interface WaveSpec {
  readonly wave: number;
  readonly spawns: readonly SpawnGroup[];
  readonly hpScale: number;
  readonly bossHpScale: number;
  readonly gunnerHpScale: number;
  readonly speedScale: number;
}

/** A relic instance placed on the loom. */
export interface PlacedRelic {
  readonly uid: number;
  readonly defId: string;
  tier: Tier;
  /** Absolute cells it occupies, after rotation and placement. */
  cells: ReadonlyArray<readonly [number, number]>;
  cooldownLeft: number;
}

// ---------------------------------------------------------------------------
// Ultimates — the only live input in a battle (reference-game.md), one per
// class, on a cooldown. Manual at every speed: choosing 10x is choosing to
// give this up, which combat-model.md keeps emergent rather than enforced.
// ---------------------------------------------------------------------------
export type UltimateId = "barrage" | "wave" | "vortex";

export interface UltimateDef {
  readonly id: UltimateId;
  readonly label: string;
  readonly text: string;
  /** Seconds before it can be cast again. Starts ready at every wave. */
  readonly cooldown: number;
  /**
   * Damage is denominated in SECONDS OF THE PLAYER'S OWN ARSENAL, never a flat
   * number. A flat ultimate decays into irrelevance against a health curve that
   * compounds, which would quietly turn every ultimate buff into a trap pick —
   * and the buff pool is required to hold no trap picks (economy.md). Scaling
   * on the loom instead keeps the ultimate worth casting at wave 5 and wave 50,
   * and keeps it a reward for the pattern the player actually wove.
   */
  readonly worthSeconds: number;
  /** Lane fractions the effect covers. */
  readonly radius: number;
  /** barrage: how many blasts, and the fuse before the first lands. */
  readonly shots?: number;
  readonly fuse?: number;
  /** wave: lane fractions it throws what it catches, away from the Beacon. */
  readonly knockback?: number;
  /** vortex: seconds it persists and lane fractions per second it drags. */
  readonly duration?: number;
  readonly pull?: number;
}

/** An ultimate after the run's buffs have been applied to it. */
export interface UltStats {
  readonly cooldown: number;
  readonly worthSeconds: number;
  readonly radius: number;
  readonly duration: number;
}
