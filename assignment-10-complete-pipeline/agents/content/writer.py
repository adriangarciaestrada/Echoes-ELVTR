#!/usr/bin/env python3
"""The UI Copy Writer — retrieval-augmented, bilingual, one string at a time.

Ported from the ELVTR metroidvania's assignment-4 "13 UI Copy Writer" agent
(same division of labor: pinned law + retrieved fact -> one StringRecord),
re-pointed at loom-vault and this game's own rules instead of that one's.

Pinned (jurisdiction, injected on every call, never retrieved):
  - from-echoes/terminology-guard.md — approved terms, banned placeholders,
    the case-sensitive rule, banned region references
  - from-echoes/architects-cosmology.md — the tone the text must carry
  - ui-and-strings.md — widget classes, caps, screen roster

Retrieved (per brief, via retriever.py's BM25 search):
  whatever loom-vault notes actually answer "what does this string need to
  say" for the specific brief given.

Usage:
  python3 writer.py --key "buff.cd_construct.label" --widget-class BuffLabel \
      --brief "a buff that raises Construct relic damage by 25%"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ai_call import call_claude, log_usage  # noqa: E402

from retriever import BASE_DIR, build_corpus, context_block, search  # noqa: E402

HERE = Path(__file__).resolve().parent
USAGE_LOG = HERE / "output" / "usage_log.jsonl"

PINNED_FILES = [
    BASE_DIR / "from-echoes" / "terminology-guard.md",
    BASE_DIR / "from-echoes" / "architects-cosmology.md",
    BASE_DIR / "ui-and-strings.md",
]

SYSTEM_PROMPT = """You are the UI Copy Writer for "The Loom", a survival
autobattler in the Echoes universe. You write the words a player reads on
screen — one bilingual string at a time.

AUTHORITATIVE CONTEXT:
The PINNED CONTEXT below is the single source of truth and outranks anything
retrieved. It gives you the approved terms and banned placeholders (use ONLY
what it approves, never rely on a memorized list), the tone this universe
speaks in, and the widget-class character caps. If a rule you need is
missing from the pinned or retrieved context, say so instead of guessing.

BOTH LANGUAGES ARE ORIGIN:
Write text_en and text_es together, with equivalent weight. Do not write
English and translate it — Spanish is written in Spanish, not derived from
the English clause by clause, even when a literal rendering would fit. Both
must independently fit the widget_class's character cap; if the Spanish
will not fit, the ENGLISH is what changes, not the meaning.

THE CAP IS NOT A SUGGESTION:
The widget_class you are given has a hard character cap, per language,
stated in the pinned ui-and-strings.md. Write to it; do not write long and
hope a reviewer trims it.

TONE — the house style for this whole universe: no cheerfulness, no
exclamation marks, no congratulating the player, never address them as
"player" or "gamer", no marketing register, no modern casual idiom. Sci-fi
melancholic, grounded in what is actually in front of the character. A
string that changes no decision is noise with a budget — cut it rather than
pad it.

WHAT NOT TO WRITE:
1. NO software copy. "Settings", "Are you sure?", "Press to continue" are
   correct, clear, and belong to no particular game. This is the single
   most common failure in this discipline.
2. NO explaining a mechanic the player will learn by playing. Name what is
   true, do not narrate how a system works.
3. NO banned placeholder terms (capitalised forms only — the term table is
   case-sensitive on purpose) and no naming the region this setting is
   built on, under any capitalisation.

CITE WHAT YOU USED:
Every record carries source_chunks: the path#heading of each retrieved
chunk it was actually written from. A record citing nothing is rejected.
If the retrieved context does not answer what this string should say, say
so instead of inventing a fact about the world.

OUTPUT — respond with ONLY this JSON object, no prose outside it:
{
  "key": "<the key given>",
  "widget_class": "<the widget_class given>",
  "text_en": "...",
  "text_es": "...",
  "source_chunks": ["path#heading", "..."]
}
"""


def load_pinned() -> str:
    parts = []
    for path in PINNED_FILES:
        parts.append(f"--- PINNED: {path.relative_to(BASE_DIR)} ---\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(parts)


def write_string(key: str, widget_class: str, brief: str, k: int = 4) -> Dict[str, Any]:
    corpus = build_corpus()
    hits = search(brief, corpus, k=k)
    retrieved = context_block(brief, hits)
    pinned = load_pinned()

    user = (f"KEY: {key}\nWIDGET_CLASS: {widget_class}\nBRIEF: {brief}\n\n"
            f"PINNED CONTEXT:\n{pinned}\n\n{retrieved}\n\n"
            "Respond with the JSON object only.")
    raw, usage = call_claude(SYSTEM_PROMPT, user)
    log_usage(USAGE_LOG, "writer", 0, usage)

    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        record = json.loads(text)
    except json.JSONDecodeError:
        sys.exit(f"writer did not return valid JSON:\n{raw}")
    return record


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--key", required=True)
    ap.add_argument("--widget-class", required=True)
    ap.add_argument("--brief", required=True)
    ap.add_argument("--k", type=int, default=4)
    args = ap.parse_args()

    record = write_string(args.key, args.widget_class, args.brief, k=args.k)
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
