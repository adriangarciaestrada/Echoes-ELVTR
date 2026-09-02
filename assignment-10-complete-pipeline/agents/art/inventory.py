#!/usr/bin/env python3
"""Prompt bodies, read from the inventory in the vault.

The subjects and their sizes are derived from the game; the words that describe
them are a human decision and live in `loom-vault/asset-inventory.md`. Parsing
them from there keeps the prompt in exactly one place — the export was otherwise
building its own from the enemy's stat line, so a curated prompt would have sat
in the vault while a generic one went to the API.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict

VAULT = Path.home() / "dev" / "ELVTR" / "loom-vault" / "asset-inventory.md"


def prompt_bodies(path: Path = VAULT) -> Dict[str, str]:
    """`spec id` -> the prompt body written for it."""
    full = path.read_text(encoding="utf-8")
    # Only the subject section. The global-parameters table upstream has the
    # same three-column shape, and without this bound it contributes rows like
    # `enemy_no_background` — a parser confidently reading the wrong table.
    # Matched by shape, not by count: the heading carries the number of subjects
    # and it changed the day the Weavers were added.
    import re as _re
    start = _re.search(r"^## The \d+ subjects", full, _re.M).start()
    end = full.index("## What is NOT generated")
    text = full[start:end]
    out: Dict[str, str] = {}

    # | `bolt_needle` | Swift Fang | a slender fang-shaped dart ... |
    # The id in the table is the id the export emits — no prefix is inferred.
    # Guessing it from the name worked until the Weavers arrived and would have
    # produced `enemy_weaver_hunter_card`.
    for row in re.findall(r"^\|\s*`([a-z_]+)`[^|]*\|([^|]*)\|([^|]*)\|\s*$", text, re.M):
        ident, body = row[0], row[2].strip()
        if not body or body.startswith("---"):
            continue
        out[ident] = body

    # Some subjects are indented blocks rather than table rows, and a block can
    # run to several lines with prose above it. Matching "the line right after
    # the heading" broke the moment the Beacon gained an explanatory paragraph.
    for heading, ident in (("The Beacon", "beacon"), ("The battlefield", "battlefield")):
        section = re.search(rf"^### {heading}\b.*?(?=^###|\Z)", full, re.M | re.S)
        if not section:
            continue
        block = re.findall(r"^ {4}(\S.*)$", section.group(0), re.M)
        if block:
            out[ident] = " ".join(line.strip() for line in block)
    return out


if __name__ == "__main__":
    bodies = prompt_bodies()
    print(f"{len(bodies)} prompt bodies read from {VAULT.name}\n")
    for k, v in bodies.items():
        print(f"  {k:26} {v[:66]}")
