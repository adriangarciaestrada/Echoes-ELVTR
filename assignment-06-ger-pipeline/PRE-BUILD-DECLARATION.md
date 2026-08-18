# Pre-Build Declaration — Assignment #6

**Echoes** — a 2.5D metroidvania slice in Unreal Engine 5.8.

**Generated inconsistently:** room geometry. An agent writes a RoomSpec: the carved
cavity, its ledges and doors, the class pockets, and the ordered critical path.

**The rule:** `GDD-course-scope.md` §7.1, band 1 — "Clearability = 100%: every
class clears every room, branch, and boss at every bot profile; softlocks = 0.
Hard assertion, build-blocking." §5 adds its geometric half: "Neither class
out-jumps the other, so exclusivity comes from where anchors and cracked walls
are placed, never from raw reach."

**Failure, concretely:** the character jumps to the next ledge, 200 above and
inside the guaranteed band, and stops dead. That ledge is 40 thick, so the space
between them is 160 and the body is 176. Reach was satisfied; the body did not
fit. The generator, the gate and a human review all passed that room.
