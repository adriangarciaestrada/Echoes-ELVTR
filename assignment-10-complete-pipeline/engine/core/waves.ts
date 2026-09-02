/**
 * The escalation curve. An endless game cannot ship a finite wave list
 * (wave-contract.md), so waves are generated: count rises continuously as the
 * primary pressure, HP and speed rise more slowly, and the walker/gunner mix
 * shifts as the run deepens. Attack values scale slower than count, because
 * rising damage kills runs abruptly and rising numbers kill them legibly.
 */
import type { SpawnGroup, WaveSpec } from "./types.js";

export const BOSS_EVERY = 5;

/**
 * Enemy health growth. EXPONENTIAL on purpose: the player's power is
 * multiplicative — more cells x higher tiers x stacking buffs — so linear
 * health scaling loses to it permanently. The first version grew roughly
 * linearly and the simulator reported a median depth of 146 with wave
 * durations flat at 20s: waves stopped being a threat and simply became
 * longer piles. TUNE_HP_BASE is the single knob; the simulator owns its value.
 */
// core/ runs in BOTH the browser and Node, so it may not touch environment
// globals unguarded. Reading process.env directly here shipped a browser that
// threw "process is not defined" on load while every Node-side test passed.
const ENV_BASE = typeof process !== "undefined"
  ? Number((process as { env?: Record<string, string | undefined> }).env?.LOOM_HP_BASE)
  : Number.NaN;
// 1.058, not 1.05. Implementing the ring and line hit patterns gave the roster
// real power it had never had — relics that had always struck one enemy began
// striking the 1.5 to 5.8 they were written to strike — and median depth went
// 48.5 to 78.0. That power is correct and staying; the curve is the dial that
// prices it, and pricing it here keeps the relic-by-relic balance that the
// patterns just bought. [TUNE]
export const TUNE_HP_BASE = Number.isFinite(ENV_BASE) && ENV_BASE > 0 ? ENV_BASE : 1.058;

/**
 * The floor, kept separate from the rate, because they fix different faults.
 *
 * The rate decides how long a run lasts; the floor decides how much of that run
 * is spent under threat. Enemy health grows at roughly the rate the player's
 * power does, so whatever gap exists at wave 1 persists for most of the run and
 * closes only at the very end. Starting the player far above the curve is what
 * produced a Beacon that sat untouched for 91% of every run and then died in
 * three waves. Raising the rate instead does bring pressure forward, but it
 * ends runs at wave 19, and depth is the score here.
 */
const ENV_LEVEL = typeof process !== "undefined"
  ? Number((process as { env?: Record<string, string | undefined> }).env?.LOOM_HP_LEVEL)
  : Number.NaN;
export const TUNE_HP_LEVEL = Number.isFinite(ENV_LEVEL) && ENV_LEVEL > 0 ? ENV_LEVEL : 2.8;
export function hpScale(wave: number): number {
  return TUNE_HP_LEVEL * TUNE_HP_BASE ** (wave - 1);
}

/**
 * Bosses scale MORE SLOWLY than trash, and the difference is not cosmetic.
 * A wave of trash is a throughput problem spread over eighteen seconds; a boss
 * is one concentrated pool that must be deleted before it crosses. Scaling
 * both at the same rate made bosses the only thing that ever killed a run —
 * measured at 98% of deaths on boss waves against the 20% chance would give,
 * which turns four waves in five into decoration.
 */
const ENV_BOSS = typeof process !== "undefined"
  ? Number((process as { env?: Record<string, string | undefined> }).env?.LOOM_BOSS_EXP)
  : Number.NaN;
export const TUNE_BOSS_EXP = Number.isFinite(ENV_BOSS) && ENV_BOSS > 0 ? ENV_BOSS : 0.90;
export function bossHpScale(wave: number): number {
  return hpScale(wave) ** TUNE_BOSS_EXP;
}
/**
 * The gunner gets its own health curve: a large early multiplier on an exponent
 * BELOW one, so it starts tanky and is slowly overtaken by the player's growth.
 *
 * Why the shape is inverted from the boss curve. Relic range covers 0.55-1.0
 * and enemies enter the lane at 1.0, so the whole arsenal fires from the first
 * second of a wave. Under a single shared health curve every enemy therefore
 * dies at the far edge until the power ratio crosses one, at which point the
 * whole wave lands at once. The probe measured exactly that: closest approach
 * held at 0.79-0.90 for forty-six waves, then went 0.41, 0.02, 0.00, and the
 * Beacon took its first damage on wave 52 of a run that ended on wave 54.
 *
 * A flat health rise for the gunner did not fix it - it moved the cliff earlier
 * and shortened the run, leaving the quiet stretch at the same ~82% of every
 * run, because two exponentials still cross exactly once. Front-loading the
 * multiplier instead makes gunners arrive while the player is weak, which is
 * what the contract means by "a throughput race that begins early", and the
 * sub-one exponent stops that race from becoming the only thing that kills a
 * run: late waves outgrow the gunner and end on walkers reaching the wall.
 */
const envNum = (key: string): number =>
  typeof process !== "undefined"
    ? Number((process as { env?: Record<string, string | undefined> }).env?.[key])
    : Number.NaN;
const tune = (key: string, fallback: number): number => {
  const v = envNum(key);
  return Number.isFinite(v) && v > 0 ? v : fallback;
};
export const TUNE_GUNNER_MULT = tune("LOOM_GUNNER_MULT", 4);
export const TUNE_GUNNER_EXP = tune("LOOM_GUNNER_EXP", 0.75);
export function gunnerHpScale(wave: number): number {
  return TUNE_GUNNER_MULT * hpScale(wave) ** TUNE_GUNNER_EXP;
}

const GUNNERS_FROM = 3;

export function waveSpec(wave: number): WaveSpec {
  const spawns: SpawnGroup[] = [];

  // Count is the primary pressure: gentle start, steady climb.
  const total = Math.round(4 + wave * 1.6 + wave ** 1.35 * 0.35);
  const gunnerShare = wave < GUNNERS_FROM ? 0 : Math.min(0.45, 0.10 + (wave - GUNNERS_FROM) * 0.02);
  const gunners = Math.round(total * gunnerShare);
  const walkers = total - gunners;

  const window = Math.min(18, 8 + wave * 0.25);
  if (walkers > 0) spawns.push({ kind: "walker", count: walkers, fromS: 0, overS: window });
  if (gunners > 0) spawns.push({ kind: "gunner", count: gunners, fromS: 2, overS: window - 1 });

  if (wave % BOSS_EVERY === 0) {
    const kinds = ["bulwark", "splitter", "disruptor"] as const;
    const kind = kinds[((wave / BOSS_EVERY - 1) % kinds.length + kinds.length) % kinds.length]!;
    spawns.push({ kind, count: 1, fromS: 3, overS: 0 });
    // Past wave 25 a second boss joins.
    if (wave >= 25) {
      const other = kinds[(kinds.indexOf(kind) + 1) % kinds.length]!;
      spawns.push({ kind: other, count: 1, fromS: 8, overS: 0 });
    }
  }

  return {
    wave,
    spawns,
    hpScale: +hpScale(wave).toFixed(3),
    bossHpScale: +bossHpScale(wave).toFixed(3),
    gunnerHpScale: +gunnerHpScale(wave).toFixed(3),
    speedScale: +Math.min(1.9, 1 + (wave - 1) * 0.018).toFixed(3),
  };
}
