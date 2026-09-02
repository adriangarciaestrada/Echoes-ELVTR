/**
 * Where do runs actually end? The "no wall" gate (wave-contract.md) asks
 * whether any wave craters survival relative to its neighbours. Boss waves
 * are every 5th, so if deaths cluster on multiples of 5 the bosses are a
 * cliff rather than a spike.
 */
import { simulate } from "./run.js";
import { BOSS_EVERY } from "../../engine/core/waves.js";

const RUNS = Number(process.argv[2] ?? 300);
const deaths = new Map<number, number>();
for (let i = 0; i < RUNS; i++) {
  const r = simulate(i % 2 ? "hunter" : "titan", 9000 + i, "competent", 200);
  // depth = last wave cleared, so the killing wave is depth + 1
  deaths.set(r.depth + 1, (deaths.get(r.depth + 1) ?? 0) + 1);
}

const waves = [...deaths.keys()].sort((a, b) => a - b);
const onBoss = [...deaths.entries()].filter(([w]) => w % BOSS_EVERY === 0)
  .reduce((a, [, n]) => a + n, 0);
console.log(`runs ${RUNS} · died on a boss wave: ${onBoss} (${(onBoss / RUNS * 100).toFixed(0)}%)`);
console.log(`if bosses were no harder than any other wave, expect ~${(100 / BOSS_EVERY).toFixed(0)}%\n`);

console.log("wave  deaths");
for (const w of waves) {
  const n = deaths.get(w)!;
  console.log(`${String(w).padStart(4)}${w % BOSS_EVERY === 0 ? " B" : "  "} ${"#".repeat(n)} ${n}`);
}
