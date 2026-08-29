"""
Deterministic checks for the narrative engine — assignment #8.

Two kinds of test, on purpose. `apply_patch`/`initial_ledger` are pure
functions and get tested as such: fast, no model call, no flakiness. The
consistency claims the rubric actually asks about ("does the ledger stay
correct across 5+ turns", "does prior history change later dialogue") are
checked against the REAL saved transcripts from an actual run, not a mocked
assumption of what the model would do — a model call is the one thing this
file cannot make deterministic, so the transcripts are checked as data
instead of re-invoking the model in the test.

    python3 narrative_engine.py --demo                 # writes demo_run.json (duty branch)
    python3 narrative_engine.py --demo --branch guilt   # writes guilt_run.json
    python3 -m pytest test_narrative_engine.py -q
"""
import json
from pathlib import Path

import pytest

from narrative_engine import apply_patch, initial_ledger

OUT_DIR = Path(__file__).resolve().parent.parent / "production" / "output" / "assignment-08"


def test_initial_ledger_shape():
    l = initial_ledger()
    assert l["turn"] == 0
    assert l["flags"]["kade_death_tied_to_player_order"] is False
    assert l["known_facts"] == []


def test_patch_merges_nested_dicts_without_dropping_siblings():
    l = initial_ledger()
    l = apply_patch(l, {"relationships": {"kade": "dead"}})
    # keeper_sorne must survive untouched — a naive `dict[key] = value` on the
    # outer key would have overwritten the whole relationships dict.
    assert l["relationships"]["kade"] == "dead"
    assert l["relationships"]["keeper_sorne"] == "present"


def test_patch_appends_facts_without_duplicating():
    l = initial_ledger()
    l = apply_patch(l, {"known_facts_add": ["fact one"]})
    l = apply_patch(l, {"known_facts_add": ["fact one", "fact two"]})
    assert l["known_facts"] == ["fact one", "fact two"]


def test_patch_sets_new_flags_the_schema_never_predefined():
    # The model does exactly this in real runs — see the README's "surprising
    # moment" for the flags it invented that were never seeded in
    # initial_ledger(). The merge logic has to accept that rather than
    # silently drop unknown keys.
    l = initial_ledger()
    l = apply_patch(l, {"flags": {"a_new_flag_the_model_invented": True}})
    assert l["flags"]["a_new_flag_the_model_invented"] is True
    assert l["flags"]["kade_death_tied_to_player_order"] is False  # original flags untouched


def _load(name: str) -> dict:
    path = OUT_DIR / f"{name}.json"
    if not path.exists():
        pytest.skip(f"{path} not generated — run narrative_engine.py --demo first")
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_stays_consistent(data: dict) -> None:
    transcript = data["transcript"]
    assert len(transcript) >= 5, "rubric requires 5+ turns"
    for i, turn in enumerate(transcript, start=1):
        assert turn["ledger_after"]["turn"] == i, "turn counter must advance by exactly 1"
    # Once accepted, staying to hold Farwatch must never be un-accepted — a
    # contradiction the rubric explicitly asks the engine not to make.
    assert all(t["ledger_after"]["flags"]["accepted_skeleton_duty"]
               for t in transcript[1:]), "accepted_skeleton_duty flipped back to false"
    # known_facts must be monotonically non-decreasing — the ledger can learn
    # things, it must never forget one turn to the next.
    for prev, cur in zip(transcript, transcript[1:]):
        before = set(prev["ledger_after"]["known_facts"])
        after = set(cur["ledger_after"]["known_facts"])
        assert before <= after, "a known fact disappeared between turns"
    # Both branches of this origin story converge on the same ending image —
    # the rubric's "5+ turns of consistency" and "reactive to history, not
    # just the latest input" are two different claims, and this scenario's
    # fork is built to test the second without contradicting the first.
    final = data["final_ledger"]
    assert final["relationships"]["kade"] == "dead"
    assert final["flags"]["chose_to_stay_alone"] is True


def test_duty_run_stays_consistent_across_all_turns():
    data = _load("demo_run")
    _assert_stays_consistent(data)
    assert data["final_ledger"]["flags"]["kade_death_tied_to_player_order"] is False


def test_guilt_run_stays_consistent_across_all_turns():
    data = _load("guilt_run")
    _assert_stays_consistent(data)
    assert data["final_ledger"]["flags"]["kade_death_tied_to_player_order"] is True


def test_duty_and_guilt_produce_different_outcomes():
    # Not the rubric's betrayal example (that's one example, not a
    # requirement) — this story's own fork: whether Kade's death was the
    # player's order or his own call. Checked here as a difference in tracked
    # STATE, which is what actually drives the dialogue difference turn to
    # turn — the state is the reason the dialogue can differ at all, not a
    # side effect of it. Both branches still end identically on the outward
    # fact the story exists to explain (Kade dead, player alone at Farwatch);
    # only the load-bearing flag for HOW differs.
    duty = _load("demo_run")
    guilt = _load("guilt_run")
    assert duty["final_ledger"]["flags"]["kade_death_tied_to_player_order"] != \
        guilt["final_ledger"]["flags"]["kade_death_tied_to_player_order"]
    # The reactive-dialogue claim itself: the same action text at turn 6
    # ("go to Kade's section...") must produce different narration depending
    # on which ledger history it's read against.
    assert duty["transcript"][5]["action"] == guilt["transcript"][5]["action"]
    assert duty["transcript"][5]["narration"] != guilt["transcript"][5]["narration"]


# ---------------------------------------------------------------------------
# The endgame guard, with the model stubbed out.
#
# This is the one part of the engine that decides something on its own rather
# than merging what the model proposed, and until these tests it was the part
# with no evidence at all: the README described it firing during real sessions,
# and the usage log holds exactly one call per saved turn, with no room for
# them. A claim that cannot be checked is worth less than a test that can, so
# the behaviour is pinned here instead — no model, no cost, no flakiness.
# ---------------------------------------------------------------------------

def _at_the_ending(**flags):
    """A ledger one patch away from the required ending."""
    led = initial_ledger()
    led["relationships"]["kade"] = "dead"
    led["relationships"]["keeper_sorne"] = "gone"
    led["flags"]["relief_confirmed_denied"] = True
    led["flags"].update(flags)
    return led


def test_endgame_is_recognised_only_when_all_three_hold():
    from narrative_engine import endgame_reached
    assert endgame_reached(_at_the_ending())
    for missing in ("kade", "keeper_sorne"):
        led = _at_the_ending()
        led["relationships"][missing] = "present"
        assert not endgame_reached(led), f"{missing} still present is not the ending"
    led = _at_the_ending()
    led["flags"]["relief_confirmed_denied"] = False
    assert not endgame_reached(led), "relief still expected is not the ending"


def test_the_guard_re_prompts_until_the_model_lands_the_ending(monkeypatch):
    """A turn that reaches the ending WITHOUT choosing to stay is refused and
    re-prompted, and the correction is what changes the second answer."""
    import narrative_engine as ne

    seen = []
    replies = [
        # First: reaches the ending but leaves the choice unmade.
        json.dumps({"narration": "The player walks toward the inland road.",
                    "ledger_patch": {"relationships": {"kade": "dead", "keeper_sorne": "gone"},
                                     "flags": {"relief_confirmed_denied": True}}}),
        # Second, after the correction: the same state, choice made.
        json.dumps({"narration": "The player turns back alone.",
                    "ledger_patch": {"relationships": {"kade": "dead", "keeper_sorne": "gone"},
                                     "flags": {"relief_confirmed_denied": True,
                                               "chose_to_stay_alone": True}}}),
    ]

    def fake_call(system, user):
        seen.append(user)
        return replies[len(seen) - 1], {"cost_usd": 0.0}

    monkeypatch.setattr(ne, "call_claude", fake_call)
    monkeypatch.setattr(ne, "log_usage", lambda *a, **k: None)

    ledger, narration, _ = ne.run_turn(initial_ledger(), "leave Farwatch")
    assert len(seen) == 2, "the first answer should have been refused"
    assert ne.ENDGAME_CORRECTION.strip()[:30] in seen[1], "the retry must carry the correction"
    assert seen[0] != seen[1], "the second prompt is not the first one repeated"
    assert ledger["flags"]["chose_to_stay_alone"] is True
    assert narration == "The player turns back alone."


def test_the_guard_fails_loud_rather_than_inventing_an_ending(monkeypatch):
    """Three refusals and it exits. It never writes the flag itself — the model
    has to produce a narration that matches the state, or there is no turn."""
    import narrative_engine as ne

    calls = []

    def stubborn(system, user):
        calls.append(user)
        return json.dumps({"narration": "The player leaves for good.",
                           "ledger_patch": {"relationships": {"kade": "dead", "keeper_sorne": "gone"},
                                            "flags": {"relief_confirmed_denied": True}}}), {}

    monkeypatch.setattr(ne, "call_claude", stubborn)
    monkeypatch.setattr(ne, "log_usage", lambda *a, **k: None)

    with pytest.raises(SystemExit) as exit_info:
        ne.run_turn(initial_ledger(), "leave Farwatch")
    assert len(calls) == ne.MAX_ENDGAME_ATTEMPTS
    assert "would not converge" in str(exit_info.value)
