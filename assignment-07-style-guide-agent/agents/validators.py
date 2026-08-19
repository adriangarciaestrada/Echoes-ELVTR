#!/usr/bin/env python3
"""
Echoes — Deterministic Content Validator (validators.py)

The hard gate of the generate-then-judge pipeline. Generator agents (Level
Designer, Encounter Designer, Lore Scribe, Boss-Brain, UI Designer, Game-Feel)
emit JSON; this module enforces the countable rules deterministically in Python
BEFORE anything reaches the Unreal DataTable seam. The LLM reviewers
(03 Room Reviewer, 05 Style Guard, 09 Design Critic) are the semantic second
layer on top of this — they do not replace it.

Single source of truth:
  - The banned/approved TERM TABLE is parsed live from
    vault/00-core/terminology-guard.md (a real markdown table, reliably
    parseable), so the list never drifts from the design.
  - The ENEMY ROSTER is parsed from vault/02-enemies/enemy-palette-overview.md.
  - The CUT-FEATURE denylist and the BANNED REGION REFERENCES are parsed from
    vault/07-ui-and-controls/hud-and-screens.md and vault/00-core/terminology-guard.md
    by ui_rules, so adding one is an edit to a note and nothing else.
  - Numeric thresholds (room budgets, enemy budgets) are named constants below,
    each annotated with its vault source note. They change rarely; if the vault
    numbers change, update them here.
  - The UI numbers are the exception, and the pattern to copy: they are constants
    in ui_rules.py, and test_ui_rules.py parses ui-budgets.md and fails if the two
    disagree — the note stays authoritative without the gate parsing prose at run
    time, and drift breaks the build instead of changing what ships.

Usage:
  python3 agents/validators.py --kind room     --file room.json
  python3 agents/validators.py --kind rooms    --file segment.json   # variety across a batch
  python3 agents/validators.py --kind encounter --file enc.json  [--room room.json]
  python3 agents/validators.py --kind text     --file lore.json
  python3 agents/validators.py --kind goap     --file brain.json
  python3 agents/validators.py --kind umg      --file screen.json
  python3 agents/validators.py --kind strings  --file table.json [--umg screen.json ...]
  python3 agents/validators.py --kind feel     --file feel.json
  cat lore.json | python3 agents/validators.py --kind text

Exit code 0 = PASS (no errors), 1 = FAIL. A JSON report is printed to stdout.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import room_rules as rr
import ui_rules as ur

BASE_DIR = Path(__file__).resolve().parent.parent
VAULT_DIR = BASE_DIR / "vault"

# --- Numeric thresholds (each cites its vault source note) ------------------
# vault/04-world/room-constraints.md — measured on the cavity's bounding box,
# which vault/04-world/roomspec.md computes rather than letting a spec declare.
WIDTH_MIN, WIDTH_MAX = 2000, 6000
HEIGHT_MIN, HEIGHT_MAX = 1000, 3000
# vault/02-enemies/enemy-palette-overview.md
ENEMY_MIN, ENEMY_MAX = 2, 5          # a combat room holds 2..5 enemies (0 = safe room)
MAX_ARCHETYPES = 2
# The Spanish allowance, the per-widget-class caps and the UI set-level counts all
# live in ui_rules.py, sourced from vault/07-ui-and-controls/ui-budgets.md and held
# to it by test_ui_rules.py. They are not restated here.

# --- Enums (from the room/encounter schemas) --------------------------------
SEGMENTS = {"SegmentA_Shared", "SegmentB_Hunter", "SegmentB_Titan", "Convergence"}
GATE_TOOLS = {"None", "Grapple", "Bash", "Keycard"}
FACINGS = {"Left", "Right"}
DOOR_SIDES = {"Left", "Right", "Top", "Bottom"}
# vault/04-world/roomspec.md — coordinates are multiples of the room's grid.
DEFAULT_GRID = 20
# A class-exclusive branch must never require the opposite class's tool.
FORBIDDEN_GATE_BY_SEGMENT = {"SegmentB_Hunter": "Bash", "SegmentB_Titan": "Grapple"}

# --- UMG spec (agent 07 schema + vault/07-ui-and-controls/hud-and-screens.md) --
SCREEN_IDS = ur.SCREEN_IDS                   # vault/07-ui-and-controls/uispec.md
STRING_TABLE_KEY_RE = ur.KEY_RE
# The excluded-element list is no longer a constant here. It is one row family of
# the cut-feature denylist in vault/07-ui-and-controls/hud-and-screens.md, parsed
# by ui_rules so that adding a cut feature is an edit to the note and nothing else.

# --- Feel table (agent 12 schema + vault/07-ui-and-controls/control-scheme.md
#     + vault/01-classes/class-asymmetry-contract.md) ---------------------------
FEEL_ENUMS = {
    "class": {"Hunter", "Titan"},
    "jump_type": {"double", "lift"},
    "defense_type": {"dodge_iframe", "absorbing_shield"},
    "turnaround": {"instant", "momentum"},
    "cancel_priority": {"defense", "fire"},
    "traversal_tool": {"grapple", "bash"},
}
# One motor vocabulary, two dialects: each class's verb execution is fixed.
CLASS_CONTRACT = {
    "Hunter": {"jump_type": "double", "defense_type": "dodge_iframe", "traversal_tool": "grapple"},
    "Titan":  {"jump_type": "lift",   "defense_type": "absorbing_shield", "traversal_tool": "bash"},
}
# Playable-bounds guardrails. These are NOT vault numbers: they bracket the
# vault defaults (coyote 120ms, buffer 150ms, dodge 400/250ms, lag 0ms) at
# roughly 2-3x so the QA sweep can explore while absurd values still fail.
COYOTE_MAX_MS = 400
JUMP_BUFFER_MAX_MS = 400
DODGE_TOTAL_MIN_MS, DODGE_TOTAL_MAX_MS = 100, 1000
LANDING_LAG_MAX_MS = 500


def _is_number(v) -> bool:
    """True for int/float but NOT bool (bool is a subclass of int in Python)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _err(errors: List[Dict], code: str, message: str, path: str = ""):
    errors.append({"code": code, "message": message, "path": path})


# --------------------------------------------------------------------------
# Vault-sourced rule data (parsed live so it never drifts from the design)
# --------------------------------------------------------------------------
def load_banned_and_approved() -> Dict[str, set]:
    """Parses the banned/approved term table from terminology-guard.md.

    Returns {"banned": set[str], "approved": set[str]}. Cells may list several
    terms separated by '/'. Fails loud if the table cannot be found.
    """
    note = VAULT_DIR / "00-core" / "terminology-guard.md"
    if not note.exists():
        sys.exit(f"❌ Missing source of truth: {note}")
    banned, approved = set(), set()
    seen_header = False
    for line in note.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        low = cells[0].lower()
        if "banned" in low:            # header row
            seen_header = True
            continue
        if set(cells[0]) <= {"-", ":"}:  # separator row
            continue
        if not seen_header:
            continue
        for token in re.split(r"/", cells[0]):
            t = re.sub(r"[*_`]", "", token).strip()
            if t:
                banned.add(t)
        for token in re.split(r"/", cells[1]):
            t = re.sub(r"[*_`]", "", token).strip()
            if t:
                approved.add(t)
    if not banned:
        sys.exit(f"❌ Parsed zero banned terms from {note}; refusing to run a no-op guard.")
    return {"banned": banned, "approved": approved}


SENTENCE_START_RE = re.compile(r'(?:^|[.!?:;\n])\s*["“«(]?\s*$')


def ip_term_hits(text: str, banned: Iterable[str]) -> Tuple[List[str], List[str]]:
    """(certain, ambiguous) banned-term hits in `text`.

    A term listed with a capital is banned only in that form: `Light` is the
    Destiny placeholder and `light` is a word a world of decaying ruins needs.
    The capital is the signal that the word is a proper noun, so the guard reads
    the capital rather than the letters.

    Where the capital carries no information — at the start of a sentence, where
    it is mandatory — the hit is *ambiguous*: reported, not failed. The gate does
    not guess at intent it cannot see, and the Style & IP Guard settles it.

    A term listed lowercase has no proper-noun signal to lose and stays
    case-insensitive.
    """
    certain, ambiguous = [], []
    for term in sorted(banned):
        if not term:
            continue
        cased = term[:1].isupper()
        flags = 0 if cased else re.IGNORECASE
        for match in re.finditer(r"\b" + re.escape(term) + r"\b", text, flags):
            if cased and SENTENCE_START_RE.search(text[:match.start()]):
                ambiguous.append(term)
            else:
                certain.append(term)
    return certain, ambiguous


def load_enemy_roster() -> Dict[str, str]:
    """Parses archetype names from enemy-palette-overview.md.

    Returns {normalized_name: canonical_name}. Normalization drops spaces/case so
    schema forms ('LedgeGunner') match vault forms ('Ledge Gunner').
    """
    note = VAULT_DIR / "02-enemies" / "enemy-palette-overview.md"
    if not note.exists():
        sys.exit(f"❌ Missing source of truth: {note}")
    roster: Dict[str, str] = {}
    for line in note.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*\*\*([^*|]+)\*\*\s*\|", line)  # roster table: | **Name** | ... |
        if m:
            canonical = m.group(1).strip()
            roster[re.sub(r"\s+", "", canonical).lower()] = canonical
    if not roster:
        sys.exit(f"❌ Parsed zero archetypes from {note}; refusing to run.")
    return roster


def load_blackboard_spec() -> Dict[str, set]:
    """Parses canonical blackboard keys and goal names from goap-blackboard-spec.md.

    Returns {"keys": set[str], "goals": set[str]}. Keys are the backticked
    identifiers in the '## Shared Blackboard Keys' bullet list; goals are the
    backticked names in the '## Goal Hierarchy' numbered list. Fails loud if
    either comes back empty.
    """
    note = VAULT_DIR / "03-bosses" / "goap-blackboard-spec.md"
    if not note.exists():
        sys.exit(f"❌ Missing source of truth: {note}")
    keys, goals = set(), set()
    for line in note.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        m = re.match(r"-\s*`(\w+)`\s*:", line)
        if m:
            keys.add(m.group(1))
            continue
        m = re.match(r"\d+\.\s*`(\w+)`", line)
        if m:
            goals.add(m.group(1))
    if not keys or not goals:
        sys.exit(f"❌ Parsed {len(keys)} keys / {len(goals)} goals from {note}; refusing to run a no-op guard.")
    return {"keys": keys, "goals": goals}


# --------------------------------------------------------------------------
# Validators
# --------------------------------------------------------------------------
def validate_room(room: Dict) -> List[Dict]:
    """The countable half of room review — see vault/04-world/roomspec.md.

    Four families of rule, in the order a failure is worth hearing about:
    structure (is this a room at all), reach (can the character walk it),
    exclusivity and sight (do the pockets do their job), and finally the
    class-branch rule the encounter side also depends on.
    """
    errors: List[Dict] = []
    if not isinstance(room, dict):
        return [{"code": "ERR_NOT_OBJECT", "message": "Room spec is not a JSON object", "path": ""}]

    if not isinstance(room.get("room_id"), str) or not room.get("room_id"):
        _err(errors, "ERR_FIELD", "room_id must be a non-empty string", "room_id")

    segment = room.get("segment")
    if segment not in SEGMENTS:
        _err(errors, "ERR_ENUM", f"segment must be one of {sorted(SEGMENTS)}", "segment")

    # ---- structure --------------------------------------------------------
    cavity = room.get("cavity")
    if not isinstance(cavity, list) or not cavity:
        _err(errors, "ERR_FIELD", "cavity must be a non-empty list of rectangles; "
             "a room is carved out of solid material, not an empty box", "cavity")
        return errors
    for i, c in enumerate(cavity):
        if not all(_is_number(c.get(k)) for k in ("x", "z", "width", "height")):
            _err(errors, "ERR_FIELD", "cavity rect needs numeric x, z, width, height", f"cavity[{i}]")
            return errors
        if c["width"] <= 0 or c["height"] <= 0:
            _err(errors, "ERR_FIELD", "cavity rect must have positive extent", f"cavity[{i}]")
            return errors

    bounds = rr.cavity_bounds(cavity)
    span_x, span_z = bounds["max_x"] - bounds["min_x"], bounds["max_z"] - bounds["min_z"]
    if not (WIDTH_MIN <= span_x <= WIDTH_MAX):
        _err(errors, "ERR_ROOM_BUDGET", f"cavity spans {span_x:g} wide, outside [{WIDTH_MIN},{WIDTH_MAX}]", "cavity")
    if not (HEIGHT_MIN <= span_z <= HEIGHT_MAX):
        _err(errors, "ERR_ROOM_BUDGET", f"cavity spans {span_z:g} tall, outside [{HEIGHT_MIN},{HEIGHT_MAX}]", "cavity")

    grid = room.get("grid", DEFAULT_GRID)
    if _is_number(grid) and grid > 0:
        for label, items, keys in (("cavity", cavity, ("x", "z", "width", "height")),
                                   ("solids", room.get("solids") or [], ("x", "z", "width", "height")),
                                   ("anchors", room.get("anchors") or [], ("x", "z"))):
            for i, it in enumerate(items):
                for k in keys:
                    v = it.get(k)
                    if _is_number(v) and abs(v / grid - round(v / grid)) > 1e-9:
                        _err(errors, "ERR_OFF_GRID", f"{k}={v:g} is not a multiple of grid {grid:g}",
                             f"{label}[{i}].{k}")

    seen_ids = set()
    for label in ("solids", "anchors", "doors", "checkpoints", "pockets"):
        for i, it in enumerate(room.get(label) or []):
            if not isinstance(it, dict):
                _err(errors, "ERR_FIELD", f"{label} entry must be an object", f"{label}[{i}]"); continue
            eid = it.get("id")
            if not isinstance(eid, str) or not eid:
                _err(errors, "ERR_FIELD", "element needs a non-empty id", f"{label}[{i}]")
            elif eid in seen_ids:
                _err(errors, "ERR_DUPLICATE_ID", f"id '{eid}' is used more than once", f"{label}[{i}]")
            else:
                seen_ids.add(eid)

    for i, s in enumerate(room.get("solids") or []):
        path = f"solids[{i}]"
        if not all(_is_number(s.get(k)) for k in ("x", "z", "width", "height")):
            _err(errors, "ERR_FIELD", "solid needs numeric x, z, width, height", path); continue
        if not rr.box_in_cavity(cavity, s):
            _err(errors, "ERR_IN_ROCK", "solid is not entirely inside the carved space; a wall that "
                 "seals a passage goes across it, not into the rock beside it", path)
        if s.get("breakable_by") not in (None, "Bash"):
            _err(errors, "ERR_ENUM", "breakable_by must be 'Bash' or absent", f"{path}.breakable_by")

    for i, a in enumerate(room.get("anchors") or []):
        if not all(_is_number(a.get(k)) for k in ("x", "z")):
            _err(errors, "ERR_FIELD", "anchor needs numeric x, z", f"anchors[{i}]")
        elif not rr.in_cavity(cavity, a["x"], a["z"]):
            _err(errors, "ERR_IN_ROCK", "anchor is embedded in rock", f"anchors[{i}]")

    for i, d in enumerate(room.get("doors") or []):
        path = f"doors[{i}]"
        if d.get("side") not in DOOR_SIDES:
            _err(errors, "ERR_ENUM", f"door side must be one of {sorted(DOOR_SIDES)}", path)
        if not _is_number(d.get("at")):
            _err(errors, "ERR_FIELD", "door needs a numeric 'at' offset along its side", path)
        tool = d.get("required_tool")
        if tool not in GATE_TOOLS:
            _err(errors, "ERR_ENUM", f"required_tool must be one of {sorted(GATE_TOOLS)}", path)
        if not rr.door_opens_onto_cavity(room, d):
            _err(errors, "ERR_DOOR_INTO_ROCK",
                 f"door '{d.get('id')}' is in the {d.get('side')} wall at height {d.get('at')}, "
                 "and the space just inside it is not carved: it opens onto stone. Extend the "
                 "cavity to meet the wall across the whole opening", path)
        forbidden = FORBIDDEN_GATE_BY_SEGMENT.get(segment)
        if forbidden and tool == forbidden:
            _err(errors, "ERR_CLASS_CROSS_CONTAMINATION",
                 f"{segment} must not contain a '{forbidden}' gate (opposite class)", path)

    for i, c in enumerate(room.get("checkpoints") or []):
        if not all(_is_number(c.get(k)) for k in ("x", "z")):
            _err(errors, "ERR_FIELD", "checkpoint needs numeric x, z", f"checkpoints[{i}]")
        elif not rr.in_cavity(cavity, c["x"], c["z"]):
            _err(errors, "ERR_IN_ROCK", "checkpoint is embedded in rock", f"checkpoints[{i}]")

    # ---- reach along the critical path ------------------------------------
    path_ids = room.get("critical_path")
    if not isinstance(path_ids, list) or len(path_ids) < 2:
        _err(errors, "ERR_FIELD", "critical_path must list at least an entry and an exit; without it "
             "nothing distinguishes the route from an optional pocket", "critical_path")
        return errors

    door_ids = {d.get("id") for d in room.get("doors") or []}
    if path_ids[0] not in door_ids or path_ids[-1] not in door_ids:
        _err(errors, "ERR_PATH_ENDS", "critical_path must begin and end at a door", "critical_path")

    steps = []
    for i, eid in enumerate(path_ids):
        support = rr.support_of(room, eid)
        if support is None:
            door = next((d for d in (room.get("doors") or []) if d.get("id") == eid), None)
            if door is not None:
                # Saying a door is not a door sends a designer looking for a
                # typo. The door exists; nothing stands at its threshold.
                side, at = door.get("side"), door.get("at")
                _err(errors, "ERR_DOOR_UNREACHABLE",
                     f"door '{eid}' is in the {side} wall at height {at}, and nothing the character "
                     f"can stand on reaches that wall at that height. A door opens onto a surface: "
                     f"either put a floor or a ledge against the {side} wall at {at}, or move the "
                     f"door to a height where one already is", f"critical_path[{i}]")
            elif any(c.get("id") == eid for c in cavity):
                # The space exists and was named on purpose; what it lacks is a
                # floor, because another carved space sits directly beneath it.
                _err(errors, "ERR_NO_FLOOR",
                     f"'{eid}' is a carved space with nothing under it: another cavity sits "
                     "directly below, so its lower edge is an open seam rather than a floor and "
                     "the character would fall through. Carving is subtraction, so a space above "
                     "another is one tall volume rather than two rooms. If it is a shaft, name "
                     "the ledges inside it instead of the space; if a surface really belongs "
                     "here, build a solid and name that", f"critical_path[{i}]")
            else:
                _err(errors, "ERR_UNKNOWN_ELEMENT",
                     f"critical_path names '{eid}', which is neither a door nor anything that can "
                     "be stood on", f"critical_path[{i}]")
            return errors
        steps.append((eid, support))

    for (aid, a), (bid, b) in zip(steps, steps[1:]):
        rise, gap = b[2] - a[2], rr.gap_between(a, b)
        if rise > rr.RISE_GUARANTEED:
            _err(errors, "ERR_UNREACHABLE",
                 f"{aid} -> {bid} rises {rise:g}, past the {rr.RISE_GUARANTEED:g} both classes clear "
                 f"without timing. The critical path is the clearability promise", "critical_path")
        elif -rise > rr.RISE_GUARANTEED:
            # Falling obeys no reach band, so a drop of any size is passable and
            # the rule above never sees it. That silence is how a descent becomes
            # one-way: the player commits down a face they cannot climb back, and
            # the room reads as a mistake rather than a decision.
            _err(errors, "ERR_ONE_WAY_DROP",
                 f"{aid} -> {bid} drops {-rise:g}, and only {rr.RISE_GUARANTEED:g} can be climbed "
                 "back. The player would be committed with no way to return. Break the fall into "
                 "landings within the guaranteed rise, or state the room as deliberately one-way",
                 "critical_path")
        if gap > rr.GAP_GUARANTEED:
            # Name the cause, not just the number. Two surfaces can be far apart
            # because there is space between them or because something stands in
            # the way, and the two need opposite repairs: a spec told only that a
            # step "spans 500" will be redrawn closer together, which cannot help
            # when a wall is what divides them. A generator asked to fix a
            # measurement it has misdiagnosed fails the same rule indefinitely.
            wall = None
            for q in room.get("solids") or []:
                if not (min(a[1], b[1]) - rr.EPS <= q["x"] + q.get("width", 0)
                        and q["x"] <= max(a[0], b[0]) + rr.EPS):
                    continue
                if q["z"] <= max(a[2], b[2]) + rr.EPS \
                        and q["z"] + q.get("height", 0) > min(a[2], b[2]) + rr.MAX_STEP + rr.EPS:
                    wall = q
                    break
            if wall is not None:
                _err(errors, "ERR_UNREACHABLE",
                     f"{aid} -> {bid} spans {gap:g}, past the {rr.GAP_GUARANTEED:g} guaranteed band — and "
                     f"the reason is '{wall['id']}' standing between them, not the distance. Moving them "
                     f"closer cannot help"
                     + (f"; a wall the Titan breaks may not divide the critical path, because the Hunter "
                        f"has no verb for it" if wall.get("breakable_by") else "")
                     + ". Route the path around it, or open the way through",
                     "critical_path")
            else:
                _err(errors, "ERR_UNREACHABLE",
                     f"{aid} -> {bid} spans {gap:g}, past the {rr.GAP_GUARANTEED:g} guaranteed band",
                     "critical_path")
        if gap > 0 and (a[1] - a[0]) < rr.RUNUP_MIN and aid not in door_ids:
            _err(errors, "ERR_NO_RUNUP",
                 f"{aid} is {a[1] - a[0]:g} long, under the {rr.RUNUP_MIN:g} needed to reach full speed "
                 f"before the gap to {bid}", "critical_path")

    # ---- the body has to fit where the jump can reach ---------------------
    # Reach and fit are different questions, and only reach was being asked.
    # Platforms spaced exactly RISE_GUARANTEED apart clear every reach rule and
    # cannot be climbed: the spacing is measured surface to surface, so a ledge
    # of its own thickness eats into the air the character needs to stand up in.
    body = 2 * rr.CAPSULE_RADIUS
    for eid, support in steps:
        if eid in door_ids:
            continue
        run = rr.standable_run(room, support, needed=rr.HEADROOM)
        if run < body - 1e-6:
            _err(errors, "ERR_NO_HEADROOM",
                 f"'{eid}' offers {run:g} of width with {rr.HEADROOM:g} of clear space above it, "
                 f"and the character is {rr.CAPSULE_HEIGHT:g} tall and {body:g} wide. There is "
                 "nowhere on this surface to stand up", "critical_path")

    # Somewhere to stand is not the same as a way through. A ledge hanging low
    # over a floor leaves both sides standable and the route between them shut,
    # and the widest-clear-stretch rule above is satisfied by the larger side.
    # So walk each surface from where the route arrives to where it leaves.
    # Where the route enters the first surface: the wall its entry door is in.
    entry = next((d for d in (room.get("doors") or []) if d.get("id") == path_ids[0]), None)
    entry_side = str((entry or {}).get("side", "Left"))
    walked = []          # the arrival point on each step, threaded forward
    for i, (eid, support) in enumerate(steps):
        prev_s = steps[i - 1][1] if i > 0 else None
        next_s = steps[i + 1][1] if i + 1 < len(steps) else None
        if prev_s is None:
            arrive = support[1] if entry_side == "Right" else support[0]
        else:
            arrive = rr.landing_point(prev_s, support, walked[-1])
        walked.append(arrive)
        if next_s is None:
            depart = support[0] if entry_side == "Right" else support[1]
        else:
            depart = rr.takeoff_point(support, next_s, arrive)
        if abs(arrive - depart) < 1e-6 or eid in door_ids:
            # A doorway is an opening in a wall, not a stretch of the room's
            # floor; measuring headroom over it asks the rock a question.
            continue
        spans = rr.standable_intervals(room, support, needed=rr.HEADROOM)
        if not rr.same_interval(spans, arrive, depart):
            _err(errors, "ERR_NO_WAY_THROUGH",
                 f"on '{eid}' the route runs from {arrive:g} to {depart:g}, and something hangs "
                 f"low enough over that stretch to stop the character, who is "
                 f"{rr.CAPSULE_HEIGHT:g} tall. Standing room on either side of an obstruction is "
                 "not a way past it", "critical_path")

    # A low ceiling does not only block walking. Standing under one, the jump is
    # clipped to what is left above the body — which is the whole point of a
    # tight corridor, and means a tight corridor cannot be left upwards however
    # close the ledge above it happens to be.
    for i, ((aid, a), (bid, b)) in enumerate(zip(steps, steps[1:])):
        rise = b[2] - a[2]
        if rise <= 1e-6 or bid in door_ids:
            # Arriving at a doorway is passing through it. A door in the ceiling
            # has its sill at the ceiling, so the clearance above it is zero and
            # every climb to one would read as clipped — by measuring the rock
            # the opening is cut through.
            continue
        # Measured across the stretch the jump covers, not at one point: the
        # character leaves diagonally, so an obstruction directly over the
        # take-off is one it flies out from under. What matters is whether
        # anywhere along the way there is room to make the rise.
        origin = walked[i] if i < len(walked) else None
        x0 = rr.takeoff_point(a, b, origin)
        x1 = rr.landing_point(a, b, origin)
        lo, hi = (x0, x1) if x0 <= x1 else (x1, x0)
        best, x = -1.0, lo
        while x <= hi + 1e-6:
            best = max(best, rr.rise_available(room, x, a[2]))
            x += 20.0
        if best < rise - 1e-6:
            _err(errors, "ERR_JUMP_CLIPPED",
                 f"leaving '{aid}' for '{bid}' means rising {rise:g}, and between x={lo:g} and "
                 f"x={hi:g} the ceiling never allows more than {best:g}. A low ceiling clips the "
                 "jump to whatever is left above the body, so this climb cannot be made",
                 "critical_path")

    # ---- vertical space is built from standard heights --------------------
    # Two named heights and multiples of the standard, so a player learns what
    # one floor means and can judge a room by eye. A height that is nearly
    # standard teaches only that heights are arbitrary.
    for eid, support in steps:
        if eid in door_ids:
            continue
        if not rr.on_half_floor(support[2]):
            _err(errors, "ERR_OFF_MODULE",
                 f"'{eid}' stands at {support[2]:g}, off the {rr.HALF_FLOOR:g} climbing module. "
                 f"Surfaces sit on half-floors so that one landing carries one floor of climb",
                 "critical_path")
    # The module describes the room's spaces, not what happens to be left above
    # a ledge: in a two-floor shaft the clearance over a landing at 200 is 600,
    # and no arrangement of standard heights makes that a multiple. It is the
    # carved space whose height a player reads and learns.
    for i, c in enumerate(cavity):
        if not _is_number(c.get("height")):
            continue
        if rr.height_class(float(c["height"])) is None:
            low = int(c["height"] // rr.FLOOR) * rr.FLOOR
            _err(errors, "ERR_OFF_MODULE",
                 f"this space is {c['height']:g} tall, which is neither a tight corridor "
                 f"({rr.TIGHT:g}) nor a whole number of {rr.FLOOR:g} floors "
                 f"({low or rr.FLOOR:g} or {low + rr.FLOOR:g}). A height that is nearly standard "
                 "teaches the player only that heights are arbitrary", f"cavity[{i}]")

    # A platform directly above the one being jumped from turns the climb into
    # threading the body through the space between them, which is the rise minus
    # the upper platform's thickness — always smaller than the character for any
    # rise it can actually make. Ledges have to alternate, not stack.
    for (aid, a), (bid, b) in zip(steps, steps[1:]):
        if aid in door_ids or bid in door_ids:
            continue
        overlap = rr.climb_is_threaded(room, a, b)
        if overlap is None:
            continue
        # Only when the lower surface is nearly covered. A ledge over a floor is
        # the ordinary way to climb, and rooms built that way have been played:
        # forbidding every overhang refused them on a physics argument the play
        # sessions did not support. What genuinely blocks a climb — no room to
        # stand, a ceiling that clips the jump, no way through — is measured by
        # its own rules, and those still refuse every room this one used to.
        if (a[1] - a[0]) - overlap >= body - 1e-6:
            continue
        _err(errors, "ERR_CLIMB_BLOCKED",
             f"'{bid}' overhangs '{aid}' by {overlap:g}. Standing clear of it means jumping "
             f"almost straight up, and arriving over it costs {body:g} of travel the jump has "
             "no height left to pay for. Either offset them horizontally — a climb between "
             f"ledges alternates rather than stacks — or, if '{aid}' is a floor or a long run, "
             f"rest '{bid}' on it: give it z at that surface and height 200 so it becomes a "
             "step, which nothing has to be jumped clear of", "critical_path")

    # ---- the primary route asks for no tool -------------------------------
    # A traverse key opens a reward, not the story. If the critical path is
    # gated, one class is locked out of the game rather than out of a pocket.
    for i, eid in enumerate(path_ids):
        door = next((d for d in (room.get("doors") or []) if d.get("id") == eid), None)
        if door is not None and door.get("required_tool") not in (None, "None"):
            _err(errors, "ERR_PATH_GATED",
                 f"the critical path passes through '{eid}', which requires "
                 f"'{door.get('required_tool')}'. The primary route is walkable with base "
                 "movement by both classes; tools open pockets and side rooms, not the way "
                 "forward", f"critical_path[{i}]")

    # A pocket named on the critical path needs no rule of its own: a pocket is
    # not something that can be stood on, so resolving the path already refused
    # it above with ERR_UNKNOWN_ELEMENT.

    # ---- a climb is a route, not a ladder ---------------------------------
    # Calibrated against two rooms judged in play: one read as designed and one
    # as generic filler. They had the same number of direction changes and the
    # same lateral travel, so neither of those is the thing. What separated them
    # was that the generic one shuffled between two positions with every ledge
    # the same width, and the other moved across the space with widths that
    # varied.
    lanes = rr.ascent_lanes(room)
    ladder = rr.longest_two_lane_run(lanes)
    if ladder >= 4:
        _err(errors, "ERR_LADDER_CLIMB",
             f"{ladder} steps of the route in a row shuffle between two positions. That is a "
             "ladder: the player repeats one input and sees the same view from every landing. "
             "Send the climb across the room, and carve the space wide enough to let it",
             "critical_path")

    climb_widths = []
    for eid, _ in steps:
        s = next((q for q in (room.get("solids") or []) if q.get("id") == eid), None)
        if s is not None and not s.get("breakable_by"):
            climb_widths.append(s.get("width"))
    if len(climb_widths) >= 3 and len(set(climb_widths)) == 1:
        _err(errors, "ERR_UNIFORM_LEDGES",
             f"all {len(climb_widths)} platforms on the route are {climb_widths[0]:g} wide. Width "
             "is meaning: a wide ledge is a place to stop and fight, a narrow one is a beat of "
             "precision. Identical ones say nothing", "solids")

    # ---- no space the player can see and never enter ----------------------
    for i, s in enumerate(room.get("solids") or []):
        if s.get("breakable_by"):
            continue
        gap = rr.dead_space_under(room, s)
        if gap:
            _err(errors, "ERR_DEAD_SPACE",
                 f"'{s['id']}' floats {gap:g} above what is under it, and the character needs "
                 f"{rr.HEADROOM:g} to get in there. Fill it down and let it be a step, or raise "
                 "it until the space below is usable — a gap nobody can enter reads as an "
                 "oversight, not as a secret", f"solids[{i}]")

    # ---- keys: each needs the space its verb requires ---------------------
    supports = rr.all_supports(room)
    for i, s in enumerate(room.get("solids") or []):
        if not s.get("breakable_by"):
            continue
        base, ok = s["z"], False
        for sup in supports:
            if abs(sup[2] - base) < 1e-6 and (sup[1] - sup[0]) >= rr.BASH_RUNUP \
                    and (abs(sup[1] - s["x"]) < 1e-6 or abs(sup[0] - (s["x"] + s["width"])) < 1e-6):
                ok = True
        if not ok:
            _err(errors, "ERR_NO_RUNUP", f"breakable wall '{s['id']}' has no {rr.BASH_RUNUP:g} of level "
                 "floor against it; the bash only breaks at speed, so a wall with no run-up is sealed "
                 "to everyone", f"solids[{i}]")

    path_supports = [s for _, s in steps]
    for i, a in enumerate(room.get("anchors") or []):
        if not all(_is_number(a.get(k)) for k in ("x", "z")):
            continue
        near = [s for s in supports
                if ((a["x"] - max(s[0], min(a["x"], s[1]))) ** 2 + (a["z"] - s[2]) ** 2) ** 0.5 <= rr.GRAPPLE_RANGE]
        usable = rr.visible_from(room, near, a["x"], a["z"])
        if not usable:
            _err(errors, "ERR_ANCHOR_UNUSABLE", f"anchor '{a['id']}' is not within {rr.GRAPPLE_RANGE:g} "
                 "of anywhere the character can stand with a clear line to it", f"anchors[{i}]")

        # An anchor is a destination, not only a target. The pull ends at the
        # anchor and the Hunter comes down onto whatever is underneath, so there
        # must be an underneath, close below, with room to stand. Found in play:
        # an anchor whose perch hung 60 under the ceiling passed range and sight
        # and stranded the class it exists for.
        landing, drop = rr.anchor_landing(room, a)
        if landing is None or drop > rr.LANDING_DROP_MAX:
            _err(errors, "ERR_ANCHOR_NO_LANDING",
                 f"anchor '{a['id']}' hangs {drop:g} above the nearest surface below it "
                 f"(limit {rr.LANDING_DROP_MAX:g}); the pull would end in a fall the design "
                 "never decided. Put a landing under the anchor", f"anchors[{i}]")
        else:
            spans = rr.standable_intervals(room, landing, needed=rr.HEADROOM)
            body = 2 * rr.CAPSULE_RADIUS
            spot = max(landing[0], min(a["x"], landing[1]))
            if not any(iv[0] - body / 2 <= spot <= iv[1] + body / 2
                       and iv[1] - iv[0] >= body for iv in spans):
                _err(errors, "ERR_ANCHOR_NO_LANDING",
                     f"anchor '{a['id']}' lands on '{landing[3]}', and there is no place on it "
                     f"under the anchor with {rr.HEADROOM:g} of clear space for a "
                     f"{rr.CAPSULE_HEIGHT:g}-tall body. The Hunter arrives and cannot stand up",
                     f"anchors[{i}]")

    # ---- pockets: exclusive, and seen ------------------------------------
    base_reach = rr.reachable_from(room, path_supports, rr.RISE_SKILL, rr.GAP_SKILL)
    for i, p in enumerate(room.get("pockets") or []):
        path = f"pockets[{i}]"
        if not all(_is_number(p.get(k)) for k in ("x", "z")):
            _err(errors, "ERR_FIELD", "pocket needs numeric x, z", path); continue
        if p.get("required_tool") not in ("Grapple", "Bash"):
            _err(errors, "ERR_ENUM", "a pocket is opened by 'Grapple' or 'Bash'", f"{path}.required_tool")
        if any(s[0] - 1e-6 <= p["x"] <= s[1] + 1e-6 and abs(s[2] - p["z"]) < 1e-6 for s in base_reach):
            _err(errors, "ERR_POCKET_NOT_EXCLUSIVE", f"pocket '{p.get('id')}' sits on a surface base "
                 "movement already reaches, so it is not the other class's to claim", path)
        # A reward the right class cannot stand next to is not a reward. The
        # headroom rules guard the critical path; a pocket lives off it by
        # definition, so its footing has to be asked about separately.
        footing = rr.support_under(room, p["x"], p["z"] + 1)
        if footing is not None:
            spans = rr.standable_intervals(room, footing, needed=rr.HEADROOM)
            body = 2 * rr.CAPSULE_RADIUS
            if not any(iv[0] - body / 2 <= p["x"] <= iv[1] + body / 2
                       and iv[1] - iv[0] >= body for iv in spans):
                _err(errors, "ERR_POCKET_NO_FOOTING",
                     f"pocket '{p.get('id')}' sits on '{footing[3]}', which has nowhere with "
                     f"{rr.HEADROOM:g} of clear space to stand — the class that owns this "
                     "reward arrives and cannot collect it", path)
        # What the player is meant to see is the lock, not the prize. A cache on
        # top of a ledge is occluded by that ledge from every point below it;
        # the anchor above it, or the cracked wall beside it, is what reads.
        tool = p.get("required_tool")
        markers = ([(a["id"], a["x"], a["z"]) for a in room.get("anchors") or []]
                   if tool == "Grapple" else
                   [(s["id"], s["x"] + s["width"] / 2, s["z"] + s["height"] / 2)
                    for s in room.get("solids") or [] if s.get("breakable_by")])
        if not markers:
            _err(errors, "ERR_POCKET_NO_MARKER", f"pocket '{p.get('id')}' needs '{tool}' but the room "
                 "holds nothing that verb acts on", path)
        else:
            mid, mx, mz = min(markers, key=lambda m: (m[1] - p["x"]) ** 2 + (m[2] - p["z"]) ** 2)
            if not rr.visible_from(room, path_supports, mx, mz, ignore=mid):
                _err(errors, "ERR_POCKET_UNSEEN", f"the way into pocket '{p.get('id')}' — '{mid}' — is "
                     "not visible from the critical path; a pocket nobody knows they missed motivates "
                     "nothing", path)

    return errors


def validate_room_batch(rooms: List[Dict]) -> List[Dict]:
    """Variety, which is a property of a set of rooms and not of any one of them.

    Left alone, generation converges on the shape that is cheapest to emit — the
    corridor. These rules constrain the experience across a segment (how much the
    rooms make the player turn and climb) rather than naming shapes, so the form
    of any single room stays free.
    """
    errors: List[Dict] = []
    if not isinstance(rooms, list) or not rooms:
        return [{"code": "ERR_NOT_OBJECT", "message": "batch must be a non-empty list of room specs", "path": ""}]

    usable = [r for r in rooms if isinstance(r, dict) and r.get("cavity")]
    if len(usable) != len(rooms):
        _err(errors, "ERR_FIELD", "every entry must be a room spec with a cavity", "")
        return errors

    orientations = [rr.dominant_orientation(r) for r in usable]
    for i, (a, b) in enumerate(zip(orientations, orientations[1:])):
        if a == b and a != "chamber":
            _err(errors, "ERR_MONOTONOUS_SEQUENCE",
                 f"rooms {i} and {i+1} are both {a}; consecutive rooms must not share a dominant "
                 "orientation, which is what makes a route zigzag instead of run straight",
                 f"[{i+1}]")

    if not any(rr.floor_levels(r) >= 3 for r in usable):
        _err(errors, "ERR_FLAT_BATCH", "no room in this batch has three or more distinct floor levels", "")
    # "Taller than wide" means exactly that. An earlier version demanded a ratio
    # of 0.7, which called a 2000x2400 room neither tall nor wide — a threshold
    # stricter than the sentence describing it.
    if not any(rr.aspect(r) < 1.0 for r in usable):
        _err(errors, "ERR_NO_VERTICAL_ROOM", "no room in this batch is taller than it is wide", "")
    if not any(rr.aspect(r) > 1.0 for r in usable):
        _err(errors, "ERR_NO_HORIZONTAL_ROOM", "no room in this batch is wider than it is tall", "")

    turns = [rr.direction_changes(r) for r in usable]
    mean_turns = sum(turns) / len(turns)
    if mean_turns < 2:
        _err(errors, "ERR_TOO_STRAIGHT", f"critical paths average {mean_turns:.1f} direction changes; "
             "under two means the batch reads as corridors", "")

    # A proportion is meaningless below three rooms: one side-only room out of
    # two already exceeds a third, so the rule would fire on every pair.
    side_only = [r for r in usable if rr.door_sides(r) <= {"Left", "Right"}]
    if len(usable) >= 3 and len(side_only) > len(usable) / 3:
        _err(errors, "ERR_CHAIN_TOPOLOGY", f"{len(side_only)} of {len(usable)} rooms have doors only on "
             "Left and Right; a route of those can only be a chain", "")

    # ---- the rooms have to join -------------------------------------------
    # A room carries no world position, so a segment is only a segment if each
    # exit meets the next entrance: facing walls, the same opening, and an offset
    # that keeps both rooms' surfaces on the module. Nothing checked this, and
    # four rooms were generated that cannot be chained.
    for i, (a, b) in enumerate(zip(usable, usable[1:])):
        offset, why = rr.connection(a, b)
        if offset is None:
            _err(errors, "ERR_NOT_CONNECTABLE",
                 f"'{a.get('room_id')}' cannot be followed by '{b.get('room_id')}': {why}",
                 f"[{i + 1}]")

    # ---- the batch must contain more than one shape -----------------------
    # Rules that only reject the worst cases do not produce variety. Generated
    # against the previous set, every room came out the same archetype: a
    # corridor opening into a climb. Nine rooms existed before this rule and not
    # one of them descended.
    shapes = [rr.path_profile(r) for r in usable]
    if len(usable) >= 2 and len(set(shapes)) == 1:
        _err(errors, "ERR_SAME_SHAPE",
             f"all {len(usable)} rooms are {shapes[0]}. A segment made of one shape teaches the "
             "player one thing however varied its dimensions. The vocabulary is ASCENT, DESCENT, "
             "ARCH, BASIN, TERRACE and FLAT", "")
    for i, (a, b) in enumerate(zip(shapes, shapes[1:])):
        if a == b:
            _err(errors, "ERR_SAME_SHAPE",
                 f"rooms {i} and {i + 1} are both {a}; consecutive rooms should not repeat a "
                 "shape, since the contrast is what the player reads", f"[{i + 1}]")

    return errors


def validate_encounter(enc: Dict, room: Optional[Dict] = None) -> List[Dict]:
    errors: List[Dict] = []
    if not isinstance(enc, dict):
        return [{"code": "ERR_NOT_OBJECT", "message": "Encounter spec is not a JSON object", "path": ""}]
    roster = load_enemy_roster()

    if not isinstance(enc.get("room_id"), str) or not enc.get("room_id"):
        _err(errors, "ERR_FIELD", "room_id must be a non-empty string", "room_id")

    spawns = enc.get("spawns", []) or []
    if not isinstance(spawns, list):
        _err(errors, "ERR_FIELD", "spawns must be a list", "spawns")
        spawns = []

    distinct = set()
    has_shieldbearer = False
    for i, s in enumerate(spawns):
        path = f"spawns[{i}]"
        if not isinstance(s, dict):
            _err(errors, "ERR_FIELD", "spawn must be an object", path); continue
        arche = s.get("archetype", "")
        norm = re.sub(r"\s+", "", str(arche)).lower()
        if norm not in roster:
            _err(errors, "ERR_UNKNOWN_ARCHETYPE",
                 f"'{arche}' is not in the closed roster {sorted(roster.values())}", path)
        else:
            distinct.add(roster[norm])
            if roster[norm].lower().replace(" ", "") == "shieldbearer":
                has_shieldbearer = True
        pos = s.get("position", {})
        if not _is_number(pos.get("x")) or not _is_number(pos.get("z")):
            _err(errors, "ERR_FIELD", "spawn.position needs numeric x, z", path)
        if not _is_number(s.get("patrol_range")):
            _err(errors, "ERR_FIELD", "spawn.patrol_range must be a number", path)
        if s.get("facing_direction") not in FACINGS:
            _err(errors, "ERR_ENUM", f"facing_direction must be one of {sorted(FACINGS)}", path)

    budget = enc.get("encounter_budget", {})
    total = budget.get("total_enemies")
    arche_count = budget.get("archetype_count")

    if not _is_number(total):
        _err(errors, "ERR_FIELD", "encounter_budget.total_enemies must be a number", "encounter_budget.total_enemies")
    else:
        if total != len(spawns):
            _err(errors, "ERR_BUDGET_MISMATCH",
                 f"total_enemies={total} but {len(spawns)} spawns listed", "encounter_budget.total_enemies")
        if total != 0 and not (ENEMY_MIN <= total <= ENEMY_MAX):
            _err(errors, "ERR_ENEMY_BUDGET",
                 f"total_enemies must be 0 (safe room) or in [{ENEMY_MIN},{ENEMY_MAX}]", "encounter_budget.total_enemies")

    if len(distinct) > MAX_ARCHETYPES:
        _err(errors, "ERR_ARCHETYPE_BUDGET",
             f"{len(distinct)} distinct archetypes exceeds max {MAX_ARCHETYPES}", "spawns")
    if _is_number(arche_count) and arche_count != len(distinct):
        _err(errors, "ERR_ARCHETYPE_COUNT",
             f"archetype_count={arche_count} but {len(distinct)} distinct archetypes present", "encounter_budget.archetype_count")

    # Checkpoint rooms are combat-free. Only checkable when the room is provided.
    if room is not None and (room.get("checkpoints") or []) and len(spawns) > 0:
        _err(errors, "ERR_CHECKPOINT_NOT_SAFE",
             "room contains a checkpoint but the encounter places enemies (checkpoint rooms must be combat-free)", "spawns")

    # ---- the corridor decides what may fight in it ------------------------
    # A tight corridor is one where a full jump does not fit, so the player
    # cannot go over anything: combat becomes spacing rather than evasion. That
    # is the point of the height, and it also rules two archetypes out. The
    # Shieldbearer is passed *over or through* — take the hop away and it stops
    # being a choice and becomes a wall only the Titan opens, which is exactly
    # what the class-asymmetry contract forbids. A Ledge Gunner needs a ledge
    # to shoot from, and a tight corridor has no room for one.
    #
    # This used to be deferred to an in-engine check nobody performed. With the
    # standard heights it is arithmetic.
    NEEDS_STANDARD = {"shieldbearer", "ledgegunner"}
    if room is not None:
        for i, s in enumerate(spawns):
            if not isinstance(s, dict):
                continue
            norm = re.sub(r"\s+", "", str(s.get("archetype", ""))).lower()
            pos = s.get("position", {})
            if norm not in NEEDS_STANDARD or not _is_number(pos.get("x")) \
                    or not _is_number(pos.get("z")):
                continue
            clear = rr.clear_above(room, pos["x"], pos["z"])
            if clear < rr.FLOOR - 1e-6:
                _err(errors, "ERR_ARCHETYPE_NEEDS_HEIGHT",
                     f"'{s.get('archetype')}' stands where the ceiling is {clear:g} away, under the "
                     f"{rr.FLOOR:g} of a standard corridor. A jump needs {rr.JUMPING_HEIGHT:g} and "
                     "does not fit, so this enemy cannot be gone over — it becomes a wall rather "
                     "than a choice", f"spawns[{i}]")
    elif has_shieldbearer:
        _err(errors, "WARN_NO_ROOM",
             "Shieldbearer present but no room spec was supplied, so its overhead clearance "
             "could not be checked. Pass --room", "spawns")

    return errors


def validate_text(rec: Dict) -> List[Dict]:
    errors: List[Dict] = []
    if not isinstance(rec, dict):
        return [{"code": "ERR_NOT_OBJECT", "message": "Text record is not a JSON object", "path": ""}]
    en = rec.get("text_en")
    es = rec.get("text_es")
    if not isinstance(en, str) or not en.strip():
        _err(errors, "ERR_FIELD", "text_en must be a non-empty string", "text_en")
    if not isinstance(es, str) or not es.strip():
        _err(errors, "ERR_FIELD", "text_es must be a non-empty string", "text_es")

    errors.extend(_bilingual_errors(en, es))
    return errors


def _bilingual_errors(en: object, es: object, prefix: str = "") -> List[Dict]:
    """The rules every bilingual payload obeys, whatever artifact carries it.

    Shared by lore records and UI strings so the two cannot drift: both are
    author-once-in-both-languages text bound for a String Table.
    """
    errors: List[Dict] = []

    # A region term is also in the banned set, since the term guard reads the same
    # table. Reporting it once, under the code that explains it, beats reporting it
    # twice under one that does not.
    region = {t.lower() for t in ur.load_region_denylist()}
    banned = {t for t in load_banned_and_approved()["banned"] if t.lower() not in region}

    for field, text in ((prefix + "text_en", en), (prefix + "text_es", es)):
        if not isinstance(text, str):
            continue
        leak = ur.region_leak(text)
        if leak:
            _err(errors, "ERR_REGION_LEAK",
                 f"region reference '{leak}' found — the country is never named "
                 f"(source: terminology-guard.md, GDD §1.2)", field)
        certain, ambiguous = ip_term_hits(text, banned)
        for term in certain:
            _err(errors, "ERR_IP_TRADEMARK",
                 f"banned term '{term}' found (source: terminology-guard.md)", field)
        for term in ambiguous:
            _err(errors, "WARN_IP_SENTENCE_INITIAL",
                 f"'{term}' opens a sentence, where the capital is mandatory and so "
                 f"says nothing about whether the placeholder was meant — a human or "
                 f"agent 05 settles this one (source: terminology-guard.md)", field)
        for found in ur.placeholders(text):
            _err(errors, "ERR_PLACEHOLDER",
                 f"placeholder text '{found}' must not ship", field)
        cut = ur.cut_feature_in_text(text)
        if cut:
            _err(errors, "ERR_CUT_FEATURE",
                 f"names the cut feature '{cut[0]}' via '{cut[1]}' — the slice has no "
                 f"such system (source: hud-and-screens.md)", field)

    if isinstance(en, str) and isinstance(es, str) and en:
        if not ur.es_within_budget(en, es):
            _err(errors, "ERR_UI_OVERFLOW",
                 f"text_es ({len(es)} chars) exceeds its allowance of "
                 f"{ur.es_allowance(en)} for a {len(en)}-char text_en "
                 f"(source: ui-budgets.md)", prefix + "text_es")
        if not ur.specifier_parity(en, es):
            diff = ur.specifier_diff(en, es)
            _err(errors, "ERR_SPECIFIER_MISMATCH",
                 f"substitutions differ between languages: missing in es "
                 f"{diff['missing_in_es']}, missing in en {diff['missing_in_en']}",
                 prefix + "text_es")

    return errors


def validate_goap(brain: Dict) -> List[Dict]:
    errors: List[Dict] = []
    if not isinstance(brain, dict):
        return [{"code": "ERR_NOT_OBJECT", "message": "GOAP brain spec is not a JSON object", "path": ""}]
    spec = load_blackboard_spec()

    if not isinstance(brain.get("brain_id"), str) or not brain.get("brain_id"):
        _err(errors, "ERR_FIELD", "brain_id must be a non-empty string", "brain_id")

    # Blackboard keys must match the injected spec EXACTLY (agent 06 mandate):
    # no invented keys, no missing canonical keys.
    bb = brain.get("blackboard_keys")
    if not isinstance(bb, list) or not all(isinstance(k, str) for k in bb or []):
        _err(errors, "ERR_FIELD", "blackboard_keys must be a list of strings", "blackboard_keys")
        bb = []
    declared = set(bb)
    for k in sorted(declared - spec["keys"]):
        _err(errors, "ERR_UNKNOWN_BLACKBOARD_KEY",
             f"'{k}' is not in goap-blackboard-spec.md", "blackboard_keys")
    for k in sorted(spec["keys"] - declared):
        _err(errors, "ERR_MISSING_BLACKBOARD_KEY",
             f"canonical key '{k}' missing (spec must be matched exactly)", "blackboard_keys")

    goap = brain.get("goap")
    if not isinstance(goap, dict):
        _err(errors, "ERR_FIELD", "goap must be an object with goals and actions", "goap")
        goap = {}

    goals = goap.get("goals", []) or []
    if not isinstance(goals, list) or not goals:
        _err(errors, "ERR_FIELD", "goap.goals must be a non-empty list", "goap.goals")
        goals = []
    goal_names = set()
    for i, g in enumerate(goals):
        path = f"goap.goals[{i}]"
        if not isinstance(g, dict):
            _err(errors, "ERR_FIELD", "goal must be an object", path); continue
        name = g.get("name")
        if not isinstance(name, str) or not name:
            _err(errors, "ERR_FIELD", "goal.name must be a non-empty string", path)
        else:
            goal_names.add(name)
            if name not in spec["goals"]:
                _err(errors, "WARN_EXTRA_GOAL",
                     f"'{name}' is not in the canonical goal hierarchy; needs design sign-off", path)
        if not _is_number(g.get("priority_base")):
            _err(errors, "ERR_FIELD", "goal.priority_base must be a number", path)
        if not isinstance(g.get("utility_formula"), str) or not g.get("utility_formula"):
            _err(errors, "ERR_FIELD", "goal.utility_formula must be a non-empty string", path)
    for name in sorted(spec["goals"] - goal_names):
        _err(errors, "ERR_MISSING_GOAL",
             f"canonical goal '{name}' from goap-blackboard-spec.md is not designed", "goap.goals")

    actions = goap.get("actions", []) or []
    if not isinstance(actions, list) or not actions:
        _err(errors, "ERR_FIELD", "goap.actions must be a non-empty list", "goap.actions")
        actions = []
    for i, a in enumerate(actions):
        path = f"goap.actions[{i}]"
        if not isinstance(a, dict):
            _err(errors, "ERR_FIELD", "action must be an object", path); continue
        if not isinstance(a.get("name"), str) or not a.get("name"):
            _err(errors, "ERR_FIELD", "action.name must be a non-empty string", path)
        if not _is_number(a.get("cost")) or a.get("cost") < 0:
            _err(errors, "ERR_FIELD", "action.cost must be a number >= 0", path)
        for field in ("preconditions", "effects"):
            block = a.get(field)
            if not isinstance(block, dict):
                _err(errors, "ERR_FIELD", f"action.{field} must be an object", f"{path}.{field}")
                continue
            # Planner state must live on the shared blackboard — an unknown key
            # here is a condition the runtime solver can never read.
            for k in sorted(set(block) - spec["keys"]):
                _err(errors, "ERR_UNKNOWN_BLACKBOARD_KEY",
                     f"'{k}' is not in goap-blackboard-spec.md", f"{path}.{field}")

    # Dual-output mandate: the slice must be shippable without GOAP.
    fallback = brain.get("scripted_fallback")
    phases = (fallback or {}).get("phases", []) if isinstance(fallback, dict) else []
    if not isinstance(phases, list) or not phases:
        _err(errors, "ERR_MISSING_FALLBACK",
             "scripted_fallback.phases must be a non-empty list (GOAP may be cut)", "scripted_fallback")
    else:
        for i, p in enumerate(phases):
            path = f"scripted_fallback.phases[{i}]"
            if not isinstance(p, dict):
                _err(errors, "ERR_FIELD", "phase must be an object", path); continue
            for field in ("name", "enter_when", "behavior"):
                if not isinstance(p.get(field), str) or not p.get(field):
                    _err(errors, "ERR_FIELD", f"phase.{field} must be a non-empty string", path)

    return errors


def validate_umg(screen: Dict) -> List[Dict]:
    errors: List[Dict] = []
    if not isinstance(screen, dict):
        return [{"code": "ERR_NOT_OBJECT", "message": "UMG spec is not a JSON object", "path": ""}]

    if screen.get("screen_id") not in SCREEN_IDS:
        _err(errors, "ERR_ENUM", f"screen_id must be one of {sorted(SCREEN_IDS)}", "screen_id")

    widgets = screen.get("widgets", []) or []
    if not isinstance(widgets, list) or not widgets:
        _err(errors, "ERR_FIELD", "widgets must be a non-empty list", "widgets")
        widgets = []

    seen_ids = set()
    for i, w in enumerate(widgets):
        path = f"widgets[{i}]"
        if not isinstance(w, dict):
            _err(errors, "ERR_FIELD", "widget must be an object", path); continue
        wid = w.get("id")
        if not isinstance(wid, str) or not wid:
            _err(errors, "ERR_FIELD", "widget.id must be a non-empty string", path)
        elif wid in seen_ids:
            _err(errors, "ERR_DUPLICATE_ID", f"widget id '{wid}' is duplicated", path)
        else:
            seen_ids.add(wid)
        wtype = w.get("type")
        if not isinstance(wtype, str) or not wtype:
            _err(errors, "ERR_FIELD", "widget.type must be a non-empty string", path)
        if not isinstance(w.get("anchor"), str) or not w.get("anchor"):
            _err(errors, "ERR_FIELD", "widget.anchor must be a non-empty string", path)
        pos, size = w.get("position", {}), w.get("size", {})
        if not (isinstance(pos, dict) and _is_number(pos.get("x")) and _is_number(pos.get("y"))):
            _err(errors, "ERR_FIELD", "widget.position needs numeric x, y", path)
        if not (isinstance(size, dict) and _is_number(size.get("w")) and _is_number(size.get("h"))
                and size.get("w") > 0 and size.get("h") > 0):
            _err(errors, "ERR_FIELD", "widget.size needs numeric w, h > 0", path)

        # Localization seam: every text widget goes through a StringTable ID, and
        # nothing else carries one. The old wording made the key optional on text
        # widgets, which permitted a text widget with no key — a hardcoded string
        # in everything but name.
        key = w.get("string_table_key")
        is_text = isinstance(wtype, str) and "text" in wtype.lower()
        if is_text:
            if not isinstance(key, str) or not STRING_TABLE_KEY_RE.match(key):
                _err(errors, "ERR_HARDCODED_STRING",
                     "text widget must set string_table_key as 'ST_<Table>.<Key>' (never a hardcoded string)", path)
        elif key not in (None, ""):
            _err(errors, "ERR_KEY_ON_NON_TEXT",
                 f"non-text widget carries string_table_key '{key}'; a binding carries "
                 f"live state, a key carries authored words (source: uispec.md)", path)

        # The cut-feature denylist, parsed from hud-and-screens.md. Every identifier
        # field is searched, because a boss bar named `bar_progress_02` is still a
        # boss bar and the binding is where it gives itself away.
        cut = ur.cut_feature_in_identifiers(
            w.get("id"), wtype, w.get("binding"), key)
        if cut:
            _err(errors, "ERR_CUT_FEATURE",
                 f"widget matches the cut feature '{cut[0]}' via '{cut[1]}' "
                 f"(source: hud-and-screens.md)", path)

    return errors


# --------------------------------------------------------------------------
# Strings — the copy half of a screen (vault/07-ui-and-controls/uispec.md)
# --------------------------------------------------------------------------
_CORPUS_ADDRESSES = None


def _corpus_addresses() -> set:
    """Every `path#heading` the retriever can return, built once per process.

    Imported lazily so the room and encounter paths never pay for it.
    """
    global _CORPUS_ADDRESSES
    if _CORPUS_ADDRESSES is None:
        import retriever
        _CORPUS_ADDRESSES = {chunk["source"] for chunk in retriever.build_corpus()}
        if not _CORPUS_ADDRESSES:
            sys.exit("❌ Empty retrieval corpus; refusing to accept unverifiable provenance.")
    return _CORPUS_ADDRESSES



def validate_strings(table: Dict, umg_specs: Optional[List[Dict]] = None) -> List[Dict]:
    """The StringTable artifact, and optionally its cross-reference to the layouts.

    Without `umg_specs` this checks everything a table can be judged on alone.
    With them it also runs the cross-reference, which is the integration
    checkpoint: neither artifact can see a dangling key or an orphan record by
    itself.
    """
    errors: List[Dict] = []
    if not isinstance(table, dict):
        return [{"code": "ERR_NOT_OBJECT", "message": "String table is not a JSON object", "path": ""}]

    if table.get("table") not in ur.STRING_TABLES:
        _err(errors, "ERR_ENUM", f"table must be one of {sorted(ur.STRING_TABLES)}", "table")

    records = table.get("records", []) or []
    if not isinstance(records, list) or not records:
        _err(errors, "ERR_FIELD", "records must be a non-empty list", "records")
        records = []

    seen_keys = set()
    for i, rec in enumerate(records):
        path = f"records[{i}]"
        if not isinstance(rec, dict):
            _err(errors, "ERR_FIELD", "record must be an object", path)
            continue

        key = rec.get("key")
        if not isinstance(key, str) or not ur.KEY_RE.match(key or ""):
            _err(errors, "ERR_FIELD", "key must match 'ST_<Table>.<Key>'", f"{path}.key")
        elif key in seen_keys:
            _err(errors, "ERR_DUPLICATE_ID", f"key '{key}' is defined twice", f"{path}.key")
        else:
            seen_keys.add(key)
            if isinstance(table.get("table"), str) and not key.startswith(table["table"] + "."):
                _err(errors, "ERR_FIELD",
                     f"key '{key}' does not belong to table '{table['table']}' — a key never "
                     f"crosses tables (source: uispec.md)", f"{path}.key")

        screens = rec.get("screens")
        if not isinstance(screens, list) or not screens:
            _err(errors, "ERR_FIELD", "screens must be a non-empty list", f"{path}.screens")
        else:
            for screen in screens:
                if screen not in ur.SCREEN_IDS:
                    _err(errors, "ERR_ENUM",
                         f"screen '{screen}' must be one of {sorted(ur.SCREEN_IDS)}",
                         f"{path}.screens")

        wclass = rec.get("widget_class")
        if ur.cap_for(wclass) is None:
            _err(errors, "ERR_ENUM",
                 f"widget_class must be one of {sorted(ur.WIDGET_CLASS_CAPS)}",
                 f"{path}.widget_class")

        chunks = rec.get("source_chunks")
        if not isinstance(chunks, list) or not chunks or not all(
                isinstance(c, str) and c.strip() for c in chunks):
            _err(errors, "ERR_UNSOURCED",
                 "source_chunks must be a non-empty list of 'path#heading' strings — "
                 "no new copy without a source (source: uispec.md)", f"{path}.source_chunks")
        else:
            # A citation nobody checks is a formality. Requiring the field to be
            # non-empty only proves the writer typed something; resolving it against
            # the corpus proves the address exists and is the one retrieval returns.
            for cited in chunks:
                if cited not in _corpus_addresses():
                    _err(errors, "ERR_UNRESOLVED_SOURCE",
                         f"cited chunk '{cited}' does not exist in the retrieval corpus — "
                         f"provenance must resolve, not merely be present",
                         f"{path}.source_chunks")

        en, es = rec.get("text_en"), rec.get("text_es")
        for field, text in (("text_en", en), ("text_es", es)):
            if not isinstance(text, str) or not text.strip():
                _err(errors, "ERR_FIELD", f"{field} must be a non-empty string", f"{path}.{field}")
                continue
            cap = ur.over_cap(wclass, text)
            if cap is not None:
                _err(errors, "ERR_OVER_CAP",
                     f"{len(text)} chars exceeds the {wclass} cap of {cap} "
                     f"(source: ui-budgets.md)", f"{path}.{field}")
            for glyph in ur.glyph_literals(text):
                _err(errors, "ERR_GLYPH_LITERAL",
                     f"'{glyph}' names a button; input remap is in scope, so prompts carry "
                     f"an action token such as <Interact> (source: ui-budgets.md)",
                     f"{path}.{field}")

        errors.extend(_bilingual_errors(en, es, prefix=f"{path}."))

    # --- Set-level: a table fails as a set even when every record passes alone --
    for text, keys in sorted(ur.duplicate_texts(records).items()):
        _err(errors, "ERR_DUPLICATE_TEXT",
             f"{keys} all say '{text}' — either a key is redundant, or a distinction "
             f"was meant and got lost (source: ui-budgets.md)", "records")

    for screen, count in sorted(ur.screens_over_key_cap(records).items()):
        _err(errors, "ERR_KEY_BUDGET",
             f"{screen} defines {count} keys, over the cap of {ur.MAX_KEYS_PER_SCREEN} "
             f"(source: ui-budgets.md)", "records")

    approved = load_banned_and_approved()["approved"]
    for term, surfaces in sorted(ur.term_variants(records, approved).items()):
        _err(errors, "WARN_TERM_VARIANT",
             f"'{term}' appears as {sorted(surfaces)} — one concept, one name "
             f"(source: terminology-guard.md)", "records")

    # --- Cross-reference: the integration checkpoint ---------------------------
    if umg_specs:
        dangling, orphan = ur.cross_reference(umg_specs, records)
        for key in sorted(dangling):
            _err(errors, "ERR_DANGLING_KEY",
                 f"a widget references '{key}' and no record defines it — an empty "
                 f"widget would ship", "records")
        for key in sorted(orphan):
            _err(errors, "ERR_ORPHAN_STRING",
                 f"'{key}' is defined and no widget shows it — work nobody sees", "records")

    return errors


def validate_feel(table: Dict) -> List[Dict]:
    errors: List[Dict] = []
    if not isinstance(table, dict):
        return [{"code": "ERR_NOT_OBJECT", "message": "Feel table is not a JSON object", "path": ""}]

    if table.get("table") != "DT_PlayerFeel":
        _err(errors, "ERR_FIELD", "table must be 'DT_PlayerFeel'", "table")

    rows = table.get("rows", []) or []
    if not isinstance(rows, list) or not rows:
        _err(errors, "ERR_FIELD", "rows must be a non-empty list", "rows")
        rows = []

    seen_classes = []
    for i, r in enumerate(rows):
        path = f"rows[{i}]"
        if not isinstance(r, dict):
            _err(errors, "ERR_FIELD", "row must be an object", path); continue

        for field, allowed in FEEL_ENUMS.items():
            if r.get(field) not in allowed:
                _err(errors, "ERR_ENUM", f"{field} must be one of {sorted(allowed)}", f"{path}.{field}")

        cls = r.get("class")
        if cls in CLASS_CONTRACT:
            seen_classes.append(cls)
            for field, expected in CLASS_CONTRACT[cls].items():
                if r.get(field) is not None and r.get(field) != expected:
                    _err(errors, "ERR_CLASS_CONTRACT",
                         f"{cls} must have {field}='{expected}' (source: class-asymmetry-contract.md)",
                         f"{path}.{field}")

        for field in ("vertical_reach_u", "coyote_time_ms", "jump_buffer_ms", "variable_jump_min_pct",
                      "dodge_total_ms", "dodge_iframe_ms", "landing_lag_ms", "traversal_range_u"):
            if not _is_number(r.get(field)):
                _err(errors, "ERR_FIELD", f"{field} must be a number", f"{path}.{field}")

        # Playable-bounds guardrails (constants above; the QA sweep tunes inside them).
        checks = (
            ("vertical_reach_u",      lambda v: v > 0,                                    "must be > 0"),
            ("traversal_range_u",     lambda v: v > 0,                                    "must be > 0"),
            ("coyote_time_ms",        lambda v: 0 <= v <= COYOTE_MAX_MS,                  f"must be in [0,{COYOTE_MAX_MS}]"),
            ("jump_buffer_ms",        lambda v: 0 <= v <= JUMP_BUFFER_MAX_MS,             f"must be in [0,{JUMP_BUFFER_MAX_MS}]"),
            ("variable_jump_min_pct", lambda v: 0 < v <= 100,                             "must be in (0,100]"),
            ("dodge_total_ms",        lambda v: DODGE_TOTAL_MIN_MS <= v <= DODGE_TOTAL_MAX_MS,
                                                                                          f"must be in [{DODGE_TOTAL_MIN_MS},{DODGE_TOTAL_MAX_MS}]"),
            ("landing_lag_ms",        lambda v: 0 <= v <= LANDING_LAG_MAX_MS,             f"must be in [0,{LANDING_LAG_MAX_MS}]"),
        )
        for field, ok, msg in checks:
            v = r.get(field)
            if _is_number(v) and not ok(v):
                _err(errors, "ERR_FEEL_BOUNDS", f"{field} {msg}", f"{path}.{field}")

        # An i-frame window longer than the dodge itself is a physical impossibility.
        total, iframe = r.get("dodge_total_ms"), r.get("dodge_iframe_ms")
        if _is_number(total) and _is_number(iframe) and not (0 < iframe < total):
            _err(errors, "ERR_IFRAME_EXCEEDS_DODGE",
                 f"dodge_iframe_ms={iframe} must be > 0 and < dodge_total_ms={total}", f"{path}.dodge_iframe_ms")

        pct = r.get("variable_jump_min_pct")
        if _is_number(pct) and 0 < pct < 1:
            _err(errors, "WARN_UNIT_AMBIGUOUS",
                 f"variable_jump_min_pct={pct} looks like a fraction; the schema expects percent (~40)",
                 f"{path}.variable_jump_min_pct")

        if r.get("cancel_priority") == "fire":
            _err(errors, "WARN_CANCEL_PRIORITY",
                 "cancel_priority deviates from the vault default (defense has priority); needs design sign-off",
                 f"{path}.cancel_priority")

    # Exactly one row per class, both classes present.
    for cls in ("Hunter", "Titan"):
        n = seen_classes.count(cls)
        if n == 0:
            _err(errors, "ERR_CLASS_ROWS", f"missing row for class '{cls}'", "rows")
        elif n > 1:
            _err(errors, "ERR_CLASS_ROWS", f"class '{cls}' appears {n} times (expected 1)", "rows")

    return errors


VALIDATORS = {"room": validate_room, "rooms": validate_room_batch, "encounter": validate_encounter, "text": validate_text,
              "goap": validate_goap, "umg": validate_umg, "feel": validate_feel,
              "strings": validate_strings}


def rules_fingerprint() -> str:
    """One hash over the rule set a verdict was produced by.

    A provenance record that stores only the artifact's hash binds what was
    judged but not the law it was judged under. A room approved in August
    against August's rules walked straight through September's importer while
    failing September's gate with eight softlocks — the record said PASS because
    PASS had been true once. Stamping the rules alongside the artifact lets the
    importer notice that the verdict it is trusting no longer has a gate behind
    it.

    The fingerprint covers this file and the geometry it delegates to; changing
    either is changing the law.
    """
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(rr.__file__)):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Echoes deterministic content validator")
    parser.add_argument("--kind", required=True, choices=sorted(VALIDATORS), help="Spec type to validate")
    parser.add_argument("--file", help="Path to the JSON file (reads stdin if omitted)")
    parser.add_argument("--room", help="For --kind encounter: room spec JSON for cross-checks")
    parser.add_argument("--umg", action="append", metavar="SCREEN",
                        help="For --kind strings: a UMGSpec JSON to cross-reference. "
                             "Repeatable; pass every screen the table serves")
    args = parser.parse_args()

    raw = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        report = {"kind": args.kind, "status": "FAIL",
                  "errors": [{"code": "ERR_INVALID_JSON", "message": str(e), "path": ""}]}
        print(json.dumps(report, indent=2, ensure_ascii=False))
        sys.exit(1)

    if args.kind == "encounter":
        room = None
        if args.room:
            room = json.loads(Path(args.room).read_text(encoding="utf-8"))
        errors = validate_encounter(payload, room)
    elif args.kind == "strings":
        screens = [json.loads(Path(p).read_text(encoding="utf-8")) for p in (args.umg or [])]
        errors = validate_strings(payload, screens or None)
    else:
        errors = VALIDATORS[args.kind](payload)

    hard = [e for e in errors if e["code"].startswith("ERR_")]
    warns = [e for e in errors if not e["code"].startswith("ERR_")]
    report = {"kind": args.kind, "status": "PASS" if not hard else "FAIL",
              "rules_sha256": rules_fingerprint(),
              "error_count": len(hard), "warning_count": len(warns), "errors": errors}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
