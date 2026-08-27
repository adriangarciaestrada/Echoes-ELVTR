# An adversarial QA agent that tries to break The Loom

**ELVTR "Multi-Agent AI for Game Development" — Assignment #9 (optional).**

An agent that runs continuously inside the capstone game with one goal: make it
do something its own design law says it cannot. It plays badly on purpose,
watches roughly twenty invariants while it does, and writes a JSON/CSV bug
report another developer can act on without opening the game.

Like assignment #8, this targets **The Loom** — the Phaser/TypeScript capstone
spin-off in the same Echoes universe (`vault/loom-design.md`) — rather than the
UE5 metroidvania the earlier assignments build against.

## The half of crew agent #10 that was missing

Assignment #3 shipped a twelve-agent crew, and agent **10, the Adversarial QA
Crew** ([`../assignment-03-agent-crew/agents/10-adversarial-qa-crew.md`](../assignment-03-agent-crew/agents/10-adversarial-qa-crew.md)),
opens with an integrity rule that is worth re-reading:

> You do NOT run tests, simulate runs, or produce telemetry. You analyze ONLY
> the raw telemetry provided in the task input.

That was the right call — a model asked to both generate and judge its own
telemetry will invent numbers — but it left the spec naming a "Headless Bot
Execution Harness (produces the input logs)" that did not exist yet. **This
assignment is that harness**, and it is deliberately not an LLM: the thing that
decides whether the game is broken has to be arithmetic, or the report is worth
nothing. Same division of labour the rest of this course's pipelines use, with
the model moved all the way out of the loop rather than into the proposer seat —
because here there is nothing to propose. There is only the game's own law, and
whether the running build obeys it.

## Running it

```bash
# from the game repo, where these files live at src/qa/adversary/
npm run adversary                    # ~8 min: probes, core fuzz, real browser
npm run adversary -- --no-browser    # core only, ~1 min, no dev server needed
npm run adversary -- --headed        # watch it click
LOOM_ADV_TRACE=1 npm run adversary   # print each browser tactic as it runs
```

The dev server is started and stopped automatically unless one is already up.
Output lands in `qa-reports/` — reproduced here under `production/output/`.

`agents/` is a verbatim copy of `src/qa/adversary/` in the game's own
repository, which is private, so the relative imports (`../../core/…`) point at
game modules not vendored here. The report in `production/output/` is the real
artifact of one full run, not an example.

## What "broken" means — `agents/oracle.ts`

This file is the whole strategy, and everything else exists to feed it.

A fuzzer that only watches for exceptions finds crashes and nothing else. Every
bug this agent actually found is one that never threw: a pair of parallel arrays
drifting apart, a settle function paying a reward twice, a grant applied against
an empty queue. So the oracle is a set of statements that must hold over a
snapshot of the running game, most of them lifted straight out of the design law
copied into `vault/`:

| law | vault source |
|---|---|
| relics never leave the 7×7 envelope, never sit on a locked cell, never overlap | `loom-grid.md` |
| a relic's tier stays in 0..4, and its cells always match its footprint | `relic-contract.md` |
| nothing comes to rest further from the Beacon than the shortest reach in the roster | `wave-contract.md`, `combat-model.md` |
| gold is only ever earned by killing something | `economy.md` |
| the tray is emptied when a fight begins | `economy.md` |
| the buff screen is dealt once per grant and held | `economy.md` |
| a market is only reached once every earned reward has been taken | `economy.md` |
| every wave either clears or kills the Beacon | `combat-model.md` |
| an expansion phase always has a legal cell, or converts itself to buffs | `loom-grid.md` |

Plus the structural ones a snapshot makes cheap: unique uids, finite numbers, no
negative resources, no live battle outside the battle phase, no wave counter
going backwards. Two surfaces produce the same snapshot shape, so both are
judged by exactly the same laws and a break found in both is one finding with
two witnesses.

## Three ways of attacking it

**`agents/fuzz.ts` — the core, headless, flat out.** Named attacks, each aimed
at a way this game has broken before: `banish_storm` (parallel arrays drifting
apart), `scrap_loop` (an income stream that bypasses combat — an exploit the
game already closed once, kept here as a regression trap), `hand_churn`
(lift/rotate/drop past the board's edges), `merge_storm` (every pair including a
relic against itself), `expansion_abuse`, `economy_drain`, `phase_confusion`
(transitions in the wrong order, as a stale click handler would produce),
`ult_spam` (the one live input, pressed every single tick), `offer_index_abuse`
(−1, 99, NaN, 1.5). One run in four plays competently instead, because the
interesting state — Disruptors unravelling the loom mid-battle, Purples on the
shelf, a board one relic from a dead end — only exists past wave 20. **A
90-second sweep is 1,868 runs, 73,169 hostile calls and a deepest wave of 121.**

**`agents/browser.ts` — the shipped build, in real Chromium.** Everything is
driven in the game's own 1280×720 coordinates and converted to page pixels
through the canvas's bounding box, so the agent can resize the window or run at
a HiDPI device pixel ratio and still aim at the same cell — that mapping is
itself under test, since this game shipped a bug once where every grid click
landed on the wrong cell, scaled by the display's pixel ratio. Tactics:
`boundary_carpet` (the ring outside the envelope, its edge, both diagonals, the
canvas corners, the panel seams), `ghost_clicks` (clicking where the *previous*
screen's controls were — every screen here is a state of the same panel, never
an overlay, so a control that outlives its phase sits invisibly on top of the
next one), `double_click_storm` (four clicks inside one frame on every live
control), `speed_lang_thrash` (forcing a redraw as fast as possible in every
phase), `key_mash`, `drag_dump`, `ult_mash`, `resize_churn`, `storage_poison`,
and two Banish attacks. Three passes, at pixel ratios 1, 2 and 3.

**`agents/probes.ts` — minimal reproductions.** The shortest sequence that
produces each break from a fresh run, so the report carries a recipe rather than
a haystack. Nine of its twelve rules are ones the game already gets right; they
are there so a discriminating oracle can be told apart from a noisy one.

---

# What did the agent find?

Six report rows, four distinct root causes. Full detail in
[`production/output/adversarial-report.json`](production/output/adversarial-report.json)
(same rows in `.csv`).

## 1. Banishing a market card upgrades the card below it, for free — `critical`

`LOOM-ADV-001`, plus `LOOM-ADV-004` and `LOOM-ADV-005`, which are the same
defect seen as invariant violations.

`Run.removeFromPool` splices `offers` and never touches `offerTiers`. The two
are parallel arrays read together by every consumer, so each surviving card
inherits the tier of the slot **above** it. Banishing costs nothing, so whenever
the shelf happens to be ordered high-then-low, one free click raises the rarity
of a card the player never touched — and banishes chain, so the last survivor
can be handed the best tier that was on the shelf.

Reproduced through the real UI at wave 22, with screenshots either side of the
click ([`shots/banish-before.png`](production/output/shots/banish-before.png),
[`shots/banish-after.png`](production/output/shots/banish-after.png)). One click
on the top card's **Banish** — on *Focus Turret*, which the player was
discarding anyway — moved the other two up a slot and changed both of them:

| card | before the click | after the click |
|---|---|---|
| Flame Field | Common — 34 dmg / 2.80 s | **Uncommon — 58 dmg / 2.52 s** |
| Heavy Hitter | Uncommon — 88 dmg / 2.34 s | **Common — 52 dmg / 2.60 s** |

Neither was touched. One was handed a free rarity worth 71% more damage; the
other was quietly robbed of one it had already been shown. The core fuzzer hit
the underlying array desync **30,211 times across 1,868 runs**.

This one matters because `relic-contract.md`'s first law is that merging buys
space and effects rather than raw damage — two separate copies always out-damage
one merged relic — and the whole tier ladder is priced around that. A free tier
is the one thing the economy is built to never hand out.

The fix is one line: splice `offerTiers` alongside `offers`. `Hand.removeOffer`
in the game's `src/game/hand.ts` is that exact helper, written after the same
mistake was made on the *take* path, with a comment explaining that removing
from only one array re-tiers every card below it. The market's other exit paths
all go through it. Banish does not.

## 2. `Run.endBattle()` settles the same wave twice — `high`

`LOOM-ADV-002`. The guard is `if (!b || !b.finished) return`, which passes
forever once a battle has finished. A second call pays the wave's gold and EXP
again and advances to the next wave without fighting it: wave 2→3, gold 12→24,
level 1→2. The renderer does not currently call it twice, but the headless
simulator and every QA harness in the game repo drive `Run` directly — and those
are what produce this project's balance verdicts, so a double settle there
silently corrupts a measurement rather than showing up as a visible bug.
`settlePhase()`, its neighbour in the same file, already carries exactly the
guard this needs, and its comment says why it was added.

## 3. `Run.takeBuff()` grants a buff with nothing owed — `high`

`LOOM-ADV-003`. It applies the buff unconditionally and only clamps
`pendingBuffChoices` at zero, so three calls with an empty queue produce three
permanent buffs. The only thing standing between that and unlimited buffs is the
renderer destroying its buff-card click zones — a leak this codebase has already
had once, and whose fallout (a stale zone over the battle screen granting a buff
mid-fight) is what `settlePhase()`'s guard was written for. Both surfaces around
this method were hardened. The method that grants the power was not.

## 4. An unreadable `loom.best` bricks the score screen — `medium`

`LOOM-ADV-006`. `recordBest` does
`JSON.parse(localStorage.getItem("loom.best") || "{}")` with no try/catch and no
shape check, so `"not json"` throws a `SyntaxError`, `"12"` throws
`Cannot create property 'hunter' on number`, and `null` throws on the property
read. The run reaches `phase: "over"`, the score screen never builds, and there
is no Play-again button: the game cannot be restarted without clearing the
site's data ([`shots/storage-poison.png`](production/output/shots/storage-poison.png)).

Not reachable by play today — reachable by any change to the stored format, a
second page on the same itch.io origin, or a half-written value. Worth noting
that the two sibling keys are read defensively: `loom.lang` checks the value is
one of two strings and `loom.speed` checks it is one of five numbers. This one
is not checked at all.

## What held

Nine rules, and they are part of the result. The scrap-for-gold loop stays
closed; `settlePhase` cannot pull a run out of a live battle; the tray is
emptied by starting a fight; merging stops at Epic; expansion never leaves the
envelope; out-of-range market indices are refused rather than thrown on; the
buff screen is dealt once and held across ten reads; a banished relic never
returns across 200 rerolls; and a Disruptor unravelling the loom mid-battle
leaves it consistent. Across 73,169 adversarial core calls and 31 browser tactic
cycles at three pixel ratios there were **zero uncaught page errors, zero frozen
battles, zero relics lost to a stray click, and zero clicks that landed on the
wrong cell.**

---

# Were the findings surprising?

Two of them, yes — and not for the reason I expected.

I went in aiming at the loom itself: rotation, merging, dropping relics at the
edges, the expansion grid. That is the fiddliest geometry in the game and the
obvious place for an off-by-one. The agent found nothing there. It also found
nothing in the battle, which has the most moving pieces, and nothing in the
pointer-to-cell mapping even at pixel ratio 3, which is where this game shipped
a real bug once before. All four findings are in the *bookkeeping* around those
systems, and three of the four are in one file.

The genuinely surprising thing is the shape they share. **Every one of them is a
guard that already exists somewhere else in the same file, on the same idea, and
is missing here.** `Hand.removeOffer` splices both arrays and carries a comment
explaining that failing to do so re-tiers the cards below; `Run.removeFromPool`
splices one. `settlePhase` was hardened against a stale caller and says so in
its comment; `endBattle`, its neighbour, was not. `Run.buy` refuses when the
gold is not there; `Run.takeBuff` does not refuse when the grant is not there.
`loom.lang` and `loom.speed` validate what they read back; `loom.best` does not.
Each fix had already been reasoned through once in this codebase. It just was
not carried to the sibling.

That is not what I thought an adversarial agent would be for. I expected edge
cases at the boundary of a mechanic. What it actually found is **where a lesson
stopped being applied** — which is a thing a test suite written by the same
person who wrote the code is structurally bad at noticing. The game's 50 core
tests all pass, and they pass because they check the paths their author was
thinking about. The agent is not smarter than those tests; it is just not
thinking about anything, which turns out to be the point.

The second surprise is a methodological one, and it changed how the tool is
built. The first version of the browser agent looked healthy — it clicked
everything, threw no errors, reported nothing — and it was worthless: it was
dropping every relic it took onto a locked cell, so it fought every wave with
one relic and died at wave 1, over and over, never seeing the buff screen, the
expansion grid or a market past the first. **An adversarial agent has to be able
to play the game well enough to reach the parts worth breaking**, which is why
one core run in four now plays competently and why the browser tactics are
interleaved with a deliberate `advance_wave`. Every finding except the first
lives past that threshold.

The one thing I was *not* surprised by is the severity of finding #1. Once the
desync was visible, the free-upgrade exploit followed directly — and the reason
it survived this long is that early waves deal nothing but Commons, so the bug
is invisible for the first ten minutes of every run and only starts paying out
around wave 20, deeper than a playtest usually goes. The agent found it in 90
seconds because it does not have to play the twenty minutes first.

---

# The report — `production/output/`

`adversarial-report.json` and `adversarial-report.csv` carry the same rows.
Findings are deduped on `(code, system, symbol)` and sorted by severity, because
a fuzzer running 73,000 steps hits the same break tens of thousands of times and
a report with 30,000 identical rows is one nobody reads.

| field | what it answers |
|---|---|
| `location.system` | where in the **game** — `market / banish`, `battle / lane`, `progression / buffs` |
| `location.file` / `location.symbol` | where in the **code**, down to the method that owns the rule |
| `location.screen` | which pixel the browser agent was clicking, and that control's label |
| `error_type` | `economy_exploit`, `state_desync`, `boundary_break`, `stuck_state`, `crash`, `rule_violation`, `invariant_break` |
| `severity` | `critical` / `high` / `medium` / `low` |
| `game_context` | class, seed, phase, wave, level, gold, Beacon HP, relics, cells, buffs, enemies alive, battle time |
| `game_context.steps_to_reproduce` | the recipe, oldest step first |
| `expected` / `observed` | the law, and what happened instead |
| `witnessed_by` | which surfaces and tactics saw it — a break the fuzzer finds and the browser then reproduces through real clicks is a different report from one only the headless side hit |
| `evidence` | screenshots taken at the moment it broke, relative to the report |
| `occurrences` / `reproduced` | how many times, and whether a minimal replay confirmed it |

```
production/output/
├── adversarial-report.json     6 findings, 4 root causes, one full run
├── adversarial-report.csv      the same rows, 29 columns
└── shots/
    ├── banish-before.png       the market before one Banish click
    ├── banish-after.png        …and after: two cards changed rarity untouched
    ├── LOOM-ADV-004-…png       the desync caught mid-run in the browser
    └── storage-poison.png      the score screen that never built
```
