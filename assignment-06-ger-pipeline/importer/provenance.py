"""Provenance records: what an artifact passed, and who let it in.

The import stage is where generated content stops being a proposal and becomes
part of the game. Everything upstream of it — the deterministic gate, the
semantic reviewer — produces verdicts in files nobody is obliged to read. This
makes reading them obligatory: the importer asks this module, and this module
refuses anything that has not passed the gate and been approved.

Two design points, both load-bearing:

* **The record is a sidecar, not a field inside the artifact.** Validation
  metadata has to come from the validating layer, never from the producer. A
  `verified: true` written into the spec is something the generator could emit
  about itself, and stamping it would change the very bytes being attested. A
  separate file holding the artifact's hash keeps the artifact exactly as
  produced and still binds the two: edit the spec after approval and the hash
  stops matching.
* **A gate failure cannot be overridden; a review finding can.** The gate
  encodes facts — bounds, enums, budgets — and arguing with it is arguing with
  arithmetic. The reviewer raises questions that are answerable only by playing
  the game, which is exactly the judgment a human is here to supply. Overriding
  one is allowed, requires a reason, and is recorded as an override.

Attribution comes from version control, not from a name field: the record is
committed, and the commit says who.

Usage:

    provenance.py stamp   --file room.json --gate-report gate.json [--review r.json]
    provenance.py approve --file room.json --note "reason" [--override]
    provenance.py check   --file room.json

`check` exits 0 only when the artifact is unchanged since stamping, the gate
passed, and an approval is present. It is what the importer calls.
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "echoes.provenance/1"
SUFFIX = ".provenance.json"

# Reviewer verdicts that stand on their own. Anything else needs a human to say
# why it is being let through.
REVIEW_CLEAN = {"PASS", "APPROVED", "OK"}


class ProvenanceError(Exception):
    """The artifact cannot be imported, and the message says what is missing."""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def record_path(artifact):
    return Path(str(artifact) + SUFFIX)


def load_record(artifact):
    path = record_path(artifact)
    if not path.is_file():
        raise ProvenanceError(
            f"no provenance record at {path.name}. Run the gate, then:\n"
            f"  provenance.py stamp --file {Path(artifact).name} --gate-report <report.json>"
        )
    return json.loads(path.read_text())


def _read_json(path, label):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ProvenanceError(f"{label} at {path} is unreadable: {exc}") from exc


def stamp(artifact, gate_report, review_report=None):
    """Write the record. Records failures too — a rejected artifact is evidence."""
    spec = _read_json(artifact, "artifact")
    gate = _read_json(gate_report, "gate report")

    status = gate.get("status")
    if status not in {"PASS", "FAIL"}:
        raise ProvenanceError(
            f"gate report has no usable status (got {status!r}); "
            "expected the output of validators.py"
        )

    record = {
        "schema": SCHEMA,
        "artifact": {
            "name": Path(artifact).name,
            "sha256": sha256(artifact),
            "kind": gate.get("kind"),
            "id": spec.get("room_id") or spec.get("encounter_id") or spec.get("id"),
        },
        "gate": {
            "status": status,
            "error_count": len(gate.get("errors") or []),
            "report_sha256": sha256(gate_report),
            # The law the verdict was produced under. A record that binds only
            # the artifact lets an old PASS outlive the rules that granted it.
            "rules_sha256": gate.get("rules_sha256"),
            "stamped_at": _now(),
        },
        "review": None,
        "approval": None,
    }

    if review_report:
        review = _read_json(review_report, "review report")
        findings = review.get("findings") or []
        record["review"] = {
            "status": review.get("status"),
            "finding_count": len(findings),
            "finding_codes": sorted({f.get("code") for f in findings if f.get("code")}),
            "report_sha256": sha256(review_report),
        }

    record_path(artifact).write_text(json.dumps(record, indent=2) + "\n")
    return record


def approve(artifact, note, override=False):
    record = load_record(artifact)

    if record["gate"]["status"] != "PASS":
        raise ProvenanceError(
            f"gate status is {record['gate']['status']} with "
            f"{record['gate']['error_count']} error(s). A deterministic failure is "
            "not a judgment call — fix the spec and re-stamp."
        )

    if record["artifact"]["sha256"] != sha256(artifact):
        raise ProvenanceError(
            "the artifact changed after it was stamped. Re-run the gate and re-stamp "
            "before approving."
        )

    review = record.get("review")
    if review is None:
        raise ProvenanceError(
            "no review recorded. Generate → Validate → Review → Import: the review "
            "is not optional. Re-stamp with --review."
        )

    unresolved = review.get("status") not in REVIEW_CLEAN
    if unresolved and not override:
        raise ProvenanceError(
            f"review status is {review.get('status')!r} with "
            f"{review.get('finding_count')} finding(s): "
            f"{', '.join(review.get('finding_codes') or []) or 'unnamed'}. "
            "Resolve them, or approve with --override and a note saying how each "
            "was answered in engine."
        )

    if not (note or "").strip():
        raise ProvenanceError("an approval needs a note saying what was checked.")

    record["approval"] = {
        "at": _now(),
        "note": note.strip(),
        "override": bool(unresolved),
        "overridden": review.get("finding_codes") or [] if unresolved else [],
    }
    record_path(artifact).write_text(json.dumps(record, indent=2) + "\n")
    return record



def current_rules_fingerprint():
    """The fingerprint of the rules as they exist right now, or None.

    None when the validator modules are not importable — a packaged game, a
    stripped checkout. In that case staleness cannot be judged and the artifact
    hash remains the only bond; refusing to import anywhere the rules are absent
    would make the record unusable outside the dev machine.
    """
    try:
        import validators
        return validators.rules_fingerprint()
    except Exception:
        return None


def check_preview(artifact):
    """Raise unless the artifact may be built in the preview level.

    Preview is a review instrument, not an import. It exists so that a human can
    walk a room before judging it, which is strictly better than judging a spec:
    approvals written from a spec alone tend to say so themselves.

    The gate applies here, because a room still being iterated is best walked
    once it is at least arithmetically sound. Approval deliberately does not,
    because approval is the thing the preview exists to inform. What keeps this
    from becoming a way around the gate is that it builds somewhere else: a
    preview level is a fixture, not the game, and `check` still guards the real
    one.

    To walk a room the gate rejects — which is how the gate itself gets checked
    against reality — use `check_diagnostic` instead.

    The hash is still bound, so the room that gets approved is the room that was
    played, byte for byte.
    """
    record = load_record(artifact)

    if record.get("schema") != SCHEMA:
        raise ProvenanceError(
            f"record schema is {record.get('schema')!r}, expected {SCHEMA!r}")
    if record["artifact"]["sha256"] != sha256(artifact):
        raise ProvenanceError(
            "the artifact changed after it was stamped. Re-run the gate and re-stamp "
            "before previewing, or the room you walk is not the room on record.")
    if record["gate"]["status"] != "PASS":
        raise ProvenanceError(
            f"gate status is {record['gate']['status']} with "
            f"{record['gate']['error_count']} error(s). Fix the spec and re-stamp, or "
            "preview it in diagnostic mode to see the failure for yourself.")
    return record


def check_diagnostic(artifact):
    """Raise unless the artifact can be built for the express purpose of failing.

    Requiring the gate to pass before a room may be walked was backwards. It
    meant only rooms the gate approves could ever be built, so the gate could
    never be contradicted by play — and play is what found the rule the gate was
    missing in the first place. A check that cannot be falsified is not a check,
    it is an assumption with a test suite.

    So this asks for less: a record must exist and its hash must still match, so
    that what gets walked is what was measured. The gate's verdict is reported
    rather than enforced. Nothing about the import path changes; that still
    demands an approval, and a diagnostic build goes to a fixture level under its
    own label.
    """
    record = load_record(artifact)

    if record.get("schema") != SCHEMA:
        raise ProvenanceError(
            f"record schema is {record.get('schema')!r}, expected {SCHEMA!r}")
    if record["artifact"]["sha256"] != sha256(artifact):
        raise ProvenanceError(
            "the artifact changed after it was stamped, so the room you would walk is not "
            "the room the gate measured. Re-run the gate and re-stamp first.")
    return record


def check(artifact):
    """Raise unless the artifact is safe to import. The importer's precondition."""
    record = load_record(artifact)

    if record.get("schema") != SCHEMA:
        raise ProvenanceError(
            f"record schema is {record.get('schema')!r}, expected {SCHEMA!r}"
        )
    if record["artifact"]["sha256"] != sha256(artifact):
        raise ProvenanceError(
            "the artifact changed after it was approved — its hash no longer matches "
            "the record. Re-run the gate, re-stamp, and re-approve."
        )
    if record["gate"]["status"] != "PASS":
        raise ProvenanceError(f"gate status is {record['gate']['status']}, not PASS")

    # A PASS is a verdict, and a verdict is only as current as its law. This
    # exists because a room approved in August walked through the importer while
    # failing the current gate with eight softlocks: the record said PASS
    # because PASS had been true once.
    stamped_rules = record["gate"].get("rules_sha256")
    rules_now = current_rules_fingerprint()
    if stamped_rules and rules_now and stamped_rules != rules_now:
        raise ProvenanceError(
            "the validation rules have changed since this artifact was stamped, so its PASS "
            "was issued by a gate that no longer exists. Re-run the gate, re-stamp, and "
            "re-approve against the current rules.")
    if record.get("review") is None:
        raise ProvenanceError("no review recorded")
    if record.get("approval") is None:
        raise ProvenanceError(
            "not approved. Nothing reaches the level without a human saying so:\n"
            f"  provenance.py approve --file {Path(artifact).name} --note \"...\""
        )
    return record


def _describe(record):
    a, g, r, ap = (record["artifact"], record["gate"],
                   record.get("review"), record.get("approval"))
    lines = [f"{a['name']}  ({a['kind']}, id={a['id']})",
             f"  gate     {g['status']} ({g['error_count']} error(s))"]
    lines.append(f"  review   {r['status']} ({r['finding_count']} finding(s))"
                 if r else "  review   MISSING")
    if ap:
        mark = " OVERRIDE" if ap["override"] else ""
        lines.append(f"  approval {ap['at']}{mark} — {ap['note']}")
    else:
        lines.append("  approval MISSING")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_stamp = sub.add_parser("stamp", help="record gate and review verdicts")
    p_stamp.add_argument("--file", required=True)
    p_stamp.add_argument("--gate-report", required=True)
    p_stamp.add_argument("--review")

    p_approve = sub.add_parser("approve", help="record human approval")
    p_approve.add_argument("--file", required=True)
    p_approve.add_argument("--note", required=True)
    p_approve.add_argument("--override", action="store_true",
                           help="accept unresolved review findings, with the note "
                                "explaining how each was answered in engine")

    p_check = sub.add_parser("check", help="the importer's precondition")
    p_check.add_argument("--file", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "stamp":
            record = stamp(args.file, args.gate_report, args.review)
        elif args.command == "approve":
            record = approve(args.file, args.note, args.override)
        else:
            record = check(args.file)
    except ProvenanceError as exc:
        print(f"REFUSED — {exc}", file=sys.stderr)
        return 1

    print(_describe(record))
    return 0


if __name__ == "__main__":
    sys.exit(main())
