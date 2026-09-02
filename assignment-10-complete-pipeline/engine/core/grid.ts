/**
 * The Loom — a set of unlocked cells with relics packed into them.
 *
 * The board is NOT a rectangle: expansion cells are player-placed, so the
 * outline is a chosen shape (loom-grid.md). Unlocked cells are therefore a
 * set, not a width/height pair.
 */
import type { Footprint, PlacedRelic, RelicDef, Tier } from "./types.js";
import { MAX_TIER } from "./types.js";

export type Cell = readonly [number, number];
const key = (x: number, y: number) => `${x},${y}`;

export type ClassId = "hunter" | "titan" | "warden";

/**
 * Starting shapes: 13 cells each, centred in the same 7x7 envelope.
 *
 * The uniform board the market layout needs is kept; what comes back is the
 * class identity that the 3x3 opening had flattened. Hunter opens tall, Titan
 * wide, Warden as a symmetric diamond that fits every footprint in either
 * orientation — the same three characters the asymmetric envelopes used to
 * carry, now drawn in the opening hand instead of in the board's outline.
 *
 * Thirteen, not twelve, because 49 - 13 = 36 is divisible by 4 and 49 - 12 is
 * not; `expansionsToFill` asserts it. Nine cells was measured and rejected:
 * it cost every class a quarter to a half of its depth and pushed class spread
 * to 1.42x against a contract of 1.10x, because at nine cells the opening
 * relic's damage-per-cell decides the run and the three classes do not open
 * with equal relics.
 *
 * Each shape is connected and can reach all 49 by edge-adjacent expansion;
 * `grid.test.ts` holds both properties.
 */
export function startingCells(cls: ClassId): Cell[] {
  const out: Cell[] = [];
  const add = (x: number, y: number) => out.push([x, y]);
  if (cls === "hunter") {
    for (let y = 0; y < 7; y++) add(3, y);          // the full column
    for (const x of [2, 4]) for (const y of [2, 3, 4]) add(x, y);
  } else if (cls === "titan") {
    // Concave: the top and bottom ranks are notched. Those two gaps are the
    // only thing in the roster that a rotation cannot undo, which is what makes
    // this shape a different problem rather than a mirror of the Hunter's.
    for (const y of [1, 5]) { add(2, y); add(4, y); }
    for (let y = 2; y <= 4; y++) for (const x of [2, 3, 4]) add(x, y);
  } else {
    add(3, 1);                                       // a diamond of radius two
    for (const x of [2, 3, 4]) add(x, 2);
    for (let x = 1; x <= 5; x++) add(x, 3);
    for (const x of [2, 3, 4]) add(x, 4);
    add(3, 5);
  }
  return out;
}

/**
 * The envelope expansions may grow into.
 *
 * 49 cells = 9 starting + 4 x 10 expansions, EXACTLY. Any change here must
 * keep (w*h - 9) divisible by 4; `expansionsToFill` asserts it. (Was 12
 * starting on a per-class rectangle — see startingCells.)
 */
export function envelope(_cls: ClassId): { w: number; h: number } {
  return { w: 7, h: 7 };
}

export function expansionsToFill(cls: ClassId): number {
  const e = envelope(cls);
  const remaining = e.w * e.h - startingCells(cls).length;
  if (remaining % 4 !== 0) throw new Error(`envelope leaves ${remaining % 4} unplaceable cells`);
  return remaining / 4;
}

/** Rotate a footprint 90° clockwise n times, renormalised to origin. */
export function rotate(fp: Footprint, times: number): Footprint {
  let cells = fp.map(([x, y]) => [x, y] as const);
  for (let i = 0; i < ((times % 4) + 4) % 4; i++) {
    cells = cells.map(([x, y]) => [-y, x] as const);
  }
  const minX = Math.min(...cells.map((c) => c[0]));
  const minY = Math.min(...cells.map((c) => c[1]));
  return cells.map(([x, y]) => [x - minX, y - minY] as const);
}

export class Loom {
  readonly unlocked = new Set<string>();
  readonly relics: PlacedRelic[] = [];
  private nextUid = 1;

  constructor(readonly cls: ClassId) {
    for (const [x, y] of startingCells(cls)) this.unlocked.add(key(x, y));
  }

  isUnlocked(x: number, y: number): boolean {
    return this.unlocked.has(key(x, y));
  }

  occupant(x: number, y: number): PlacedRelic | undefined {
    return this.relics.find((r) => r.cells.some((c) => c[0] === x && c[1] === y));
  }

  get freeCellCount(): number {
    let used = 0;
    for (const r of this.relics) used += r.cells.length;
    return this.unlocked.size - used;
  }

  /** Cells a footprint would occupy if anchored at (ax, ay) with rotation. */
  resolve(fp: Footprint, ax: number, ay: number, rot: number): Cell[] {
    return rotate(fp, rot).map(([x, y]) => [x + ax, y + ay] as const);
  }

  canPlace(fp: Footprint, ax: number, ay: number, rot: number, ignoreUid?: number): boolean {
    return this.resolve(fp, ax, ay, rot).every(([x, y]) => {
      if (!this.isUnlocked(x, y)) return false;
      const occ = this.occupant(x, y);
      return !occ || occ.uid === ignoreUid;
    });
  }

  place(def: RelicDef, ax: number, ay: number, rot: number, tier: Tier = 0): PlacedRelic | null {
    if (!this.canPlace(def.footprint, ax, ay, rot)) return null;
    const relic: PlacedRelic = {
      uid: this.nextUid++,
      defId: def.id,
      tier,
      cells: this.resolve(def.footprint, ax, ay, rot),
      cooldownLeft: 0,
    };
    this.relics.push(relic);
    return relic;
  }

  /** Lift a relic off the board, keeping its identity for re-placement. */
  pickUp(uid: number): PlacedRelic | undefined {
    return this.remove(uid);
  }

  /** Put a lifted relic back down. Returns false if the spot is illegal. */
  putDown(relic: PlacedRelic, fp: Footprint, ax: number, ay: number, rot: number): boolean {
    if (!this.canPlace(fp, ax, ay, rot)) return false;
    relic.cells = this.resolve(fp, ax, ay, rot);
    relic.cooldownLeft = 0;
    this.relics.push(relic);
    return true;
  }

  remove(uid: number): PlacedRelic | undefined {
    const i = this.relics.findIndex((r) => r.uid === uid);
    return i >= 0 ? this.relics.splice(i, 1)[0] : undefined;
  }

  /** First legal placement anywhere, scanning the envelope. Used by auto-place. */
  findSpot(fp: Footprint, env: { w: number; h: number }): { x: number; y: number; rot: number } | null {
    for (let rot = 0; rot < 4; rot++)
      for (let y = 0; y < env.h; y++)
        for (let x = 0; x < env.w; x++)
          if (this.canPlace(fp, x, y, rot)) return { x, y, rot };
    return null;
  }

  /**
   * Merge b into a: same def, same tier, one tier up, occupying a's cells.
   * Returns false if the pair is not mergeable.
   */
  merge(aUid: number, bUid: number): boolean {
    const a = this.relics.find((r) => r.uid === aUid);
    const b = this.relics.find((r) => r.uid === bUid);
    if (!a || !b || a.uid === b.uid) return false;
    if (a.defId !== b.defId || a.tier !== b.tier || a.tier >= MAX_TIER) return false;
    this.remove(b.uid);
    a.tier = (a.tier + 1) as Tier;
    return true;
  }

  /**
   * Unravel: split the highest-tier relic above Common into two of the tier
   * below. The half that does not fit is LOST (bosses.md) — which is why an
   * empty cell is insurance.
   */
  unravelHighest(env: { w: number; h: number }): { split: boolean; lost: boolean } | null {
    const target = this.relics
      .filter((r) => r.tier > 0)
      .sort((x, y) => y.tier - x.tier)[0];
    if (!target) return null;

    const def = target.defId;
    const lowered = (target.tier - 1) as Tier;
    target.tier = lowered;

    const relicDef = { id: def, footprint: target.cells.map(([x, y]) => [x, y] as const) };
    // The clone reuses the same footprint shape, normalised.
    const minX = Math.min(...relicDef.footprint.map((c) => c[0]));
    const minY = Math.min(...relicDef.footprint.map((c) => c[1]));
    const shape: Footprint = relicDef.footprint.map(([x, y]) => [x - minX, y - minY] as const);

    const spot = this.findSpot(shape, env);
    if (!spot) return { split: true, lost: true };

    this.relics.push({
      uid: this.nextUid++,
      defId: def,
      tier: lowered,
      cells: rotate(shape, spot.rot).map(([x, y]) => [x + spot.x, y + spot.y] as const),
      cooldownLeft: 0,
    });
    return { split: true, lost: false };
  }

  /** Expansion: +4 player-placed cells, edge-adjacent, inside the envelope. */
  canExpandInto(x: number, y: number, env: { w: number; h: number }): boolean {
    if (x < 0 || y < 0 || x >= env.w || y >= env.h) return false;
    if (this.isUnlocked(x, y)) return false;
    return [[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) =>
      this.isUnlocked(x + dx!, y + dy!));
  }

  expand(x: number, y: number): void {
    this.unlocked.add(key(x, y));
  }
}
