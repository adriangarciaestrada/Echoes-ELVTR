# The Loom grid — geometry and class asymmetry

Owns every grid number. The asymmetry contract's law — exclusivity by
placement, never raw power — applied as shape.

## One board, three openings

The board is **7×7 = 49 for every class**, because the market layout reserves a
single fixed footprint for the loom. The asymmetry moved from the board's
outline into the opening hand: each class starts on **13 cells**, centred, in a
shape that is its own.

| | Hunter | Titan | Warden |
|---|---|---|---|
| Opening | 3×7, tall | 3×5, notched | 5×5 diamond |
| Full board | **7×7 = 49** | same | same |
| Per expansion | +4 cells, player-placed, edge-adjacent to unlocked | same | same |
| Expansions per run | 9 | same | same |

```
   Hunter        Titan         Warden
   ...#...       .......       .......
   ...#...       ..#.#..       ...#...
   ..###..       ..###..       ..###..
   ..###..       ..###..       .#####.
   ..###..       ..###..       ..###..
   ...#...       ..#.#..       ...#...
   ...#...       .......       .......
```

The Titan's shape is **concave**: the notches in its top and bottom ranks are
the only feature in the roster that a rotation cannot undo. An earlier version
made it a 7×3 — the Hunter's shape turned ninety degrees — which is not a
different problem at all, because pieces rotate freely and a mirror is not a
difference when the pieces can turn.

The Warden's diamond is symmetric on both axes, so a footprint that fits one
way fits the other and a rotation is never wasted — the same property the old
6×6 square carried.

**49 = 13 + 4×9 exactly, and that is a constraint, not a coincidence.** An
early envelope of 35 left three cells on a final expansion of four — a pending
cell with nowhere legal to go, and a run that could never leave the expansion
phase. Any change here must keep `(w×h − opening)` divisible by 4;
`expansionsToFill()` throws otherwise, and the run converts unplaceable pending
cells into buff choices as a second guard.

**Thirteen, not twelve**, only because 49 − 12 = 37 is not divisible by 4.

## Why not nine

The uniform revamp opened every class on a 3×3 and shipped unmeasured. Measured
afterwards at 200 runs per class, median depth with a bootstrap interval:

| Opening | Hunter | Titan | Warden | Class spread |
|---|---|---|---|---|
| 12 cells, asymmetric envelopes | 46 | 46 | 47.5 | 1.03× |
| 12 cells, uniform 6×6 | 47 | 44 | 47.5 | 1.08× |
| **9 cells, uniform 7×7** | **34** | **24** | **26** | **1.42×** |
| **13 cells, shapes above** | **44** | **44** | **46** | **1.05×** |

Nine cells cost every class between a quarter and a half of its depth and broke
the parity contract (≤1.10×, `wave-contract.md`) at 1.42×. The uniform *board*
was never the problem — the middle row shows uniformity holding parity fine. The
opening hand was: at nine cells the opening relic's damage-per-cell decides the
run, and the three classes do not open with equal relics (Hunter's
`bolt_needle` carries 8.33 damage-per-cell against Titan's `burst_arc` at 3.67).

## Placement exclusivity does not exist yet

The asymmetry contract puts exclusivity in placement. Measured
(`qa/placement.ts`), nothing is exclusive: **every relic fits every class's
opening**, and build divergence across classes sits at 0.03 out of 1 — the same
0.02 the old asymmetric envelopes produced, so this is not something the current
shapes lost.

The cause is structural rather than a matter of tuning:

- All nine relics fit inside a 3×3 bounding box.
- All three opening shapes contain the central 3×3 in full.

While both hold, no shape can exclude anything, whatever its outline. Changing
that needs one of two things: an opening that does **not** contain a complete
3×3, or a relic whose footprint does not fit in one.

Laws held in `laws.test.ts`: each shape is exactly 13 cells, connected, able to
expand into all 49, distinct from the other two, and centred on both axes.

Rules:
- A placed expansion cell is permanent for the run.
- Relics may be lifted and repacked freely during any market phase; nothing
  commits until Continue (`economy.md` owns the market).
- All three classes reach the same 49-cell maximum, and all three open on the
  same count; none ever has more cells than another — the difference is *where*
  they can put them, and what shape they must pack around on the way there.
  Asymmetry is placement, never power
  (`from-echoes/class-asymmetry-contract.md`).

## Deferred: constructs with a place on the battlefield

Constructs are, in the fiction, things the Weaver *puts down* — unlike Bolts and
Bursts, which come out of the Weaver. Giving them their own sprite and their own
spot beside the Weaver is the natural next step for the battlefield, and it
splits into two jobs of very different size.

**Visual only** — sprites drawn beside the Weaver, shots still leaving `(0, 0)`.
Hours, no core change, no balance risk. Coherent for constructs standing close
to the Weaver; incoherent for one in a corner, whose ring would still be born at
the Beacon.

**Real positions** — a day or two, plus re-measuring. Nothing has a battlefield
position today: `bearing()` and `distance()` both assume the origin, across
seven sites in `battle.ts` plus the renderer. Generalising them to an arbitrary
origin is tractable; the cost is that it is a balance change, not an art change.

Measured, for the orbiter (reach 0.60, ring pattern) — share of the lane it
covers from each origin:

| origin | lane covered |
|---|---|
| the Weaver, `(0, 0)` — today | 53.1% |
| beside the Weaver, `+0.2` | 44.6% |
| top-right corner | **30.1%** |

A corner costs it nearly half its coverage, because half the radius falls
outside the lane. That does not make it wrong — it makes it a different relic:
zone control high up the lane rather than defence of the Beacon. But the orbiter
was the roster's broken relic until its ring was implemented, and a corner takes
back more than the pattern gave. If this is done, do the near positions first,
where coverage barely moves, and measure before moving anything to a corner.
