/**
 * The headless simulator. Same core the browser runs, with the frame cap
 * removed — which is what turns "wave 12 is fair" into a measurement.
 *
 *   npx tsx src/sim/run.ts [runs] [policy]
 */
import { Run } from "../../engine/core/run.js";
import type { ClassId } from "../../engine/core/grid.js";
import { playBuff, playExpansion, playMarket, playUlt, type PolicyName } from "./policy.js";

export interface RunReport {
  depth: number;          // wave reached (the score)
  firstDamageWave: number | null;  // when the Beacon is first touched
  fullEpicWave: number | null;     // when every relic is maxed
  battleSeconds: number;  // total in-battle time, excludes deliberation
  waveSeconds: number[];
  relics: number;
  cells: number;
  buffs: number;
}

export function simulate(cls: ClassId, seed: number, policy: PolicyName, maxWave = 200): RunReport {
  const run = new Run(cls, seed);
  const waveSeconds: number[] = [];
  let battleSeconds = 0;
  let firstDamageWave: number | null = null;
  let fullEpicWave: number | null = null;
  let lastBeacon = run.beaconHp;

  for (let guard = 0; guard < maxWave * 4; guard++) {
    if (run.phase === "over" || run.wave > maxWave) break;
    switch (run.phase) {
      case "market": {
        playMarket(run, policy);
        const b = run.startBattle();
        b.runToEnd(600, (bb) => playUlt(bb, policy));
        waveSeconds.push(b.elapsed);
        battleSeconds += b.elapsed;
        if (firstDamageWave === null && b.beaconHp < lastBeacon) firstDamageWave = run.wave;
        lastBeacon = b.beaconHp;
        run.endBattle();
        if (fullEpicWave === null && run.loom.relics.length >= 6 &&
            run.loom.relics.every((r) => r.tier >= 4)) fullEpicWave = run.wave;
        break;
      }
      case "buff": playBuff(run, policy); run.settlePhase(); break;
      case "expansion": playExpansion(run); run.settlePhase(); break;
      default: run.settlePhase();
    }
  }

  return {
    depth: run.wave - 1,
    firstDamageWave,
    fullEpicWave,
    battleSeconds,
    waveSeconds,
    relics: run.loom.relics.length,
    cells: run.loom.unlocked.size,
    buffs: run.buffs.length,
  };
}

function median(xs: number[]): number {
  const s = xs.slice().sort((a, b) => a - b);
  return s.length % 2 ? s[(s.length - 1) / 2]! : (s[s.length / 2 - 1]! + s[s.length / 2]!) / 2;
}

/**
 * The CLI, only when this file IS the command. Importing `simulate` used to run
 * the whole batch and print it, so every harness that reused the simulator
 * emitted lines that looked exactly like its own output — which is how a floor
 * sweep came back reading "median median 44".
 */
const isEntry = typeof process !== "undefined" &&
  !!process.argv[1] && /sim[\/\\]run\.ts$/.test(process.argv[1]);
if (isEntry) {
  const RUNS = Number(process.argv[2] ?? 200);
  const POLICY = (process.argv[3] as PolicyName) ?? "competent";

  for (const cls of ["hunter", "titan"] as const) {
    const reports = Array.from({ length: RUNS }, (_, i) => simulate(cls, 1000 + i, POLICY));
    const depths = reports.map((r) => r.depth);
    console.log(
      `${cls.padEnd(7)} ${POLICY.padEnd(10)} median depth ${String(median(depths)).padStart(4)}  ` +
      `p10 ${String(median(depths.slice(0, 0).concat(depths.slice().sort((a,b)=>a-b).slice(0, Math.max(1, Math.floor(RUNS*0.1))))))
        .padStart(3)}  ` +
      `max ${String(Math.max(...depths)).padStart(4)}  ` +
      `battle-time ${(median(reports.map((r) => r.battleSeconds)) / 60).toFixed(1)}min`);
  }

  // Wave-by-wave duration for one representative run: is any wave a cliff?
  const sample = simulate("hunter", 1234, POLICY);
  console.log("\nwave durations (hunter, seed 1234):");
  console.log(sample.waveSeconds.map((s, i) => `${i + 1}:${s.toFixed(0)}s`).join("  "));
}
