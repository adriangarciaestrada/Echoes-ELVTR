import { expansionsToFill, envelope, startingCells } from "../../engine/core/grid.js";
for (const c of ["hunter", "titan"] as const) {
  const e = envelope(c);
  console.log(`${c}: ${e.w}x${e.h} = ${e.w * e.h} cells, start ${startingCells(c).length}, ` +
              `${expansionsToFill(c)} expansions of 4 — exact`);
}
