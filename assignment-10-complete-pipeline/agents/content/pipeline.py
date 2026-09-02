#!/usr/bin/env python3
"""The full loop: retrieve -> generate -> gate -> review, one string at a time.

The gate never sees a model it can refuse instantly, and the reviewer never
runs against a record the gate has already rejected — recomputing voice on
copy that is illegal wastes a call for a verdict that cannot land above
FAIL. Both verdicts are persisted beside the record, not printed and lost.

Usage:
  python3 pipeline.py --key "buff.cd_construct.label" --widget-class BuffLabel \
      --brief "a buff that raises Construct relic damage by 25%" --out cd_construct
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import gate
from writer import write_string
from reviewer import review

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "output"


def run(key: str, widget_class: str, brief: str, out_name: str, k: int = 4) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"--- retrieve + generate: {key} ---")
    record = write_string(key, widget_class, brief, k=k)
    print(json.dumps(record, indent=2, ensure_ascii=False))
    (OUT_DIR / f"{out_name}.record.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"\n--- gate ---")
    errors = gate.validate_record(record.get("key", key),
                                   record.get("text_en", ""), record.get("text_es", ""))
    gate_report = {"key": key, "widget_class": widget_class,
                    "verdict": "FAIL" if errors else "PASS", "errors": errors}
    print(json.dumps(gate_report, indent=2))
    (OUT_DIR / f"{out_name}.gate.json").write_text(
        json.dumps(gate_report, indent=1), encoding="utf-8")

    if errors:
        print("\nGate FAILED — the reviewer never runs on illegal content.")
        return

    print(f"\n--- review ---")
    review_report = review(record, gate_report)
    print(json.dumps(review_report, indent=2, ensure_ascii=False))
    (OUT_DIR / f"{out_name}.review.json").write_text(
        json.dumps(review_report, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"\nDone. Artifacts: {out_name}.record.json, {out_name}.gate.json, "
          f"{out_name}.review.json in {OUT_DIR}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--key", required=True)
    ap.add_argument("--widget-class", required=True)
    ap.add_argument("--brief", required=True)
    ap.add_argument("--out", required=True, help="Output filename prefix")
    ap.add_argument("--k", type=int, default=4)
    args = ap.parse_args()
    run(args.key, args.widget_class, args.brief, args.out, k=args.k)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
