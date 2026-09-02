/** When does the run start to threaten, and when does the loom stop mattering? */
import { simulate } from "./run.js";
const N = Number(process.argv[2] ?? 60);
const med = (xs: number[]) => xs.length ? xs.slice().sort((a,b)=>a-b)[Math.floor(xs.length/2)]! : NaN;
const rs = Array.from({ length: N }, (_, i) => simulate(i % 2 ? "hunter" : "titan", 7000 + i, "competent", 200));
const dmg = rs.map(r => r.firstDamageWave).filter((x): x is number => x !== null);
const epic = rs.map(r => r.fullEpicWave).filter((x): x is number => x !== null);
console.log(`depth              median ${med(rs.map(r => r.depth))}`);
console.log(`first damage taken median wave ${med(dmg)}  (${dmg.length}/${N} runs took any)`);
console.log(`board all-Epic     median wave ${epic.length ? med(epic) : "never"}  (${epic.length}/${N} runs)`);
// The shape metric: what fraction of a run happens before anything threatens
// the Beacon. Absolute wave numbers move whenever the curve is retuned; this
// does not, so it is the number worth aiming at.
const frac = rs.filter(r => r.firstDamageWave !== null && r.depth > 0)
  .map(r => r.firstDamageWave! / r.depth);
console.log(`QUIET FRACTION     ${(med(frac) * 100).toFixed(0)}% of the run passes untouched`);
