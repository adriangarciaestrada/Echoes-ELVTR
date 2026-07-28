#!/usr/bin/env python3
"""
Echoes — Deterministic Content Validator (validators.py)

The hard gate of the generate-then-judge pipeline. Generator agents (Level
Designer, Encounter Designer, Lore Scribe, UI Designer) emit JSON; this module
enforces the countable rules deterministically in Python BEFORE anything reaches
the Unreal DataTable seam. The LLM reviewers (03 Room Reviewer, 05 Style Guard)
are the semantic second layer on top of this — they do not replace it.

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


VALIDATORS = {"room": validate_room, "encounter": validate_encounter, "text": validate_text}


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
