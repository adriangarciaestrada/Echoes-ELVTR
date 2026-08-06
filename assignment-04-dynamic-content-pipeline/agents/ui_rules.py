#!/usr/bin/env python3
"""UI copy and layout rules. Pure functions plus vault-sourced lists.

The countable half of the UI contract (`vault/07-ui-and-controls/uispec.md`).
Everything here answers a question a language model answers worse and more
expensively: does this string fit its widget, do the two languages agree about
their substitutions, is this key referenced by anything, does this table say the
same thing twice.

Two kinds of rule data, handled two ways on purpose:

**Numbers are constants here**, sourced from
`vault/07-ui-and-controls/ui-budgets.md` and cited line by line.
`test_ui_rules.py` parses that note and fails if any constant disagrees with it,
so the note stays the source of truth without this module depending on markdown
tables surviving a rewrite. Drift is caught by the test rather than in production.

**Lists are parsed live** from the vault, because a denylist that grows is a
denylist someone will extend by editing the note and nothing else. A parse that
comes back empty is treated as a broken guard and fails loud rather than passing
everything.
"""

import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
VAULT_DIR = BASE_DIR / "vault"

# --- Budgets, from vault/07-ui-and-controls/ui-budgets.md -------------------
ES_OVERFLOW_RATIO = 1.30    # top of the 15-30% industry expansion range
ES_OVERFLOW_FLOOR = 6       # characters [TUNE]; governs below len(en) == 20

WIDGET_CLASS_CAPS = {       # characters, applied to each language [TUNE]
    "Prompt": 24,
    "MenuLabel": 20,
    "OptionValue": 16,
    "OptionDescription": 80,
    "ClassName": 16,
    "ClassTagline": 48,
    "StatLabel": 20,
    "ProseBlock": 240,
}

MAX_KEYS_PER_SCREEN = 14    # [TUNE]
TITLE_SAFE = 0.90           # [VERIFY] against UE's own safe-zone settings
ACTION_SAFE = 0.95          # [VERIFY]

# --- Contract shapes, from vault/07-ui-and-controls/uispec.md ---------------
SCREEN_IDS = {"HUD_Main", "Screen_ClassSelect", "Screen_RunComplete", "Screen_Pause"}
STRING_TABLES = {"ST_UI", "ST_Lore"}
KEY_RE = re.compile(r"^ST_\w+\.\w+$")

# A substitution the runtime fills in: an index, a printf verb, or an action
# token. Action tokens are deliberately in this set — a prompt that loses its
# <Interact> in one language is the same bug as one that loses its {0}.
SPECIFIER_RE = re.compile(r"\{\d+\}|%[sd]|<[A-Za-z]\w*>")

# A hardcoded button glyph. Input remap is in scope, so a string naming a button
# is a lie the moment a player rebinds it: prompts carry action tokens instead.
GLYPH_LITERAL_RE = re.compile(
    r"\[[A-Za-z0-9]{1,3}\]"                                   # [X], [LB], [A]
    r"|\b(?:press|hold|pulsa|pulse|mantén|manten)\s+[A-Z0-9]\b",  # "press A"
    re.IGNORECASE,
)

PLACEHOLDER_RE = re.compile(
    r"\b(lorem|ipsum|todo|tbd|tbc|xxx+|placeholder|marcador)\b", re.IGNORECASE
)


# --------------------------------------------------------------------------
# Spanish overflow
# --------------------------------------------------------------------------
def es_allowance(text_en: str) -> int:
    """Characters Spanish may use for this English string.

    The ratio alone rejects correct translations of short strings, which is what
    a menu is made of: Resume/Continuar fails a flat 1.30. The absolute floor
    admits them. The two terms cross at 20 characters, so the floor governs
    buttons and the ratio governs prose.
    """
    return int(max(len(text_en) * ES_OVERFLOW_RATIO, len(text_en) + ES_OVERFLOW_FLOOR))


def es_within_budget(text_en: str, text_es: str) -> bool:
    return len(text_es) <= es_allowance(text_en)


# --------------------------------------------------------------------------
# Per-class caps
# --------------------------------------------------------------------------
def cap_for(widget_class: str) -> Optional[int]:
    return WIDGET_CLASS_CAPS.get(widget_class)


def over_cap(widget_class: str, text: str) -> Optional[int]:
    """Returns the cap that `text` exceeds, or None if it fits (or is unknown)."""
    cap = cap_for(widget_class)
    if cap is None or len(text) <= cap:
        return None
    return cap


# --------------------------------------------------------------------------
# Substitutions
# --------------------------------------------------------------------------
def specifiers(text: str) -> Counter:
    return Counter(SPECIFIER_RE.findall(text or ""))


def specifier_parity(text_en: str, text_es: str) -> bool:
    """Order may differ — Spanish reorders legitimately. Count and identity may not."""
    return specifiers(text_en) == specifiers(text_es)


def specifier_diff(text_en: str, text_es: str) -> Dict[str, List[str]]:
    en, es = specifiers(text_en), specifiers(text_es)
    return {
        "missing_in_es": sorted((en - es).elements()),
        "missing_in_en": sorted((es - en).elements()),
    }


def glyph_literals(text: str) -> List[str]:
    return [m.group(0) for m in GLYPH_LITERAL_RE.finditer(text or "")]


def placeholders(text: str) -> List[str]:
    return [m.group(0) for m in PLACEHOLDER_RE.finditer(text or "")]


# --------------------------------------------------------------------------
# Vault-sourced lists (parsed live so they never drift from the design)
# --------------------------------------------------------------------------
def _table_rows(note: Path, heading: str) -> List[List[str]]:
    """Markdown table rows under `heading`, as lists of stripped cells.

    Stops at the next heading of the same or higher level, so a note may hold
    several tables without them bleeding into each other.
    """
    if not note.exists():
        sys.exit(f"❌ Missing source of truth: {note}")
    rows: List[List[str]] = []
    depth = None
    inside = False
    for line in note.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped.lstrip("#").strip().lower()
            if title == heading.lower():
                inside, depth = True, level
                continue
            if inside and depth is not None and level <= depth:
                break
            continue
        if not inside or not stripped.startswith("|"):
            continue
        cells = [re.sub(r"[*_`]", "", c).strip() for c in stripped.strip("|").split("|")]
        if not cells or set("".join(cells)) <= {"-", ":", " "}:
            continue        # separator row
        rows.append(cells)
    return rows


def load_cut_features() -> Dict[str, List[str]]:
    """Cut features and their match tokens, from hud-and-screens.md.

    Returns {feature name: [token, ...]} with tokens lowercased. Fails loud on an
    empty parse: a denylist that silently becomes empty passes everything.
    """
    note = VAULT_DIR / "07-ui-and-controls" / "hud-and-screens.md"
    features: Dict[str, List[str]] = {}
    for cells in _table_rows(note, "Cut Features — Denylist"):
        if len(cells) < 2 or "match token" in cells[1].lower():
            continue        # header row
        tokens = [t.strip().lower() for t in cells[1].split(",") if t.strip()]
        if tokens:
            features[cells[0]] = tokens
    if not features:
        sys.exit(f"❌ Parsed zero cut features from {note}; refusing to run a no-op guard.")
    return features


def load_region_denylist() -> List[str]:
    """Banned region references, from terminology-guard.md.

    The same table is picked up by the term guard in validators.py, so these bind
    lore as well as interface text — the country is never named anywhere.
    """
    note = VAULT_DIR / "00-core" / "terminology-guard.md"
    terms: List[str] = []
    for cells in _table_rows(note, "Banned Region References"):
        if not cells or "banned region" in cells[0].lower():
            continue        # header row
        for token in cells[0].split("/"):
            t = re.sub(r"\[TUNE\]", "", token).strip()
            if t:
                terms.append(t)
    if not terms:
        sys.exit(f"❌ Parsed zero region terms from {note}; refusing to run a no-op guard.")
    return terms


def _normalise_ident(*fields: object) -> str:
    joined = "".join(str(f or "") for f in fields).lower()
    return re.sub(r"[\s_\-.]", "", joined)


def cut_feature_in_identifiers(*fields: object) -> Optional[Tuple[str, str]]:
    """(feature, token) if any identifier field names a cut feature."""
    haystack = _normalise_ident(*fields)
    for feature, tokens in sorted(load_cut_features().items()):
        for token in tokens:
            if re.sub(r"[\s_\-.]", "", token) in haystack:
                return feature, token
    return None


def _word_pattern(term: str) -> str:
    """Word-boundary match tolerating a plural suffix in either language.

    Without it a denylist is trivially evaded by pluralising: `\\bMayan\\b` does not
    match "Mayans", and `\\bpirámide\\b` does not match "pirámides". Optional `s`
    and `es` cover both languages; the leading boundary still keeps "maya" out of
    "mayhem".
    """
    return r"\b" + re.escape(term) + r"(?:e?s)?\b"


def cut_feature_in_text(text: str) -> Optional[Tuple[str, str]]:
    """(feature, token) if prose names a cut feature. Word boundaries, both languages."""
    if not text:
        return None
    for feature, tokens in sorted(load_cut_features().items()):
        for token in tokens:
            if re.search(_word_pattern(token), text, re.IGNORECASE):
                return feature, token
    return None


def region_leak(text: str) -> Optional[str]:
    if not text:
        return None
    for term in load_region_denylist():
        if re.search(_word_pattern(term), text, re.IGNORECASE):
            return term
    return None


# --------------------------------------------------------------------------
# Set-level rules
#
# The inverse of the room batch rules. A set of rooms fails by being too
# similar; a set of strings fails by being inconsistent. Same mechanism,
# opposite sign — see ui-constraints.md.
# --------------------------------------------------------------------------
def duplicate_texts(records: Sequence[Dict]) -> Dict[str, List[str]]:
    """{text: [key, ...]} for any English text used by more than one key.

    Either a key is redundant, or a distinction was meant and got lost. A string
    shared between screens is one key referenced twice.
    """
    by_text: Dict[str, List[str]] = {}
    for rec in records:
        text = (rec.get("text_en") or "").strip().lower()
        if text:
            by_text.setdefault(text, []).append(rec.get("key", ""))
    return {t: sorted(keys) for t, keys in by_text.items() if len(keys) > 1}


def keys_per_screen(records: Sequence[Dict]) -> Counter:
    counts: Counter = Counter()
    for rec in records:
        for screen in rec.get("screens", []) or []:
            counts[screen] += 1
    return counts


def screens_over_key_cap(records: Sequence[Dict]) -> Dict[str, int]:
    return {s: n for s, n in keys_per_screen(records).items() if n > MAX_KEYS_PER_SCREEN}


def term_variants(records: Sequence[Dict], approved: Iterable[str]) -> Dict[str, Set[str]]:
    """{canonical term: {surface forms found}} where a term is spelled inconsistently.

    One concept, one name. A Beacon is a Beacon on every screen.
    """
    found: Dict[str, Set[str]] = {}
    texts = [t for rec in records for t in (rec.get("text_en"), rec.get("text_es")) if t]
    for term in approved:
        if not term or len(term) < 3:
            continue
        surfaces = set()
        for text in texts:
            for match in re.finditer(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE):
                surfaces.add(match.group(0))
        if len(surfaces) > 1:
            found[term] = surfaces
    return found


# --------------------------------------------------------------------------
# The cross-reference: the integration checkpoint between the two artifacts
# --------------------------------------------------------------------------
def referenced_keys(umg_specs: Iterable[Dict]) -> Set[str]:
    keys = set()
    for spec in umg_specs:
        for widget in spec.get("widgets", []) or []:
            key = widget.get("string_table_key")
            if isinstance(key, str) and key:
                keys.add(key)
    return keys


def defined_keys(records: Iterable[Dict]) -> Set[str]:
    return {r["key"] for r in records if isinstance(r.get("key"), str) and r["key"]}


def cross_reference(umg_specs: Iterable[Dict], records: Iterable[Dict]) -> Tuple[Set[str], Set[str]]:
    """(dangling, orphan).

    Dangling: a widget references a key nothing defines — an empty widget ships.
    Orphan: a record no widget references — work nobody sees.

    Neither is visible while checking one artifact alone, which is why this lives
    here and not in either validator.
    """
    referenced = referenced_keys(umg_specs)
    defined = defined_keys(records)
    return referenced - defined, defined - referenced
