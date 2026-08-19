# Junction Mechanics & Gate Specification — Echoes (GDD V2)

## Junction Behavior
- The junction is the emotional core of *"One map, two games"*.
- It is NOT a menu choice. The gate that responds to the player's class traversal tool opens organically.
- The opposite class gate stays visibly sealed with a distinct visual lock (grapple anchor target vs cracked reinforced wall).

## Gate Types & Reachability Requirements

| Gate Type | Required Tool | Reachability Validation Rule |
|---|---|---|
| **Grapple Gate** | Hunter Grapple Knife | Anchor point within 800u, with an unobstructed line to it. Hunter branch ONLY. |
| **Bash Wall** | Titan Charge Bash | Cracked destructible wall preceded by >= 250u `[TUNE]` of clear, level run-up on the same floor. Titan branch ONLY. |
| **Keycard Door** | Interaction Keycard | Keycard item placed in preceding room. Shared Segment A. |
| **Boss Door** | None (Pre-boss) | Immediately preceded by an adjacent Checkpoint room. |

## Why each rule exists

**The run-up is the bash.** The Charge Bash strikes from a standstill but only
breaks a wall at speed, so a wall with no floor in front of it is sealed to
everyone — a soft lock, not a gate. The distance is a legibility figure rather
than a physical one: full running speed arrives after 88 units
(`movement-reach.md`), and the rest exists so the space reads as asking for a
run-up before the player has been told it does. It was 400u; reduced because
room widths start at 2000 and a fifth of a small room is a high price for
legibility already achieved sooner.

**An anchor makes three promises, and placement must keep all three at once.**
Seen from the route, out of jumping reach, and **standable on arrival**: the pull
ends at the anchor, the Hunter comes down onto whatever is underneath, and that
surface needs a full body of clear space — found in play when a perch hung 60
under the ceiling and the pull ended with nowhere to stand. The three pull
against each other (tucking an anchor over its perch hides it; raising it past
200 above the landing turns arrival into an undecided fall), which is exactly
why placement is the design act.

**The clear line is the grapple.** An anchor behind geometry is decorative. The
range is 800u, and the segment from the Hunter's standing position to the
anchor must intersect nothing solid.

**Lift is not a gate tool.** It reaches exactly as high as the Hunter's double
jump and opens nothing; the Titan's only traversal key is the Charge Bash. Any
space described as "a shaft only the Titan can scale" is a leftover from an
earlier design and is wrong.

## Pockets use the same two keys

Optional pockets are gated by the same markers as branch gates, under the two
rules in `../01-classes/class-asymmetry-contract.md`: the space behind the key
must be reachable no other way, and it must be visible from ground the other
class can stand on. A pocket that is exclusive but invisible teaches the player
nothing; a pocket that is visible but reachable anyway is not a pocket.
