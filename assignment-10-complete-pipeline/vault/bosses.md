# Bosses — recurring, escalating

Every **5th wave** brings a boss. Endless escalation means bosses are a
recurring pressure valve, never a finale.

## The forms

Bosses are heavy Remnant constructs — Architect defence machinery still
running (`from-echoes/architects-cosmology.md`). Three archetypes, cycling
and scaling with wave number. An endless run has no finale, so a boss is
recurring pressure rather than a climax:

| archetype | pressure it applies | teaches |
|---|---|---|
| **Bulwark** | huge HP, slow, absorbs everything | sustained single-target damage; pure swarm builds stall |
| **Splitter** | splits into swarm on death `[TUNE]` count | crowd answer must survive the wave AFTER the boss |
| **Disruptor** | periodically **unravels** the player's highest-tier relic — splits it back into its two components | punishes greedy merging; the merge verb inverted |

Bosses obey the reach law (`wave-contract.md`): a boss advances until it is
inside range of every relic, and never parks where part of a build cannot
answer it.

## The unravel, exactly

Merging frees cells — two relics of one footprint become one — so an unravel
needs space that may not exist. The rule handles both cases without a special
case:

- **Room on the loom:** the relic splits into its two components, one tier
  down, placed automatically where they fit.
- **No room:** it splits anyway, and **the half that does not fit is lost.**

That is self-scaling. A player carrying slack takes a *packing problem*; a
player packed to the last cell takes a *material loss*. Both are punished in
proportion to how tightly they optimised, and it needs no holding buffer, no
forced-choice popup, and no immunity case.

It also creates a decision the game otherwise lacks: **fill every cell, or
keep one free as insurance against the Disruptor.**

Details: the target is the highest-tier relic above Common; if a player holds
nothing above Common there is nothing to unravel and the ability does
nothing that cycle — a player in that state is already losing. Unravel fires
on arrival and every `[TUNE]` seconds while the Disruptor lives, so killing
it faster is the counter.

The Disruptor is the roster's sharpest idea: it attacks the player's
*decisions* rather than the wall, and it is self-balancing — the greedier the
merging, the more it has to undo. Recurring makes it a standing threat rather
than a gimmick seen once.

Scaling `[TUNE]`: HP and damage rise with wave; beyond wave ~25 two bosses
may arrive together.
