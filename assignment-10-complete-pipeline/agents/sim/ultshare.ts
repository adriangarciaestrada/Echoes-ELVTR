/**
 * What the ultimate is actually worth, wave by wave: how often it can be cast
 * and what share of the wave's damage it accounts for. The design target is a
 * curve that starts high and decays without reaching zero — powerful when the
 * loom is thin, one tool among many once the loom is full.
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
    b.runToEnd(600, (bb) => playUlt(bb, "competent"));
    const relic = [...b.damageByRelic.values()].reduce((a, c) => a + c, 0);
    const share = b.ultDamage / Math.max(1, relic + b.ultDamage);
    rows.push(`${String(run.wave).padStart(3)} ${run.wave % 5 === 0 ? "BOSS" : "    "}` +
      ` ${b.elapsed.toFixed(0).padStart(2)}s  casts ${b.ultCasts}` +
      `  ult share ${(share * 100).toFixed(0).padStart(3)}%` +
      `  ultBuffs ${run.buffs.filter((x) => x.effect.k.startsWith("ult")).length}`);
    run.endBattle();
  } else if (run.phase === "buff") {
    // LOOM_ULT_BUFFS=1 makes the bot invest in the ultimate whenever it can,
    // which is the comparison that matters: the ultimate's share of a wave
    // falls on its own as waves grow, and the buffs are the only thing a
    // player can spend to hold it up.
    const c = run.buffChoices();
    const pick = process.env.LOOM_ULT_BUFFS
      ? c.find((x) => x.effect.k.startsWith("ult")) : undefined;
    if (pick) { run.takeBuff(pick); } else { playBuff(run, "competent"); }
    run.settlePhase();
  }
  else if (run.phase === "expansion") { playExpansion(run); run.settlePhase(); }
  else run.settlePhase();
}
console.log(rows.join("\n"));
