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
  - Numeric thresholds (room budgets, enemy budgets, overflow ratio) are named
    constants below, each annotated with its vault source note. They change
    rarely; if the vault numbers change, update them here (a future improvement
    is to move these into one machine-readable rules file the vault prose cites).

Usage:
  python3 agents/validators.py --kind room     --file room.json
  python3 agents/validators.py --kind encounter --file enc.json  [--room room.json]
  python3 agents/validators.py --kind text     --file lore.json
  python3 agents/validators.py --kind goap     --file brain.json
  python3 agents/validators.py --kind umg      --file screen.json
  python3 agents/validators.py --kind feel     --file feel.json
  cat lore.json | python3 agents/validators.py --kind text

Exit code 0 = PASS (no errors), 1 = FAIL. A JSON report is printed to stdout.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
VAULT_DIR = BASE_DIR / "vault"

# --- Numeric thresholds (each cites its vault source note) ------------------
# vault/04-world/room-constraints.md
WIDTH_MIN, WIDTH_MAX = 2000, 6000
HEIGHT_MIN, HEIGHT_MAX = 1000, 3000
# vault/02-enemies/enemy-palette-overview.md
ENEMY_MIN, ENEMY_MAX = 2, 5          # a combat room holds 2..5 enemies (0 = safe room)
MAX_ARCHETYPES = 2
# vault/05-lore/bilingual-string-tables.md
ES_OVERFLOW_RATIO = 1.30             # len(text_es) must not exceed len(text_en) * 1.30

# --- Enums (from the room/encounter schemas) --------------------------------
SEGMENTS = {"SegmentA_Shared", "SegmentB_Hunter", "SegmentB_Titan", "Convergence"}
GATE_TOOLS = {"None", "Grapple", "Bash", "Keycard"}
FACINGS = {"Left", "Right"}
# A class-exclusive branch must never require the opposite class's tool.
FORBIDDEN_GATE_BY_SEGMENT = {"SegmentB_Hunter": "Bash", "SegmentB_Titan": "Grapple"}

# --- UMG spec (agent 07 schema + vault/07-ui-and-controls/hud-and-screens.md) --
SCREEN_IDS = {"HUD_Main", "Screen_ClassSelect", "Screen_RunComplete", "Screen_Pause"}
STRING_TABLE_KEY_RE = re.compile(r"^ST_\w+\.\w+$")   # e.g. ST_UI.Key_Name
# Excluded HUD elements ("NO boss health bar / minimap / ammo counters / damage
# numbers"). Matched as substrings of normalized widget id/type/binding/key.
EXCLUDED_HUD_PATTERNS = {"bossbar", "bosshealth", "minimap", "ammocount", "damagenumber"}

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
    errors: List[Dict] = []
    if not isinstance(room, dict):
        return [{"code": "ERR_NOT_OBJECT", "message": "Room spec is not a JSON object", "path": ""}]

    if not isinstance(room.get("room_id"), str) or not room.get("room_id"):
        _err(errors, "ERR_FIELD", "room_id must be a non-empty string", "room_id")

    segment = room.get("segment")
    if segment not in SEGMENTS:
        _err(errors, "ERR_ENUM", f"segment must be one of {sorted(SEGMENTS)}", "segment")

    dims = room.get("dimensions", {})
    w, h = dims.get("width"), dims.get("height")
    if not _is_number(w) or not (WIDTH_MIN <= w <= WIDTH_MAX):
        _err(errors, "ERR_ROOM_BUDGET", f"width must be a number in [{WIDTH_MIN},{WIDTH_MAX}]", "dimensions.width")
    if not _is_number(h) or not (HEIGHT_MIN <= h <= HEIGHT_MAX):
        _err(errors, "ERR_ROOM_BUDGET", f"height must be a number in [{HEIGHT_MIN},{HEIGHT_MAX}]", "dimensions.height")

    cb = room.get("camera_bounds", {})
    bounds_ok = all(_is_number(cb.get(k)) for k in ("min_x", "max_x", "min_z", "max_z"))
    if not bounds_ok:
        _err(errors, "ERR_FIELD", "camera_bounds must have numeric min_x/max_x/min_z/max_z", "camera_bounds")
    elif not (cb["min_x"] < cb["max_x"] and cb["min_z"] < cb["max_z"]):
        _err(errors, "ERR_CAMERA_BOUNDS", "camera_bounds min must be < max on both axes", "camera_bounds")

    def _in_bounds(x, z) -> bool:
        if not bounds_ok:
            return True  # already reported
        return cb["min_x"] <= x <= cb["max_x"] and cb["min_z"] <= z <= cb["max_z"]

    for i, p in enumerate(room.get("platforms", []) or []):
        path = f"platforms[{i}]"
        if not isinstance(p, dict):
            _err(errors, "ERR_FIELD", "platform must be an object", path); continue
        if not _is_number(p.get("x")) or not _is_number(p.get("z")) or not _is_number(p.get("width")):
            _err(errors, "ERR_FIELD", "platform needs numeric x, z, width", path)
        if not isinstance(p.get("is_one_way"), bool):
            _err(errors, "ERR_FIELD", "platform.is_one_way must be boolean", path)
        if _is_number(p.get("x")) and _is_number(p.get("z")) and not _in_bounds(p["x"], p["z"]):
            _err(errors, "ERR_OUT_OF_BOUNDS", "platform outside camera_bounds", path)

    for i, g in enumerate(room.get("gates", []) or []):
        path = f"gates[{i}]"
        if not isinstance(g, dict):
            _err(errors, "ERR_FIELD", "gate must be an object", path); continue
        tool = g.get("required_tool")
        if tool not in GATE_TOOLS:
            _err(errors, "ERR_ENUM", f"required_tool must be one of {sorted(GATE_TOOLS)}", path)
        # Anti-softlock isolation: no opposite-class tool in a class-exclusive branch.
        forbidden = FORBIDDEN_GATE_BY_SEGMENT.get(segment)
        if forbidden and tool == forbidden:
            _err(errors, "ERR_CLASS_CROSS_CONTAMINATION",
                 f"{segment} must not contain a '{forbidden}' gate (opposite class)", path)
        if _is_number(g.get("x")) and _is_number(g.get("z")) and not _in_bounds(g["x"], g["z"]):
            _err(errors, "ERR_OUT_OF_BOUNDS", "gate outside camera_bounds", path)

    for i, c in enumerate(room.get("checkpoints", []) or []):
        path = f"checkpoints[{i}]"
        if not isinstance(c, dict) or not _is_number(c.get("x")) or not _is_number(c.get("z")):
            _err(errors, "ERR_FIELD", "checkpoint needs numeric x, z", path); continue
        if not _in_bounds(c["x"], c["z"]):
            _err(errors, "ERR_OUT_OF_BOUNDS", "checkpoint outside camera_bounds", path)

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

    # Shieldbearer clearance (300u vertical / 400u runway) is geometry-dependent
    # and cannot be verified precisely from coordinates alone.
    if has_shieldbearer:
        _err(errors, "WARN_NEEDS_INENGINE",
             "Shieldbearer present: 300u overhead / 400u runway clearance must be confirmed in-engine", "spawns")

    return errors


def validate_text(rec: Dict) -> List[Dict]:
    errors: List[Dict] = []
    if not isinstance(rec, dict):
        return [{"code": "ERR_NOT_OBJECT", "message": "Text record is not a JSON object", "path": ""}]
    terms = load_banned_and_approved()
    banned = terms["banned"]

    en = rec.get("text_en")
    es = rec.get("text_es")
    if not isinstance(en, str) or not en.strip():
        _err(errors, "ERR_FIELD", "text_en must be a non-empty string", "text_en")
    if not isinstance(es, str) or not es.strip():
        _err(errors, "ERR_FIELD", "text_es must be a non-empty string", "text_es")

    for field, text in (("text_en", en), ("text_es", es)):
        if not isinstance(text, str):
            continue
        for term in banned:
            if re.search(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE):
                _err(errors, "ERR_IP_TRADEMARK",
                     f"banned term '{term}' found (source: terminology-guard.md)", field)

    if isinstance(en, str) and isinstance(es, str) and len(en) > 0:
        if len(es) > len(en) * ES_OVERFLOW_RATIO:
            _err(errors, "ERR_UI_OVERFLOW",
                 f"text_es ({len(es)}) exceeds text_en ({len(en)}) by >{int((ES_OVERFLOW_RATIO-1)*100)}%", "text_es")

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

        # Localization seam: every text widget goes through a StringTable ID.
        if isinstance(wtype, str) and "text" in wtype.lower():
            key = w.get("string_table_key")
            if not isinstance(key, str) or not STRING_TABLE_KEY_RE.match(key):
                _err(errors, "ERR_HARDCODED_STRING",
                     "text widget must set string_table_key as 'ST_<Table>.<Key>' (never a hardcoded string)", path)

        # Excluded-elements list from hud-and-screens.md.
        haystack = "".join(
            str(w.get(f, "")) for f in ("id", "type", "binding", "string_table_key")
        ).lower().replace("_", "").replace(" ", "")
        for pattern in sorted(EXCLUDED_HUD_PATTERNS):
            if pattern in haystack:
                _err(errors, "ERR_EXCLUDED_HUD_ELEMENT",
                     f"widget matches excluded HUD element '{pattern}' (source: hud-and-screens.md)", path)

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


VALIDATORS = {"room": validate_room, "encounter": validate_encounter, "text": validate_text,
              "goap": validate_goap, "umg": validate_umg, "feel": validate_feel}


def main():
    parser = argparse.ArgumentParser(description="Echoes deterministic content validator")
    parser.add_argument("--kind", required=True, choices=sorted(VALIDATORS), help="Spec type to validate")
    parser.add_argument("--file", help="Path to the JSON file (reads stdin if omitted)")
    parser.add_argument("--room", help="For --kind encounter: room spec JSON for cross-checks")
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
    else:
        errors = VALIDATORS[args.kind](payload)

    hard = [e for e in errors if e["code"].startswith("ERR_")]
    warns = [e for e in errors if not e["code"].startswith("ERR_")]
    report = {"kind": args.kind, "status": "PASS" if not hard else "FAIL",
              "error_count": len(hard), "warning_count": len(warns), "errors": errors}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
