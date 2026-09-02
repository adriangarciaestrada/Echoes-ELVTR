import { simulate } from "./run.js";
import { BOSS_EVERY, TUNE_BOSS_EXP } from "../../engine/core/waves.js";
const RUNS = Number(process.argv[2] ?? 200);
const depths: number[] = [];
let onBoss = 0;
for (let i = 0; i < RUNS; i++) {
  const r = simulate(i % 2 ? "hunter" : "titan", 9000 + i, "competent", 200);
  depths.push(r.depth);
  if ((r.depth + 1) % BOSS_EVERY === 0) onBoss++;
}
const med = depths.sort((a, b) => a - b)[Math.floor(RUNS / 2)]!;
console.log(`bossExp ${TUNE_BOSS_EXP.toFixed(2)}  median depth ${String(med).padStart(3)}  ` +
  `boss deaths ${String(Math.round(onBoss / RUNS * 100)).padStart(3)}%  (chance = 20%)`);
