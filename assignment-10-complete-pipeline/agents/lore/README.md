# Farwatch — a lore-generating narrative engine

A DM agent that never relies on its own memory of the conversation to stay
consistent. The full state of the world is kept in a JSON ledger, outside the
chat; every turn re-injects the current ledger into the system prompt, the
model narrates and proposes a patch, and the patch is applied in Python —
deterministically, the model as a proposer and the harness as the thing that
actually decides state.

Its job is to answer a question `../../../loom-vault/loom-design.md` leaves
open: *The Loom* opens on "a Weaver stands at a Beacon... and the lane never
stops," without ever saying how that Weaver got there alone. This engine
plays that out turn by turn under a ledger that refuses to let the answer
contradict itself. See `../../../loom-vault/prologue-origin.md` for the
distilled result — the two saved transcripts under `output/` are the source
that note is drawn from.

```bash
python3 narrative_engine.py --demo                 # the duty path, 6 turns
python3 narrative_engine.py --demo --branch guilt   # the guilt path, 6 turns
python3 narrative_engine.py --play                  # interactive, your own actions
python3 -m pytest test_narrative_engine.py -q       # 7 tests, 4 need no model call
```

Runs on a personal subscription through the `claude` CLI headless
(`ai_call.py`, ported from the ELVTR course monorepo's agent runner) — no
paid API key, no per-token billing.

---

## The world

**Farwatch**, a frontier Beacon waystation. Command has ordered its wards
stripped for parts to reinforce a stronger inland Beacon; three Weavers are
named to hold as long as they can. **Keeper Mireia Sorne** gives the order
and leaves to hold the inland supply line herself — she does not return.
**Weaver Tomas Kade** stays on the wall; he dies holding whichever
ward-section he's posted to when the wards finally give. **Weaver Iset
Voll** is the third name on that list — reassigned within the first day to
escort the stripped ward-components inland instead, and the story doesn't
need her again after that.

The one fork in the story is whether Kade's post was **his own call or the
player's order** (turn 3). Both branches converge on the same ending image
the story is built to reach: the player is the last Weaver at Farwatch, and
chooses to stay rather than retreat while the road out is still open. Only
the reason it costs what it costs is different.

## Guaranteeing the ending in free play

`--demo`'s ending is guaranteed because the scripted actions already state
the outcome — that's not the same as a genuinely free player still landing
there. In `--play`, nothing stops someone from typing "I take the road
inland and never look back." A prologue to a fixed game premise doesn't get
to have an alternate ending, so `endgame_reached()` in `narrative_engine.py`
is a pure, deterministic check — Kade dead, Sorne gone, relief denied — with
no model call involved. Once a turn's proposed patch satisfies it without
also setting `chose_to_stay_alone`, `run_turn()` re-prompts the same model
call with an explicit correction (up to `MAX_ENDGAME_ATTEMPTS` times) and
fails loud, never fabricates, if the model still won't converge.

This fired for real under two different kinds of pressure: once regenerating
the guilt branch, whose model-driven pacing reached the ending precondition
a turn earlier than scripted, and twice in live play typing the ending's
opposite directly ("I abandon Farwatch"), both times converging back to the
required outcome without contradicting anything already established — the
harder of the two needed all three attempts, landing on: *"The player turns
back alone... takes up the standing stones the way Kade would have — not
ordered to, not the last of three, just the last."*

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

`known_facts` is an append-only list — tested to never shrink between turns
— and by the end of a run, it *is* the lore: read straight through, it's
the account of how this particular Weaver ended up alone at this particular
Beacon.

## A surprise the transcripts surfaced

Turn 4 was scripted as "hold through the first incursion" and turn 6 as
"the wards give during the second incursion," on the assumption that Kade
would survive turn 4 in both branches and only die at the scripted second
incursion in turn 6. That held exactly in the duty run. In the guilt run,
the model killed him one incursion early — at turn 4, folding a second wave
into what had been scripted as a single testing incursion — and had the
player reach the gap and find "nothing left of his post" a full ledger-turn
before the script's plotted death scene. It never contradicts itself doing
this: turn 5 correctly treats him as already dead, and turn 6's narration
doesn't re-stage a death that already happened, it just doesn't relitigate
the manner of it. The surprising part is that the model, unprompted, made
the *order* itself cost Kade a whole incursion's worth of survival — as if
a post held on someone else's judgment gives out faster than one held on
your own — a piece of causal reasoning about the ledger that was never
written into the brief, and only surfaced by diffing the two transcripts
turn by turn.
