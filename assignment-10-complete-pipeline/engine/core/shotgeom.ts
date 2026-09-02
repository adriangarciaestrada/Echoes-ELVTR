/**
 * The outline of a shot's damage area, in LANE UNITS.
 *
 * Lives beside the hit test rather than in the renderer so the two cannot drift
 * apart. They did: the cone was drawn from the Weaver's chest while damage was
 * measured from its feet, 50px away — a fifth of a Burst relic's reach — so
 * Remnants inside the drawn cone took nothing and Remnants outside it were hit.
 *
 * Pure geometry: no Phaser, so `shotgeom.test.ts` can check the outline against
 * the very function that decides who is hurt.
 */
import { bearing, distance } from "./battle.js";

/** Points tracing a sector: apex at the origin, closed by an arc at `range`. */
export function conePolygon(aim: number, spread: number, range: number,
                            steps = 18): Array<[number, number]> {
  const pts: Array<[number, number]> = [[0, 0]];
  for (let k = 0; k <= steps; k++) {
    const b = aim - spread + (2 * spread * k) / steps;
    pts.push([Math.sin(b) * range, Math.cos(b) * range]);
  }
  return pts;
}

/** Is (x, pos) inside the polygon? Ray casting, for the test's benefit. */
export function inPolygon(pts: Array<[number, number]>, x: number, pos: number): boolean {
  let inside = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const [xi, yi] = pts[i]!, [xj, yj] = pts[j]!;
    if ((yi > pos) !== (yj > pos) && x < ((xj - xi) * (pos - yi)) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

/** Exactly the rule `battle.ts` applies when it decides who a cone hits. */
export function coneHits(aim: number, spread: number, range: number,
                         x: number, pos: number): boolean {
  return distance(x, pos) <= range && Math.abs(bearing(x, pos) - aim) <= spread;
}
