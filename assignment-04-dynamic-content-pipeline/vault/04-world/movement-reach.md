# Movement Reach — Echoes

What the character can actually reach with base movement. Every figure below is
either measured in play or derived from a measured quantity; none is a guess.
These numbers bound room geometry: a support placed beyond them is not "hard",
it is closed.

**Derived from `DT_GameFeel`.** They are a consequence of `JumpZVelocity`,
`GravityScale`, `JumpMaxCount`, `WalkSpeed` and `MaxAcceleration`. Change a
value in the table and these figures move — recompute them before designing
against them.

*Measured 2026-08-05 in play, at `JumpZVelocity` 700 and `GravityScale` 2.*

## Vertical

| Quantity | Value | Basis |
|---|---|---|
| Standing height | 90.15 | read in play |
| **Single jump** | **125.0** | apex reconstructed from two samples on the arc, agreeing to two decimals |
| Second jump behaviour | **sets** upward velocity to 700, does not add to it | measured 576.19 in flight where an additive model predicts ~1218 |
| **Double jump, ceiling** | **250.0** | only with the second jump released exactly at apex |
| Double jump, as actually executed | 211.4 | one real attempt, second jump fired ~39 units early |

## Horizontal

| Quantity | Value | Basis |
|---|---|---|
| In-air horizontal speed | **600, constant** | measured in flight; `FallingLateralFriction` is 0, so nothing decays it |
| **Flat gap, single jump** | **428.6** | mid-flight position predicted 164.5, measured 164.51 |
| Flat gap, double jump ceiling | ~730 | same model, perfect apex timing |
| **Run-up to full speed** | **88** | from `MaxAcceleration` 2048 |

**Every gap needs a run-up.** In-air speed is whatever the character carried off
the edge. A ledge placed flush against a gap is a trap however well the
distances work out: without roughly 88 units of floor before it, the jump falls
short, and from a standstill the crossable gap is zero.

## The three bands

The ceilings are measurement. The cuts between bands are judgment, and are the
numbers most worth arguing about — they decide where "hard" becomes "closed".

| | Guaranteed | Skill | Closed to base movement |
|---|---|---|---|
| **Vertical** | ≤ 200 | 200 – 250 | > 250 |
| **Horizontal gap** | ≤ 380 | 380 – 730 | > 730 |

- **Guaranteed** is where the critical path lives. Anything here is passable by
  anyone, which is what makes the clearability promise true rather than hoped
  for.
- **Skill** is the soft lock: passable, but it asks for timing. Optional
  rewards belong here. Nothing mandatory does.
- **Closed** is not a harder version of skill. It is unreachable, and the only
  way in is a class key — which is a placement decision, not a consequence of
  distance. See `../01-classes/class-asymmetry-contract.md`.

The vertical cut sits at 200 because 250 demands releasing the second jump
within a few frames of apex. The horizontal cut sits at 380 because the
character has to land on the platform, not at its lip.
