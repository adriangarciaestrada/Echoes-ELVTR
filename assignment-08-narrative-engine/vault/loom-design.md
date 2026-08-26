# The Loom — design overview

The Echoes spin-off and course capstone: a web inventory autobattler in the
same universe, under the same law. This note owns the pitch and the loop —
**no numbers live here**; every number has exactly one owner note, listed in
`00-index.md`.

**One line:** a Weaver stands at a Beacon and arranges Architect relics on a
Loom; the pattern fights the Remnants coming down the lane, and the lane
never stops.

**Platform:** Phaser 3, browser, no install. Runtime makes zero LLM calls;
agents and PixelLab are build-time only. The battle core is a pure module the
game and the simulator share (`combat-model.md` — the architecture law).

## The loop

```
BATTLE (auto, one manual super)  →  MARKET + LOOM (all decisions)  →  …  wave 10
```

Battle is automatic and deterministic; the player steers a run through
packing, merging, rerolling, pool-thinning, and expansion placement. Merging
is deliberately lossy — space and effects, never raw damage — which is the
single rule the whole game leans on (`relic-contract.md`, law 1).

## The classes

Same law as always: exclusivity by placement, never raw power. All three
classes reach the same depth; the difference is the shape of the decisions.

| | Hunter | Titan | Warden |
|---|---|---|---|
| Loom | tall, 5x8 | wide, 8x5 | square, 6x6 |
| Cells | 40 = 12 + 4x7 | 40 = 12 + 4x7 | **36** = 12 + 4x6 |
| Starting relic | small Bolt | large Burst | Construct turret |
| Ultimate | **Blade Barrage** — five blades down the lane, each bursting where it lands | **Riven Wave** — breaks from the Beacon, throwing back what it catches | **Knot** — drags the lane together and grinds it for four seconds |
| Shape of it | spread, reaches the whole lane | sweeps out from the Beacon, throws back | sustained, holds a chokepoint |
| Cooldown | 26s | 24s | 28s |

The Warden finishes on the smallest board of the three and is not weaker for
it: a square loom never wastes a rotation, because every footprint that fits
one way fits the other. It opened on 16 cells in the first build and measured
**73% of the run untouched** against the others' 19-20% — a bigger opening hand
compounds through every merge after it — so all three now open on 12.

**All three ultimates are worth the same 7 seconds of the raw loom.** Only the
shape differs, and the shape is worth more than the number: see the sustained-
versus-burst measurement in `combat-model.md`.

A class is exactly three things: **starting relic, loom shape, and ultimate.** The ultimate matters most — it is the only live input in combat, so it is the strongest identity the class has.

Geometry and numbers: `loom-grid.md`.

## The arc

**Endless.** Waves escalate without a ceiling; a boss every fifth wave; the
run ends when the Beacon breaks, and the wave reached is the score. The
progression the player feels happens between runs — early deaths are shallow
because the packing is bad, and thirty runs later they are not. That curve is
the product, so the game never caps it (`wave-contract.md`, `bosses.md`).

## Non-goals

No meta-progression, no trap picks, no second lane, no runtime AI.
