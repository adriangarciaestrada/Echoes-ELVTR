# UI and strings — the Loom's screens

`from-echoes/ui-constraints.md` owns the law (GLANCE→GRASP→ACT→TRUST,
screens-have-jobs, plain-where-plain-is-correct). This note owns this game's
layout, screens, and caps.

## The layout — three panels, landscape

**This is the game's most visible differentiator and it exists to fix a real
flaw in the reference.** That game is portrait because it is a phone, and it
hides the information its own decisions depend on behind modals: weapon stats
and active buffs both live one tap away. Its community feels this — a player
writing a public strategy guide could not recall the name of a buff he ranked
fifth in importance.

We are a browser game on a landscape screen. The side panels are permanent.

```
┌──────────────┬────────────────────────┬──────────────┐
│   ARSENAL    │         PLAY           │    WEAVE     │
│    320px     │         640px          │    320px     │
│              │                        │              │
│ per relic:   │  battle lane           │ active buffs │
│  icon+tier   │  market                │  grouped by  │
│  cooldown ▮▮ │  grid expansion        │  category    │
│  damage      │  buff pick             │  full text   │
│  cells       │                        │              │
│  dmg/cell    │  (all state changes)   │  (read-only) │
└──────────────┴────────────────────────┴──────────────┘
                   1280 × 720 canvas
```

Rules:

- **Everything that changes state happens in the centre.** The sides are
  read-only instruments; they inform decisions and never make them.
- **The centre is the portrait column** the genre needs — battle, market,
  expansion and buff selection all appear here, never as overlays.
- **Live cooldown bars on the left, during battle.** This is what makes an
  autobattler watchable rather than passive: the player sees the build
  working and learns which relic is carrying long before a score screen
  says so.
- **Damage-per-cell is displayed**, not left to mental arithmetic. The
  reference's community invented that metric because the game withheld it;
  showing it natively is a small feature with a large "this game respects
  me" effect.
- **Buffs group by category** (Bolt / Burst / Construct) so "am I a Burst
  build?" is answerable at a glance — which is what turns the buff pick into
  a real decision.
- **Every row must change a decision.** `from-echoes/ui-constraints.md`: a
  string that changes no decision is noise with a budget. Space is not a
  reason to add a field.
- Desktop-first, deliberately. `Scale.FIT` letterboxes; below ~1000px the
  layout does not hold and that trade is accepted.
- **No bare text over the wall art** (owner's call, 2026-09-01). The
  generated stone background carries glyphs and glowing seams, so any text
  drawn over it sits on a solid plate (`ui.ts` `titlePlate`/name plaques),
  never directly on the texture. Text inside panels, frames and buttons
  already satisfies this by construction.

## Screens and their jobs

Screens are states of the CENTRE panel; the sides persist across all of them.

| Centre state | Its one job |
|---|---|
| Title | start a run in one input; class choice is the only decision |
| Class select | the run's one irreversible choice — three cards, each drawing its own loom to scale |
| Battle | sustain the run without interrupting it — wave, gold, EXP, Beacon HP, **the ultimate's slab**, **speed control (1×/2×/3×/5×/10×)** |
| Market | the decision space: offers, reroll, remove-from-pool, the loom, Continue |
| Grid expansion | place the new cells; nothing else competes for attention |
| Buff pick | choose one; the right panel shows what is already owned |
| Score | how deep, what carried (damage-per-relic bars), what to try next |

## Widget classes and caps

Both languages independently; Spanish decides fit. `[TUNE]` all.

| widget_class | cap |
|---|---|
| MenuLabel | 20 |
| RelicName | 16 |
| RelicDescription | 90 |
| BuffLabel | 40 |
| StatLabel | 20 |
| ScoreProse | 200 |
| Prompt | 24 |

## Pipeline

All user-facing text goes through the existing style loop (assignment 7,
four rules, unchanged — it already reads the guard, the cosmology, the
constraints; only this caps table replaces `ui-budgets.md` for Loom text).
Relic and enemy display names are copy-pipeline output landing as string
keys; specs carry `display_name_key`, never literals.


## The ultimate's control

The **button is the control**; Space is a shortcut. It is the only thing a
player does during a battle, so it is drawn as a filling slab in the lane's
bottom-right, not styled like `reroll` and `fight`. The first build gave it the
same small text button as every other control and it read as the least
important thing on the screen — which is the opposite of true.

Its background fills left to right as it charges, so readiness is legible
without reading the number.

**Three states, because two would lie.**

| state | reads |
|---|---|
| charging | `◆ NAME` / `12s`, dim, partly filled |
| armed, nothing in reach | `◆ NAME` / `no target in reach`, dim, full |
| armed and it would connect | `◆ NAME` / `READY — space`, gold, bordered |

The third state exists because a press that cannot connect is refused rather
than wasted (`combat-model.md`). A button that looks armed and does nothing
when pressed reads as broken, so it says which of the two it is.

Any check on this must exercise **both** controls, each from a fresh wave: the
ultimate starts every wave charged and its cooldown outlasts an early wave, so
testing the second control after spending the first inside one battle can never
pass.


## Class select

Three cards, one click. **Each card draws its own loom to scale** — filled cells
are what the class opens with, outlined cells are what it can grow into — so
tall, wide and square are read rather than described. Prose starts below the
tallest loom on every card, so the row lines up despite the shapes differing.

Every fact on a card is read from the core: geometry from `grid.ts`, the
ultimate from `ULTIMATES`, the starting relic from `RELIC_BY_ID`. The class
descriptor moved into the core for this — a card must not be able to advertise
a class the run does not build.

`?class=titan` skips the screen and starts that run directly, for sharing and
for the browser checks. **Asking for the menu outright beats the link**: without
that, "change class" bounces straight back into the class the URL names and the
button appears dead.


## Shot shapes

Every shot draws the zone it actually covered, for 130 ms.

| category | shape | why |
|---|---|---|
| Burst | **cone** from the Beacon, `±spread` wide, out to its reach | that is exactly the set it hits |
| Bolt, Construct | thin **tracer** up the target's own column, with an impact mark | one Remnant, and only one |
| Ultimates | gold **circles** for blades and the knot, a **band** for the wave | each is the shape the core tests against |

Before this, **nothing about a relic firing was drawn at all** — the renderer
never subscribed to battle events, so a player watched health bars fall with no
way to see what reached what. Burst is the category whose whole identity is
where it lands, and that was the one thing invisible.

**The shot event carries the geometry it produced** (`pos`, `radius`), because
the renderer cannot recover it afterwards: the target is often reaped in the
same tick that produced the shot.

**A single-target shot must not be drawn full width.** The first version drew a
line across the whole lane, which reads as "everything at this depth is hit" —
the one thing a Bolt does not do. It now aims at the target's drawn column.

**The lateral column is cosmetic and derived from the enemy id in exactly one
place** (`laneColumn`). The model has no lateral axis. Both the Remnant and any
shot aimed at it must use that helper or the shot appears to miss something it
certainly hit.

Shots are drawn UNDER the Remnants, so a slab never hides what it caught, and
the list is capped at 120 — at 10x a wave fires hundreds.


**Drawing the shape is what found the balance fault.** The slab was measured as
overpowered and tuned twice before anyone saw it; a single frame of it on screen
made the cause obvious in a way the numbers had not. Draw the geometry early —
a shape that is wrong is much easier to see than to derive.
