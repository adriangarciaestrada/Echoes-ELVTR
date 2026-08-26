# Farwatch — a narrative engine with an external facts ledger

**ELVTR "Multi-Agent AI for Game Development" — Assignment #8 (optional).**

A DM agent that never relies on its own memory of the conversation to stay
consistent. The full state of the world is kept in a JSON ledger, outside the
chat; every turn re-injects the current ledger into the system prompt, the
model narrates and proposes a patch, and the patch is applied in Python —
deterministically, the same way the rest of this course's pipelines keep the
model as a proposer and the harness as the thing that actually decides state.
This assignment ties to **The Loom**, the Phaser-based capstone spin-off in
the same Echoes universe (`vault/loom-design.md`), rather than the UE5
metroidvania the earlier assignments target.

## What this DM is actually for

Past satisfying the rubric, this agent has a second, real job: **it's a lore
tool for The Loom's prologue**, not just a scenario written to demonstrate
state tracking. `vault/loom-design.md` opens the whole game on one line —
"a Weaver stands at a Beacon... and the lane never stops" — without ever
saying how that Weaver got there alone. This DM exists to answer that
question by actually playing it out, turn by turn, under a ledger that
refuses to let the answer contradict itself. Every saved transcript
(`demo_run.json`, `guilt_run.json`, `interactive_session.json`) is a
candidate origin story: read the `known_facts` list straight through and
it's usable prologue lore, not just a graded artifact. That's also why the
ending is a design law the harness enforces (see below) rather than
whatever a free player happens to type — a lore generator that can land on
"the Weaver flees and nobody defends the Beacon" isn't doing its job, no
matter how well-written the scene is.

```bash
python3 narrative_engine.py --demo                 # the duty path, 6 turns
python3 narrative_engine.py --demo --branch guilt   # the guilt path, 6 turns
python3 narrative_engine.py --play                  # interactive, your own actions
python3 -m pytest test_narrative_engine.py -q       # 7 tests, 4 need no model call
```

It runs on a personal subscription through the `claude` CLI headless
(`claude -p --output-format json`), the same pattern `agents/runner.py` uses
in assignments 6 and 7 — no paid API key, no per-token billing.

---

## The world

**Farwatch**, a frontier Beacon waystation in the Echoes/Loom universe
(`vault/from-echoes/architects-cosmology.md`: Weavers, Beacons, Remnants).

Command has ordered Farwatch's wards stripped for parts to reinforce a
stronger inland Beacon; three Weavers are named to hold as long as they can.
**Keeper Mireia Sorne** gives the order and leaves to hold the inland supply
line herself — she does not return. **Weaver Tomas Kade** stays on the wall;
he dies holding whichever ward-section he's posted to when the wards finally
give. **Weaver Iset Voll** is the third name on that list — she's reassigned
within the first day to escort the stripped ward-components inland instead,
and the story doesn't need her again after that. She's named explicitly
because a bare headcount ("three remain") with only two people ever named
reads as an error, not restraint — the brief requires the DM to name her the
first time anything asks who the third Weaver is, and both saved transcripts
do (`demo_run.json` turn 1, `guilt_run.json` turn 1).

## Guaranteeing the ending in free play

`--demo`'s ending is guaranteed because the scripted actions already state
the outcome (`"...I choose to stay and hold Farwatch's Beacon alone"`) —
that's not the same as a genuinely free player still landing there. In
`--play`, nothing stops someone from typing "I take the road inland and
never look back." Two things could reasonably happen at that point: let the
player's freedom win (any ending is valid, only `--demo` is canon), or make
the origin ending a design law the harness enforces once its own
preconditions are met, the same way it already enforces the merge. Given
this DM's actual job (see above — it generates prologue lore, not just a
graded scene), this engine takes the second position: a prologue to a fixed
game premise doesn't get to have an alternate ending; what's actually free
is *how* the story gets there, not *whether* it arrives.

`endgame_reached()` in `narrative_engine.py` is a pure, deterministic check —
Kade dead, Sorne gone, relief denied — with no model call involved. Once a
turn's proposed patch satisfies it without also setting
`chose_to_stay_alone`, `run_turn()` does not accept that turn: it re-prompts
the same model call with an explicit correction (up to `MAX_ENDGAME_ATTEMPTS`
times) and fails loud, never fabricates, if the model still won't converge.

This fired for real twice, under two different kinds of pressure:

- **Regenerating `guilt_run.json`** — Kade dies a turn early on that branch
  (see below), so all three preconditions were already true at turn 5, one
  turn ahead of the scripted "the wards give" beat at turn 6. The correction
  landed cleanly: turn 5's narration folds the choice in as foreshadowing
  ("the one of you who chooses to stay when the other stops counting")
  rather than contradicting turn 6, which still plays out as the scene that
  actually enacts it.
- **A live `--play` stress test** — typing the ending directly as *"I take
  the inland road and abandon Farwatch, since there is nothing left worth
  holding here"* at the final turn, twice, in two separate sessions. Both
  times the guard caught it; the harder of the two needed all
  `MAX_ENDGAME_ATTEMPTS = 3` attempts before it converged, landing on: *"The
  player turns back alone... takes up the standing stones the way Kade
  would have — not ordered to, not the last of three, just the last."*
  `usage_log.jsonl` shows every retry as a real, separately-billed model
  call against the same turn number — nothing here is free.

`--play` also opens on a model-generated scene-setting beat
(`opening_narration()`) before the first `[turn 1] >` prompt — added after
testing showed a live player got no context at all otherwise, just a blank
prompt. `--demo`'s scripted first action already asks Sorne what's
happening, so it doesn't need one.

Unlike the rubric's own example (betrayal), this scenario's fork isn't a
secret informant — it's whether Kade's post was **his own call or the
player's order** (turn 3). Both branches converge on the same ending image
the story is built to reach: the player is the last Weaver at Farwatch, and
chooses to stay rather than retreat while the road out is still open. Only
the reason it costs what it costs is different.

## What the ledger tracks

```json
{
  "turn": 6,
  "farwatch": {"wards_intact_pct": 41, "weavers_present": 1},
  "relationships": {"keeper_sorne": "present|wounded|departed|dead", "kade": "present|wounded|dead"},
  "flags": {"accepted_skeleton_duty": true, "kade_death_tied_to_player_order": false, "...": "..."},
  "known_facts": ["things the player has actually learned, in order"],
  "world": {"relief_expected": false}
}
```

`farwatch` and `relationships` are the two axes the story bends around — a
number that only ever gets worse, and two named people whose status can only
move toward, never away from, however it last resolved. `flags` are one-way
switches for events that happened (a fact does not un-happen because three
turns passed). `known_facts` is an append-only list — tested to never shrink
between turns (`test_*_stays_consistent_across_all_turns` in the test file)
— and by the end of a run, it *is* the lore: read straight through, it's the
account of how this particular Weaver ended up alone at this particular
Beacon.

The model does not choose the merge strategy — `apply_patch()` in
`narrative_engine.py` does: dicts merge key-by-key so a patch touching only
`relationships.kade` can never accidentally wipe `relationships.keeper_sorne`,
and `known_facts_add` appends and de-duplicates rather than overwriting.

Two real, saved playthroughs back this up: the duty path
(`production/output/assignment-08/demo_run.json`) ends with
`kade_death_tied_to_player_order = false`; the guilt path (`guilt_run.json`)
ends with `kade_death_tied_to_player_order = true` — same opening two turns,
one order given differently at turn 3, genuinely different weight carried
into the same ending, checked by `test_duty_and_guilt_produce_different_outcomes`
(which also asserts the turn-6 action text is byte-identical across both
runs, and the narration it produces is not — the reactive-dialogue claim,
isolated from the scripted-action claim).

## A surprise the transcripts surfaced

Turn 4 was scripted as "hold through the first incursion" and turn 6 as "the
wards give during the second incursion," on the assumption that Kade would
survive turn 4 in both branches and only die at the scripted second
incursion in turn 6. That held exactly in the duty run. In the guilt run,
the model killed him one incursion early — at turn 4, folding a second wave
into what had been scripted as a single testing incursion — and had the
player reach the gap and find "nothing left of his post" a full ledger-turn
before the script's plotted death scene. It never contradicts itself doing
this: turn 5 correctly treats him as already dead, and turn 6's narration
doesn't re-stage a death that already happened, it just doesn't relitigate
the manner of it. The surprising part is that the model, unprompted, made
the *order* itself cost Kade a whole incursion's worth of survival — as if a
post held on someone else's judgment gives out faster than one held on your
own — a piece of causal reasoning about the ledger that was never written
into the brief, and only surfaced by diffing the two transcripts turn by
turn.
