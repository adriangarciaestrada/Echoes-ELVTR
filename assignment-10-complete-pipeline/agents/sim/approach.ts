/**
 * Is the leak a cliff or a ramp? Reports, per wave, how close the deepest enemy
 * got to the Beacon (1 = spawn edge, 0 = at the wall) and what it cost in HP.
 * A healthy endless curve leaks a little for many waves; a cliff means the wave
 * is either fully contained or fully lost, with nothing in between.
 */
import { Run } from "../../engine/core/run.js";
import type { ClassId } from "../../engine/core/grid.js";
import { playBuff, playExpansion, playMarket, playUlt } from "./policy.js";

const cls = (process.argv[2] as ClassId) ?? "hunter";
const seed = Number(process.argv[3] ?? 1234);
const run = new Run(cls, seed);
const rows: string[] = [];

for (let guard = 0; guard < 900; guard++) {
  if (run.phase === "over") break;
  if (run.phase === "market") {
    playMarket(run, "competent");
    const b = run.startBattle();
    const before = b.beaconHp;
    let closest = 1;
    while (!b.finished) {
      playUlt(b, "competent");
      b.tick();
      for (const e of b.enemies) if (e.pos < closest) closest = e.pos;
    }
    const took = before - b.beaconHp;
    rows.push(`${String(run.wave).padStart(3)} ${run.wave % 5 === 0 ? "BOSS" : "    "}` +
      ` closest ${closest.toFixed(2)}  took ${String(took).padStart(4)}` +
      `  beacon ${String(Math.max(0, b.beaconHp)).padStart(4)}/${run.beaconMax}` +
      `  gold ${String(run.gold).padStart(4)}`);
    run.endBattle();
  } else if (run.phase === "buff") { playBuff(run, "competent"); run.settlePhase(); }
  else if (run.phase === "expansion") { playExpansion(run); run.settlePhase(); }
  else run.settlePhase();
}
console.log(rows.join("\n"));
