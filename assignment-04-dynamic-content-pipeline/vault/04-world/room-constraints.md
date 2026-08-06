# Room Design Constraints — Echoes (GDD V2)

What a good room is, distilled from GDD §2.1, §2.2, §2.4 and §5. The shape a
room may take is `roomspec.md`; the distances it must respect are
`movement-reach.md`. This note holds the part neither of those can: what the
room is *for*.

## Dimensions

- **Width** 2000 (small corridor) to 6000 (large arena); **height** 1000 (flat
  passage) to 3000 (vertical shaft). Measured on the cavity's extent.
- Depth is frozen. Every walkable surface lies on the X/Z plane.
- Camera bounds are not authored — they are computed from the cavity. The camera
  is an author-controlled 2.5D follow; the player never rotates it.

## The 30-second room loop: FLOW → READ → FRICTION → MARK

Every room is a beat, and the beat has four parts. A room missing one is either
a corridor or an arena, and the slice wants neither.

- **Flow** — movement is the constant reward. Rooms are built to be crossed
  fluidly with the class verbs. What gets punished is *sloppy* movement, never
  slow decision-making: no room may require haste to survive.
- **Read** — the room's primary question is navigational: **where does my class
  go here?** It must be answerable by looking. Ledges and anchors read as Hunter
  routes, cracked walls as Titan ones, and enemies and lore register on the same
  glance.
- **Friction** — an encounter interrupts flow and taxes sloppiness. Combat is
  friction *along* the route, never the destination of the room.
- **Mark** — the beat closes on something registered: the exit, a lore node, a
  checkpoint, or a **legibly impossible gate** noted for later.

**Bands:** combat rooms 20–45 s, pure traversal rooms ≤20 s `[TUNE]`.

## Dense over large

Segment A is 5–7 rooms plus the tutorial area and the junction; Segment B is 3–5
per branch. That is the entire world, so **a room earns its size by what happens
in it, not by how far it stretches**. A long room with two ledges is worse than
a short one with four.

The practical consequence: stack space vertically and fold it back on itself
rather than extending it sideways. A room crossed in a straight line has spent
its budget on distance.

## The visibility rule

*Binds this agent directly.* The player must be shown what they cannot have.

- At the junction, **both** branch gates are in frame: one opens to the player's
  key, the other stays sealed and legibly class-locked. That is the question
  that makes a second run exist.
- In Segment A, optional pockets **show a reward only the other class can
  claim** — 2–3 across the whole segment.
- At the convergence, the other branch's exit door is visible.

What must be visible is the **lock**, not the prize: the anchor above the ledge,
the cracked wall beside the chamber. A cache is occluded by whatever holds it;
the key is what the player reads and remembers.

## Checkpoints

*Binds this agent directly.*

- One at the tutorial exit, one at the junction, one at the branch convergence,
  one at the boss door.
- **No stretch of any route exceeds 4 rooms without one** `[TUNE]`.
- Every gate is preceded by an adjacent checkpoint.
- Every checkpoint is reachable *and* exitable for the active class — never
  stranded past a point of no return.
- Checkpoint rooms hold **zero** enemies, and restore health fully.

## No mandatory backtracking

The slice has none. Any backtrack added later obeys the Dread rule: it arrives
with a new verb, or it collapses behind a shortcut. Re-traversal is power
fantasy, never repetition.

## What makes a room fail review

Ranked by how often it happens, not by how bad it is:

1. **It is a corridor.** One floor level, doors only left and right, a critical
   path that never turns. The batch rules reject a set of these outright, but
   even one wastes a room out of a very small budget.
2. **Its question has no answer by looking.** If the player must try things to
   learn where the route goes, the READ beat failed.
3. **Its pocket is invisible, or not actually exclusive.** Both are checked
   deterministically, and both mean the pocket taught nothing.
4. **Its friction is the destination.** An arena with an exit is not a room in
   this game; an encounter is crossed, not entered.

## Related

- `roomspec.md` — the format, and what the gate enforces.
- `movement-reach.md` — what the character reaches, measured.
- `junction-and-gates.md` — gate types and their geometric preconditions.
- `../01-classes/class-asymmetry-contract.md` — why exclusivity lives off the
  critical path and never on it.
