# Economy — gold, market, EXP

Owns every economic number. Run-scoped; nothing persists across runs except
score history. No meta-progression (deliberate — honest for a capstone).

## Gold

Kills pay gold. Two-phase sink, as the reference proved (~95% of endgame
gold went to rerolls): first a small upgrade shop, then rerolls only.

Upgrade shop, always open during the market, prices rising per purchase
`[TUNE]`:

| | effect | cap |
|---|---|---|
| Mend the Beacon | restore 30 | — |
| Reinforce | +20 max Beacon HP | — |
| Spare Shuttle | +1 free reroll every market | 3 |
| Study the Weave | +20% EXP gain | 4 |

**One free reroll per market, then a rising cost.** Two free rerolls meant a
player never needed gold at all and simply watched the number climb — reported
from play, and worth ~10 waves of depth once spending existed. Unspent gold is
wasted gold, and the market says so on screen.

## The tray — staging space that doubles as the discard

A strip beside the loom that does two jobs with one mechanic:

1. **Somewhere to put things while repacking.** A full board cannot be
   rearranged at all without free space to work in; the tray is that space.
2. **Discarding, without a separate verb.** Anything still in the tray when
   the fight starts is destroyed, and **pays nothing**. You set aside what you do not want
   and walk away from it, and the fight button says what that will cost.

Relics render at miniature scale but keep their true footprint, so the strip
holds several without taking screen space and the shape stays readable — the
shape being the thing the player is actually reasoning about.

**Why it is not optional.** Reported from play at wave 35: a board full of
merged relics can neither place a Common offer (no space) nor merge one into
anything (wrong tier), so improvement stops permanently while waves keep
escalating. A dead end, not a difficulty.

**Discarding pays nothing, and that is a correction.** Scrap value was
`3 × 2^tier`, which made the market a mint: reroll for 8, take three high-tier
offers, discard them for up to 140, repeat without limit. A playtest reached
wave 50 on it and reported the run had stopped being about the loom and become
about gold. The return was strictly larger than the cost to generate it, so the
loop had no fixed point. Gold now comes from kills, full stop. Closing it moved
the skill gradient from 1.83× to **1.97×**: unlimited gold had been covering
for bad decisions, so the metric had been measuring a game where choices were
close to free.

**Three of the buffs move the ultimate** — damage +30%, cooldown -18%, reach
+25% (which grows the knot's duration as well as its radius: one buff, one
idea, whichever ultimate the class carries). They are the **only** lever that holds the ultimate's
share of a wave up as waves grow — 4% by wave 35 with no investment against 9%
with it. The ultimate is never scaled down by wave number; the waves simply get
longer and the buffed arsenal outgrows a loom-priced ability. Buying that gap
back is the decision these three exist to offer.

**The tray is capped at what it can display.** It held unlimited relics while
only drawing the first row, so relics past the cap vanished from the screen but
stayed in the run — invisible state, and half the exploit's throughput. A drop
onto a full tray is now refused.

## Market offers climb with the run

An offer's tier is rolled from a distribution whose centre walks upward about
one tier every 11 waves `[TUNE]`, capped at what the player could plausibly
have merged to by then. This is the other half of the same fix: late offers
must be able to merge with a mature board, or the market stops being useful
exactly when the run needs it most.

## Market (between waves)

- 3 relics offered. Take any that fit; leave the rest.
- Reroll: first 2 free per market, then rising gold cost `[TUNE]`.
- **Remove-from-pool:** one action per market `[TUNE]` banishes a relic type
  from all future offers — deck-thinning the RNG, kept verbatim from the
  reference because it converts "reroll and pray" into a plan.
- Full repack allowed: one "lift everything" button; nothing commits until
  Continue.

## EXP and the alternation

Kills pay EXP. Each bar fill alternates **buff → expansion → buff → …**
(imposed rhythm, kept from the reference). Fills keep coming for as long as the run does.
**When the board is full, expansion fills convert to buffs** — so the
alternation never offers a reward the player cannot use. No level cap, and
therefore no trap picks: the reference capped level at 40 and made its EXP
buffs worthless late, which its own community flagged as a trap.

Buffs are category-targeted (Bolt/Burst/Construct: damage %, cooldown %,
range; plus Beacon repair) — the buff system IS the category system. No
trap picks: every buff in the pool is live at every point of a 10-wave run.
