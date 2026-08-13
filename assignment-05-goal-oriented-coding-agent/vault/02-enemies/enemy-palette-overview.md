# Enemy Palette Overview — Echoes (GDD V2)

## Closed Palette Mandate
Encounters are constructed from a strictly closed palette of **five archetypes**. Encounters are designed as COMBOS, not isolated units.

## Room Encounter Budgets
- **Max Archetypes per room:** 2 archetypes.
- **Enemy Count per room:** 2 to 5 enemies total.
- **Checkpoint Rooms:** MUST contain **0 enemies**.
- **No Area Denial / Rail Snipers in Slice:** Excluded to match Dread room grammar.

## The corridor decides what may fight in it

Space is built from two standard heights (`../04-world/roomspec.md`). They are
not only a look: a **tight corridor (260)** clips the jump, so the player cannot
go over anything and combat becomes spacing rather than evasion. A **standard
floor (400)** leaves the jump intact.

Two archetypes require standard height or taller, and the gate refuses them
below it:

- **Shieldbearer** — its whole design is *over or through*. Remove the hop and it
  stops being a choice and becomes a wall only the Titan opens, which is the one
  thing `../01-classes/class-asymmetry-contract.md` forbids.
- **Ledge Gunner** — needs a ledge to shoot from, and a tight corridor has no
  room for one.

That leaves the tight corridor to the archetypes whose threat is horizontal:
Crawler, Walking Bomb, Blink Tank. Fewer of them, and weaker — the height is
already doing the work that enemy count would otherwise have to do.

This replaces a check that used to be deferred to an in-engine confirmation
nobody performed. With standard heights it is arithmetic.

## Archetype Roster Overview

| Archetype Name | Combat Role | Skill Check | Asymmetric Impact |
|---|---|---|---|
| **Crawler** | Melee Swarm | Spacing & weapon rhythm | Neutral / baseline friction |
| **Ledge Gunner** | Elevated Shooter | Coherence & TTK calibration | Neutral / platform pressure |
| **Shieldbearer** | Chokepoint Wall | Over-or-through navigation | Hunter hops over, Titan bashes through |
| **Walking Bomb** | Proximity Explosion | Range discipline | Punishes slow Titan |
| **Blink Tank** | Teleport Heavy | Tracking & burst control | Punishes Hunter dodge reliance |
