# Differentiators — what this is, that the reference is not

The reference is documented in `reference-game.md`. Copying its loop is
deliberate; these are the places we diverge on purpose, each with a reason.

## 1. Landscape, three panels, nothing hidden

The reference is portrait because it is a phone, and it puts weapon stats
and active buffs behind modals — so part of its depth is really memory tax.
We are a desktop browser game: the arsenal lives on the left with live
cooldowns and damage-per-cell, the buffs live on the right grouped by
category, and the centre column plays the game. Decisions get made with
their information visible. `ui-and-strings.md` owns the law.

## 2. Class is loom shape, not a costume

Starting relic, **grid geometry**, and ultimate. Because the loom's shape
differs, the same relic pool packs differently for each class — the
asymmetry lives in placement, never in raw power
(`from-echoes/class-asymmetry-contract.md`). The reference's characters are
mostly a starting weapon and a skill.

## 3. The Disruptor, and the cell you leave empty

A recurring boss that **unravels** the player's highest-tier relic, splitting
it back into components. It attacks the player's decisions rather than the
wall, and it is self-balancing: the greedier the merging, the more it undoes.

Its best consequence is what happens when the loom is full — the half that
cannot fit is destroyed. So perfect packing stops being strictly optimal, and
the player gets a question no inventory game usually asks: **is a cell better
spent on a relic, or held empty as insurance?** `bosses.md`.

## 4. The player authors the pace

The market is untimed and battle runs at 1×/2×/3×/5×/10× — the reference
offered one toggle (1×/6×). Because deliberation is free and battle is
compressible, the same build reaching the same depth can be a fifteen-minute
session or an hour, entirely by temperament. The one honest cost: the
ultimate stays manual at every speed, so fast-forwarding means giving up the
only live input (`combat-model.md`).

## 5. The metric is on screen

Damage-per-cell — the yardstick the reference's community invented for
itself, because the game would not show it.

## Same as the reference, on purpose

Endless escalation with depth as the score; lossy merging; category-targeted
buffs; the free-then-paid reroll economy; pool removal; the imposed
buff/expansion alternation; full repacking between waves. These are the
reference's best-tested decisions and originality for its own sake would
only make the game worse.

## Explicitly deferred

Seeded-run sharing ("beat my seed"). The seeds exist from the first commit
because the simulator needs determinism, but surfacing them to players is
the lowest priority feature we have.
