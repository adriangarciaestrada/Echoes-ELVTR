/** One line per configuration; the sweep runs this as a subprocess so each
 *  value of LOOM_HP_BASE is read fresh at module load. */
import { simulate } from "./run.js";
import { TUNE_HP_BASE } from "../../engine/core/waves.js";
const med = (xs: number[]) => { const s = xs.slice().sort((a, b) => a - b);
  return s.length % 2 ? s[(s.length-1)/2]! : (s[s.length/2-1]! + s[s.length/2]!)/2; };
const RUNS = Number(process.argv[2] ?? 40);
const comp = Array.from({ length: RUNS }, (_, i) => simulate("hunter", 2000 + i, "competent", 150));
const rand = Array.from({ length: RUNS }, (_, i) => simulate("hunter", 2000 + i, "random", 150));
const c = med(comp.map(r => r.depth)), r = med(rand.map(r => r.depth));
const p10 = comp.map(x=>x.depth).sort((a,b)=>a-b)[Math.floor(RUNS*0.1)] ?? 0;
console.log(`${TUNE_HP_BASE.toFixed(2)}  competent ${String(c).padStart(4)}  random ${String(r).padStart(4)}  ` +
  `gradient ${(c/Math.max(1,r)).toFixed(2)}x  p10 ${String(p10).padStart(3)}  ` +
  `battle ${(med(comp.map(x=>x.battleSeconds))/60).toFixed(1)}min`);
