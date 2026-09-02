#!/usr/bin/env python3
"""Deterministic gate for a bilingual UI string record. No model involved.

Checks, in order: non-empty in both languages, per-language character cap
(`ui-and-strings.md`'s widget-class table), placeholder parity (a `{name}`
token in one language must appear in the other, or it silently truncates at
runtime), and banned placeholder terms (`from-echoes/terminology-guard.md`,
matched case-sensitively — the ban is on the capital, not the word, so
"light" the ordinary noun passes and "Light" the Destiny placeholder fails).

This is the layer that never calls a model and always agrees with itself:
given the same record twice, it gives the same verdict twice. What it
cannot judge — voice, whether the Spanish reads as translated rather than
written in Spanish, whether the English is generic software copy — is a
semantic reviewer's job, one layer up, and is exactly the layer this repo
doesn't have running live yet (see retriever.py's own docstring).

Usage:
  python3 gate.py --key "buff.cd_bolt.label" --en "Quick Shuttle" --es "Lanzadera Rapida"
  python3 gate.py --check-generated   # validate every record already shipped
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

# ui-and-strings.md's own table. Cap applies independently per language.
WIDGET_CAPS = {
    "MenuLabel": 20,
    "RelicName": 16,
    "RelicDescription": 90,
    "BuffLabel": 40,
    "StatLabel": 20,
    "ScoreProse": 200,
    "Prompt": 24,
}

# Inferred from this repo's own key naming (strings.generated.ts) — the real
# mapping lived in the pipeline this repo lost (see retriever.py). First pass
# assumed every "ui.*" key was a tight menu label and failed 41 of 109
# already-shipped, already-approved records — checked against the real
# content (`ui.tray.hint`, `ui.select.sub`, `ult.*.text` are all sentence-
# length hints and flavor text, not menu labels) and corrected: "ui." and
# "ult." default to the generous ScoreProse bucket, with the handful of
# genuinely short, fixed UI labels called out explicitly.
SHORT_UI_LABELS = {
    "ui.reroll", "ui.reroll.free", "ui.fight", "ui.restart", "ui.gold.none",
}

KEY_PREFIX_TO_CLASS = {
    "relic.": {"name": "RelicName", "desc": "RelicDescription"},
    "buff.": {"label": "BuffLabel", "text": "BuffLabel"},
    "ui.": {"*": "ScoreProse"},
    "score.": {"*": "ScoreProse"},
    "tier.": {"*": "StatLabel"},
    "class.": {"*": "ScoreProse"},
    "ult.": {"*": "ScoreProse"},
    "upgrade.": {"*": "BuffLabel"},
    "category.": {"*": "MenuLabel"},
}

# from-echoes/terminology-guard.md. Case-sensitive: the capital is the
# Destiny placeholder, the lowercase word is an ordinary noun and passes.
PLACEHOLDER_TERMS = ["Traveler", "Light", "Ghost", "Hive", "Vex", "Fallen",
                      "Scorn", "Engram", "Guardians", "Guardian"]

# Region leaks — matched case-insensitively, unlike the row above, because
# these are never legitimate under any capitalisation in shipped text.
REGION_TERMS = ["mexico", "méxico", "mexican", "mexicano", "mexicana",
                 "aztec", "azteca", "mexica", "mayan", "maya",
                 "nahuatl", "náhuatl", "quetzalcoatl",
                 "feathered serpent", "serpiente emplumada"]


def widget_class_for(key: str) -> str:
    if key in SHORT_UI_LABELS:
        return "MenuLabel"
    for prefix, parts in KEY_PREFIX_TO_CLASS.items():
        if key.startswith(prefix):
            suffix = key.rsplit(".", 1)[-1]
            return parts.get(suffix, parts.get("*", "MenuLabel"))
    return "MenuLabel"


def placeholders(text: str) -> set:
    return set(re.findall(r"\{[a-zA-Z_]+\}", text))


def validate_record(key: str, en: str, es: str) -> List[str]:
    errors = []
    if not en.strip():
        errors.append("ERR_EMPTY_EN")
    if not es.strip():
        errors.append("ERR_EMPTY_ES")
    if errors:
        return errors  # nothing else is meaningful to check against blanks

    cap = WIDGET_CAPS[widget_class_for(key)]
    if len(en) > cap:
        errors.append(f"ERR_OVER_CAP_EN  {len(en)} chars > {cap} ({widget_class_for(key)})")
    if len(es) > cap:
        errors.append(f"ERR_OVER_CAP_ES  {len(es)} chars > {cap} ({widget_class_for(key)})")

    en_ph, es_ph = placeholders(en), placeholders(es)
    if en_ph != es_ph:
        errors.append(f"ERR_SPECIFIER_MISMATCH  en={sorted(en_ph)} es={sorted(es_ph)}")

    for text, lang in ((en, "EN"), (es, "ES")):
        for term in PLACEHOLDER_TERMS:
            if term in text:  # case-sensitive on purpose
                errors.append(f"ERR_BANNED_PLACEHOLDER_{lang}  '{term}' in: {text!r}")
        low = text.lower()
        for term in REGION_TERMS:
            if term in low:
                errors.append(f"ERR_REGION_LEAK_{lang}  '{term}' in: {text!r}")
    return errors


def check_generated() -> int:
    """Validate every record already shipped in strings.generated.ts."""
    path = Path(__file__).resolve().parent.parent.parent / "src" / "core" / "strings.generated.ts"
    text = path.read_text(encoding="utf-8")
    # The table is a plain JS object literal; pull key/en/es out with a regex
    # rather than a real TS parser, which is all a read-only check needs.
    pattern = re.compile(
        r'"([\w.]+)":\s*\{\s*en:\s*"((?:[^"\\]|\\.)*)",\s*es:\s*"((?:[^"\\]|\\.)*)"\s*\}')
    records = [(k, en.replace('\\"', '"'), es.replace('\\"', '"'))
               for k, en, es in pattern.findall(text)]
    if not records:
        sys.exit("no records parsed out of strings.generated.ts — check the regex against the current format")

    total_errors = 0
    for key, en, es in records:
        errs = validate_record(key, en, es)
        if errs:
            total_errors += len(errs)
            print(f"FAIL  {key}")
            for e in errs:
                print(f"  {e}")
    print(f"\n{len(records)} records checked, {total_errors} errors.")
    return 1 if total_errors else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--key", help="String key, e.g. buff.cd_bolt.label")
    ap.add_argument("--en", help="English text")
    ap.add_argument("--es", help="Spanish text")
    ap.add_argument("--check-generated", action="store_true",
                     help="Validate every record in strings.generated.ts")
    args = ap.parse_args()

    if args.check_generated:
        return check_generated()

    if not (args.key and args.en is not None and args.es is not None):
        ap.error("--key, --en and --es are required unless --check-generated is given")

    errors = validate_record(args.key, args.en, args.es)
    print(json.dumps({"key": args.key, "widget_class": widget_class_for(args.key),
                       "verdict": "FAIL" if errors else "PASS", "errors": errors}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
