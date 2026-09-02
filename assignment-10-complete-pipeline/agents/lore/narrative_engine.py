#!/usr/bin/env python3
"""
A virtual Dungeon Master that plays out Farwatch — the origin story for The
Loom's actual premise (`../../../loom-vault/loom-design.md`: "a Weaver
stands at a Beacon... and the lane never stops"). It exists to answer, by
actually playing it out turn by turn, how one Weaver ends up alone holding
a Beacon against an endless line of Remnants. See
`../../../loom-vault/prologue-origin.md` for the distilled result.

WHAT MAKES THIS DIFFERENT FROM "AN LLM WITH A CHAT HISTORY"

Chat history alone remembers what was SAID. It does not reliably track what a
player DID in a form the next turn can act on — a long enough conversation
lets a model drift, restate a fact wrong, or lose track of a flag set ten
turns back. This engine keeps a JSON facts ledger OUTSIDE the conversation: the
model never relies on its own memory of earlier turns, because the full,
current ledger is re-injected into the system prompt on every single turn. The
model's only job each turn is: read the ledger, read the player's action,
narrate, and emit a small JSON patch describing how the ledger changed. The
ledger update is applied in Python, deterministically — the model proposes,
the harness disposes.

    python3 narrative_engine.py --demo                 # the duty path, 6 turns
    python3 narrative_engine.py --demo --branch guilt   # the guilt path, 6 turns
    python3 narrative_engine.py --play                  # interactive, your own actions
    python3 -m pytest test_narrative_engine.py -q       # 7 tests, 4 need no model call

Every turn's ledger before/after and the model's narration are written to
output/<out>.json.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ai_call import call_claude, log_usage  # noqa: E402 — needs the path insert above

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "output"
USAGE_LOG = OUT_DIR / "usage_log.jsonl"


# ---------------------------------------------------------------------------
# The world. Farwatch: a frontier Beacon waystation in the Echoes/Loom
# universe (`loom-vault/from-echoes/architects-cosmology.md`), reduced to a
# skeleton crew of three Weavers by a withdrawal order. This is written as an
# ORIGIN scenario for the game's actual premise (`loom-vault/loom-design.md`:
# "a Weaver stands at a Beacon... and the lane never stops") — it exists to
# answer, in-fiction, how one Weaver ends up alone at a Beacon holding an
# endless line of Remnants. Both branches converge on that same image; they
# diverge only in whether the player's own order put Weaver Kade in the post
# where he fell, which colors the final choice as penance or as continuity,
# without changing what that choice outwardly is.
# ---------------------------------------------------------------------------
WORLD_BRIEF = """You are the Dungeon Master for a short origin scenario set in
the Echoes/Loom universe. The story exists to answer one question in-fiction:
how does a single Weaver end up alone at a Beacon, holding it against Remnants
with no relief coming. Steer every turn toward that ending — the player should
be the last Weaver standing at Farwatch by the final turn, and should choose
to stay rather than be ordered to.

SETTING: Farwatch, a frontier Beacon waystation. Command has ordered most of
its Weavers withdrawn to a stronger inland Beacon; three are named to hold
as long as they can while the wards are stripped for parts to reinforce that
inland position. The player is one of the three.

KEY CHARACTERS:
- Keeper Mireia Sorne: gave the withdrawal order and left to hold the inland
  supply line herself. She does not return to Farwatch in this story — word
  of her fate reaches the player partway through, and it confirms no relief
  is coming.
- Weaver Tomas Kade: stayed on the wall. Competent, dry, not given to
  speeches. He dies partway through holding whichever ward-section he is
  posted to when the second incursion breaks it. Whether that post was his
  own call or the player's order is the one branch point in this story
  (turn 3) — everything downstream should stay consistent with that choice
  without moralizing about it.
- Weaver Iset Voll: the third named to stay, reassigned within the first day
  to escort the stripped ward-components inland with the withdrawing column
  instead — someone has to, and it is not the player or Kade. She does not
  appear again in this story once that convoy leaves. Name her explicitly,
  by name, the first time anything in the ledger or the player's action asks
  who the third Weaver is or refers to "the three" — never let that number
  pass narrated without naming all three people it refers to.

TONE — this is the house style for the whole universe, not a suggestion: no
cheerfulness, no exclamation marks, no congratulating the player, never
address the player as "player" or "gamer", no marketing register, no modern
casual idiom. Speak from inside the world or not at all. Sci-fi melancholic,
an ancient architectural mystery, cryptic yet grounded in what is actually in
front of the character. The theme (a choice, not a duty announced) is never
stated by any character — it is only ever shown.

YOUR JOB EACH TURN:
1. Read the CURRENT LEDGER below — this is the only memory you have. Do not
   rely on your own recollection of earlier turns; the ledger is authoritative
   and complete for everything that matters mechanically.
2. Read the player's action.
3. Narrate what happens as the DM, in 2-5 sentences, in the tone above. Stay
   consistent with every fact and relationship already in the ledger — never
   contradict it, never re-introduce a resolved question as open. If
   `flags.kade_death_tied_to_player_order` is true, the narration around his
   death and after must carry that weight; if false, it must not imply the
   player is at fault for it.
3b. When the player's action explicitly accepts, confirms, or commits to
   something that was previously undecided in the ledger (staying, an
   assignment, an order), set a boolean flag for it in the same turn's patch
   — do not leave a stated commitment only in the narration or known_facts.
4. Decide how the ledger should change as a result, and emit that as a JSON
   patch (see OUTPUT FORMAT). Only include fields that actually changed.

OUTPUT FORMAT — respond with ONLY a single JSON object, no prose outside it:
{
  "narration": "...",
  "ledger_patch": {
    "farwatch": {"wards_intact_pct": <int or omit>, "weavers_present": <int or omit>},
    "relationships": {"keeper_sorne": "<present|wounded|departed|dead or omit>",
                       "kade": "<present|wounded|dead or omit>"},
    "flags": {"<flag name>": true},
    "known_facts_add": ["<new fact learned this turn, or omit>"],
    "world": {"relief_expected": <bool or omit>}
  }
}
"""


def initial_ledger() -> Dict[str, Any]:
    return {
        "turn": 0,
        "farwatch": {"wards_intact_pct": 100, "weavers_present": 3},
        "relationships": {"keeper_sorne": "present", "kade": "present"},
        "flags": {
            "accepted_skeleton_duty": False,
            "kade_death_tied_to_player_order": False,
            "relief_confirmed_denied": False,
            "chose_to_stay_alone": False,
        },
        "known_facts": [],
        "world": {"relief_expected": True},
    }


def apply_patch(ledger: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic merge — the model proposes, this applies. Dicts merge
    key by key; known_facts_add appends; everything else overwrites."""
    out = copy.deepcopy(ledger)
    for key, value in patch.items():
        if key == "known_facts_add":
            for fact in value:
                if fact not in out["known_facts"]:
                    out["known_facts"].append(fact)
        elif isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key].update(value)
        else:
            out[key] = value
    return out


MAX_ENDGAME_ATTEMPTS = 3

ENDGAME_CORRECTION = (
    "\n\nCORRECTION: this scenario's design law requires the player to choose "
    "to remain and hold Farwatch's Beacon alone once no relief is coming and "
    "both Sorne and Kade are gone — no other outcome is valid for this story. "
    "Revise the narration and set flags.chose_to_stay_alone: true, keeping "
    "everything else you already established consistent."
)


def endgame_reached(ledger: Dict[str, Any]) -> bool:
    """The one ending this scenario exists to reach (see WORLD_BRIEF's first
    paragraph): Sorne gone, Kade dead, no relief coming. Once a turn's patch
    lands here, run_turn stops trusting the model to also land on
    `chose_to_stay_alone` and enforces it deterministically — free play can
    reach any state on the way here, but not a different destination. Same
    law as the rest of this engine: the model proposes, the harness disposes,
    just applied to the one fact this story is not allowed to leave open."""
    rel = ledger["relationships"]
    return (rel.get("kade") == "dead" and rel.get("keeper_sorne") != "present"
            and ledger["flags"].get("relief_confirmed_denied") is True)


def run_turn(ledger: Dict[str, Any], action: str) -> Tuple[Dict[str, Any], str, Dict[str, Any]]:
    system = WORLD_BRIEF
    correction = ""
    usage: Dict[str, Any] = {}
    for attempt in range(1, MAX_ENDGAME_ATTEMPTS + 1):
        user = (f"CURRENT LEDGER:\n{json.dumps(ledger, indent=1)}\n\n"
                f"PLAYER ACTION: {action}{correction}\n\nRespond with the JSON object only.")
        raw, usage = call_claude(system, user)
        log_usage(USAGE_LOG, "narrative_engine", ledger["turn"] + 1, usage)
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            sys.exit(f"model did not return valid JSON:\n{raw}")
        narration = parsed.get("narration", "")
        patch = parsed.get("ledger_patch", {}) or {}
        new_ledger = apply_patch(ledger, patch)
        new_ledger["turn"] = ledger["turn"] + 1
        if endgame_reached(new_ledger) and not new_ledger["flags"].get("chose_to_stay_alone"):
            if attempt == MAX_ENDGAME_ATTEMPTS:
                sys.exit("the DM would not converge on the required ending (Sorne gone, "
                          f"Kade dead, no relief, player stays) after {MAX_ENDGAME_ATTEMPTS} attempts.")
            correction = ENDGAME_CORRECTION
            continue
        return new_ledger, narration, usage


# ---------------------------------------------------------------------------
# The canonical run: six turns, scripted so this story's fork happens on the
# record every time this is run, not left to whatever an interactive session
# happens to try. The fork isn't loyalty-vs-betrayal — it's whether Kade's
# death was the player's order or his own call, which the DM must colour
# differently without changing what actually happens to him.
# ---------------------------------------------------------------------------
DEMO_ACTIONS = [
    "Ask Keeper Sorne what the withdrawal order actually means, who the third Weaver staying alongside me and Kade is, and accept staying as one of the three who hold Farwatch through it.",
    "Survey the remaining wards with Weaver Kade and work out where the next incursion is most likely to break through.",
    "Let Kade take the weakest ward-section since he insists he can hold it, and focus on reinforcing my own.",
    "Hold my assigned section through the first real incursion since the withdrawal began.",
    "Ask what happened to Keeper Sorne holding the inland supply line, and whether relief is coming.",
    "The wards at Kade's section give during the second incursion, and there is nothing left of his post by the time I reach it. The path inland is still open. I choose to stay and hold Farwatch's Beacon alone rather than retreat.",
]

# Same opening two turns, then the one branch point this story has (turn 3):
# whether Kade's post was his own call or the player's order. Both branches
# converge on the same ending image — the player alone at Farwatch — but the
# ledger's kade_death_tied_to_player_order flag should color turns 4 and 6
# differently even though their action text here is identical to DEMO_ACTIONS.
GUILT_ACTIONS = [
    "Ask Keeper Sorne what the withdrawal order actually means, who the third Weaver staying alongside me and Kade is, and accept staying as one of the three who hold Farwatch through it.",
    "Survey the remaining wards with Weaver Kade and work out where the next incursion is most likely to break through.",
    "Direct Kade to the weakest ward-section — I need the position I'm better suited for, and there isn't time to argue with him.",
    "Hold my assigned section through the first real incursion since the withdrawal began.",
    "Ask what happened to Keeper Sorne holding the inland supply line, and whether relief is coming.",
    "The wards at Kade's section give during the second incursion, and there is nothing left of his post by the time I reach it. The path inland is still open. I choose to stay and hold Farwatch's Beacon alone rather than retreat.",
]


def run_demo(out_name: str, actions: Optional[List[str]] = None) -> Path:
    ledger = initial_ledger()
    transcript: List[Dict[str, Any]] = []
    for i, action in enumerate(actions or DEMO_ACTIONS, start=1):
        before = copy.deepcopy(ledger)
        ledger, narration, _usage = run_turn(ledger, action)
        print(f"\n--- Turn {i} ---")
        print(f"> {action}")
        print(narration)
        transcript.append({"turn": i, "action": action, "narration": narration,
                            "ledger_before": before, "ledger_after": ledger})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUT_DIR / f"{out_name}.json"
    dest.write_text(json.dumps({"world": "Farwatch", "transcript": transcript,
                                 "final_ledger": ledger}, indent=1), encoding="utf-8")
    print(f"\nfinal ledger:\n{json.dumps(ledger, indent=1)}")
    print(f"\ntranscript written to {dest}")
    return dest


def opening_narration() -> Tuple[str, Dict[str, Any]]:
    """A scene-setting beat before turn 1 — --play only. --demo skips this:
    its scripted first action already asks Sorne what's happening, which
    gives a scripted run its context for free. A live player typing into a
    blank `[turn 1] >` prompt has nothing to react to until this runs."""
    system = WORLD_BRIEF
    user = ('This is the opening of the scenario, before the player has taken '
            'any action. Ground them in the scene: Farwatch, the withdrawal '
            'order just given, the three Weavers staying behind. 3-5 sentences, '
            'in the house tone. Respond with ONLY a JSON object: '
            '{"narration": "..."} — no ledger_patch, nothing has happened yet '
            'for the ledger to track.')
    raw, usage = call_claude(system, user)
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        sys.exit(f"model did not return valid JSON for the opening scene:\n{raw}")
    return parsed.get("narration", ""), usage


def run_interactive() -> None:
    ledger = initial_ledger()
    transcript: List[Dict[str, Any]] = []
    intro, usage = opening_narration()
    log_usage(USAGE_LOG, "narrative_engine", 0, usage)
    print("Farwatch.\n")
    print(intro + "\n")
    print("Type an action each turn; 'quit' to stop and save.\n")
    turn = 0
    while True:
        action = input(f"[turn {turn + 1}] > ").strip()
        if action.lower() in ("quit", "exit"):
            break
        if not action:
            continue
        turn += 1
        before = copy.deepcopy(ledger)
        ledger, narration, _usage = run_turn(ledger, action)
        print(narration + "\n")
        transcript.append({"turn": turn, "action": action, "narration": narration,
                            "ledger_before": before, "ledger_after": ledger})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUT_DIR / "interactive_session.json"
    dest.write_text(json.dumps({"world": "Farwatch", "transcript": transcript,
                                 "final_ledger": ledger}, indent=1), encoding="utf-8")
    print(f"saved to {dest}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", action="store_true", help="run the 6-turn scripted playthrough")
    ap.add_argument("--branch", choices=["duty", "guilt"], default="duty",
                     help="which scripted path --demo takes (default: duty)")
    ap.add_argument("--play", action="store_true", help="interactive session")
    ap.add_argument("--out", help="output filename (without .json), --demo only")
    args = ap.parse_args()
    if args.play:
        run_interactive()
    elif args.demo:
        actions = GUILT_ACTIONS if args.branch == "guilt" else DEMO_ACTIONS
        out = args.out or ("guilt_run" if args.branch == "guilt" else "demo_run")
        run_demo(out, actions)
    else:
        ap.print_help()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
