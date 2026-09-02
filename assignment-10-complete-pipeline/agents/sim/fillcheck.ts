import { simulate } from "./run.js";
for (const cls of ["hunter", "titan"] as const) {
  const r = simulate(cls, 4242, "competent", 150);
  console.log(`${cls}: depth ${r.depth} | cells ${r.cells}/40 | relics ${r.relics} | buffs ${r.buffs}`);
}
