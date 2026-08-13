# Class Asymmetry & Balance Contract — Echoes (GDD V2)

## Principle: One Motor Vocabulary, Two Dialects
Every action verb lives on the **exact same button** for both classes, but the verb's execution and feel differ radically by class:

- **Button A (South):** Jump (Hunter: Double Jump vs Titan: Lift)
- **Button B (East):** Defense (Hunter: Dodge Roll vs Titan: Absorbing Shield)
- **Button X (West):** Traversal Tool (Hunter: Grapple Knife vs Titan: Charge Bash)
- **Button RT (Right Trigger):** Fire (Hunter: Semi-Auto vs Titan: Auto)
- **Button RB (Right Bumper):** Grenade (Hunter: Sticky Burst vs Titan: Area Pulse)

**Lift reaches exactly as high as the Hunter's double jump.** It is the Titan's
dialect of the jump, not a vertical advantage. Neither class out-jumps the
other; both share the figures in `../04-world/movement-reach.md`.

## Design Law: Asymmetry Budgets Difficulty, Never Possibility

**On the critical path, nothing is class-impossible.** Every room's route from
entrance to exit is passable by both classes on base movement alone, inside the
guaranteed band. That is the promise, and it is arithmetic rather than an
aspiration.

**Off the critical path, exclusivity is the point.** Optional pockets are
deliberately closed to one class. That is not a violation of the law above: the
law governs *completion*, not access to everything. Two runs are different
games precisely because each leaves something behind.

## Traversal Asymmetry: Placement, Not Verbs

The two traversal tools differ neither by axis nor by distance. Both are keyed
to a marked piece of geometry, and **the asymmetry is created by where those
markers are placed**, not by what the verbs can do:

| | Marker | Geometric precondition | Effect |
|---|---|---|---|
| **Hunter — Grapple Knife** | anchor point | clear line to it, within 800u | pulls the Hunter **to** the anchor |
| **Titan — Charge Bash** | cracked wall | clear run-up in front, 250u `[TUNE]` | **opens** the wall |

The grapple fires in any direction, so it grants horizontal reach as readily as
vertical. What makes a space Hunter-exclusive is not the direction of the pull;
it is that no other route in exists.

Two rules bind the Level Designer:

1. **Exclusive.** An anchor must lead somewhere the Titan cannot reach *by any
   means* — not merely somewhere awkward. A cracked wall must seal a space with
   no other entrance, which it does by construction: the Hunter has no breaking
   verb at all, by design.
2. **Visible.** Both must be seen from ground the other class can stand on. A
   pocket nobody knows they missed motivates nothing; the point is that the
   player registers what this run cannot have and wants the other class for it.
   This is the visibility rule of GDD §2.2, applied to pockets.

Exclusive but visible. Both halves are checkable against the geometry: no
base-movement route into the pocket from the shared route, and an unobstructed
sight line to it from that route.

**The Charge Bash is charged.** From a standstill it strikes but does not break;
it opens a wall only at speed. That is what gives the Titan's key a geometric
requirement of its own — a wall demands floor in front of it, exactly as an
anchor demands clear space up to it. Between them the two keys are what stop
rooms collapsing into corridors: each obliges the room to afford an axis. The
run-up figure is a legibility choice rather than a physical one; the character
reaches full speed in 88 units, and the remaining distance exists so the space
reads as asking for a run-up.

## Asymmetric Friction
- Proximity Bomber punishes slow Titan; trivial for Hunter.
- Blink Tank punishes dodge-reliant Hunter; tested by Titan shield.
- Shieldbearer is hopped over by Hunter, broken through by Titan.

## Boss Adaptation
- La Costurera sharpens *her* predictive volleys against Hunter.
- La Costurera commands her *knights* to flank against Titan.
