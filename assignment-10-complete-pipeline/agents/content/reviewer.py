#!/usr/bin/env python3
"""The UI Copy Reviewer — semantic layer, judges what the gate cannot.

Ported from the ELVTR metroidvania's assignment-4 "14 UI Copy Reviewer"
agent. Division of labor: gate.py has already settled every countable
question (caps, placeholder parity, banned terms) before this runs — this
agent's input includes the gate's own verdict, and it must not recompute
what arithmetic already answered.

Usage:
  python3 reviewer.py --record record.json --gate-report gate_report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ai_call import call_claude, log_usage  # noqa: E402

from retriever import BASE_DIR  # noqa: E402

HERE = Path(__file__).resolve().parent
USAGE_LOG = HERE / "output" / "usage_log.jsonl"

PINNED_FILES = [
    BASE_DIR / "from-echoes" / "architects-cosmology.md",
    BASE_DIR / "ui-and-strings.md",
]

SYSTEM_PROMPT = """You are the UI Copy Reviewer for "The Loom". You are the
SECOND-LAYER, semantic reviewer — a deterministic gate already ran before
you and its report is in your input.

DIVISION OF LABOR:
The gate has already settled every countable question: whether the string
fits its widget_class cap in each language, whether placeholders match
between languages, whether a banned term or region reference appears. Do
NOT recompute any of this, do not count characters by eye, and never claim
to have measured anything — a language model miscounts. Do not raise a
finding that a string "may overflow" — that is arithmetic and its answer is
already in front of you.

YOUR JOB is the judgment no rule engine can make:

1. SOFTWARE_VOICE — the most common failure in this discipline. Could this
   string appear, unchanged, in any other game's UI? If yes, say so and
   name what's missing.
2. NOISE_NO_DECISION — a string the player would act on no differently
   having read it. The design law says a string that changes no decision
   is noise with a budget.
3. ES_TRANSLATED — the hardest finding to raise, and the one that decides
   whether bilingual parity is real or a checkbox. The gate proves the
   Spanish fits; only you can judge whether it reads as written in Spanish
   or as English wearing Spanish, mirroring its clause order.
4. SCREEN_JOB — each screen has one job (ui-and-strings.md's table); copy
   serving a different one is wrong even when well written.
5. SET_INCONSISTENT — read as one artifact, not a lone string: one concept
   should have one name, register should stay consistent.
6. RULE_SUSPECT — the one place you may disagree with the gate. If a
   string passes every deterministic rule and still looks wrong, say so
   with this code rather than silently overruling the gate — this reports
   that a threshold may be miscalibrated, not that you're ignoring it.

AUTHORITATIVE CONTEXT:
Design rules are in the injected PINNED CONTEXT — cite them, do not restate
from memory.

OUTPUT — respond with ONLY this JSON object, no prose outside it:
{
  "key": "the record's key",
  "status": "PASS | REVISE | REJECT",
  "findings": [
    {
      "code": "SOFTWARE_VOICE | NOISE_NO_DECISION | ES_TRANSLATED | SCREEN_JOB | SET_INCONSISTENT | RULE_SUSPECT",
      "message": "the concern, and what it costs the player",
      "quote_from_source": "the line of pinned context it contradicts, if applicable",
      "suggestion": {"text_en": "...", "text_es": "..."}
    }
  ]
}
"""


def load_pinned() -> str:
    parts = []
    for path in PINNED_FILES:
        parts.append(f"--- PINNED: {path.relative_to(BASE_DIR)} ---\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(parts)


"""
The judge's model, now explicit rather than inherited.

This file's own commit message and README said "reviewer.py (Haiku)", but
no model was ever passed, so every run silently used ai_call's
writer-grade default. Routing it was then A/B'd on the identical record,
prompt and gate report (`output/usage_log.jsonl`, entries 3 and 4):

    Sonnet 5    $0.0814   REVISE - caught the EN/ES meaning drift
    Haiku 4.5   $0.0543   PASS   - reported no findings at all

33% cheaper and blind to the one defect class this layer exists to catch:
a gate cannot see meaning drift, so a reviewer that misses it makes the
whole stage decorative. The saving is refused. Kept as a parameter so the
next candidate model can be measured the same way rather than argued
about.
"""
REVIEW_MODEL = "claude-sonnet-5"


def review(record: Dict[str, Any], gate_report: Dict[str, Any],
           model: str = REVIEW_MODEL) -> Dict[str, Any]:
    pinned = load_pinned()
    user = (f"PINNED CONTEXT:\n{pinned}\n\n"
            f"RECORD UNDER REVIEW:\n{json.dumps(record, indent=1, ensure_ascii=False)}\n\n"
            f"GATE REPORT (already ran, do not recompute):\n{json.dumps(gate_report, indent=1)}\n\n"
            "Respond with the JSON object only.")
    raw, usage = call_claude(SYSTEM_PROMPT, user, model=model)
    log_usage(USAGE_LOG, "reviewer", 0, usage)

    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        sys.exit(f"reviewer did not return valid JSON:\n{raw}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--record", required=True, help="Path to the writer's StringRecord JSON")
    ap.add_argument("--gate-report", required=True, help="Path to gate.py's JSON verdict")
    args = ap.parse_args()

    record = json.loads(Path(args.record).read_text(encoding="utf-8"))
    gate_report = json.loads(Path(args.gate_report).read_text(encoding="utf-8"))
    result = review(record, gate_report)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
