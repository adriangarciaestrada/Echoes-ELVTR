"""Tests for the provenance gate. Stdlib only, no engine.

    python3 -m unittest discover -s Content/Python

What is pinned here is the refusal behaviour, because that is the whole point of
the module: every test that matters asserts something does NOT get imported.
"""

import json
import tempfile
import unittest
from pathlib import Path

import provenance as pv

ROOM = {
    "room_id": "room_test_01",
    "segment": "SegmentA_Shared",
    "dimensions": {"width": 4000, "height": 1500},
    "platforms": [{"id": "floor", "x": 0, "z": 0, "width": 4000, "is_one_way": False}],
    "gates": [],
    "checkpoints": [],
    "camera_bounds": {"min_x": 0, "max_x": 4000, "min_z": 0, "max_z": 1500},
}
GATE_PASS = {"kind": "room", "status": "PASS", "errors": []}
GATE_FAIL = {"kind": "room", "status": "FAIL",
             "errors": [{"code": "ERR_ROOM_BUDGET", "message": "too wide", "path": "d.width"}]}
REVIEW_PASS = {"room_id": "room_test_01", "status": "PASS", "findings": []}
REVIEW_OPEN = {"room_id": "room_test_01", "status": "NEEDS_INENGINE_CHECK",
               "findings": [{"code": "REACHABILITY_UNVERIFIABLE", "message": "check the jump"}]}


class ProvenanceCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write(self, name, payload):
        path = self.dir / name
        path.write_text(json.dumps(payload))
        return path

    def stamped(self, gate=GATE_PASS, review=REVIEW_PASS):
        artifact = self.write("room.json", ROOM)
        gate_path = self.write("gate.json", gate)
        review_path = self.write("review.json", review) if review else None
        pv.stamp(artifact, gate_path, review_path)
        return artifact


class Refusals(ProvenanceCase):
    def test_no_record_at_all_is_refused(self):
        artifact = self.write("room.json", ROOM)
        with self.assertRaises(pv.ProvenanceError) as c:
            pv.check(artifact)
        self.assertIn("no provenance record", str(c.exception))

    def test_stamped_but_unapproved_is_refused(self):
        artifact = self.stamped()
        with self.assertRaises(pv.ProvenanceError) as c:
            pv.check(artifact)
        self.assertIn("not approved", str(c.exception))

    def test_gate_failure_cannot_be_approved(self):
        artifact = self.stamped(gate=GATE_FAIL)
        with self.assertRaises(pv.ProvenanceError) as c:
            pv.approve(artifact, note="looks fine to me")
        self.assertIn("not a judgment call", str(c.exception))

    def test_missing_review_is_refused(self):
        artifact = self.stamped(review=None)
        with self.assertRaises(pv.ProvenanceError) as c:
            pv.approve(artifact, note="skipping review")
        self.assertIn("not optional", str(c.exception))

    def test_open_review_needs_an_explicit_override(self):
        artifact = self.stamped(review=REVIEW_OPEN)
        with self.assertRaises(pv.ProvenanceError) as c:
            pv.approve(artifact, note="probably fine")
        self.assertIn("REACHABILITY_UNVERIFIABLE", str(c.exception))

    def test_approval_needs_a_note(self):
        artifact = self.stamped()
        with self.assertRaises(pv.ProvenanceError):
            pv.approve(artifact, note="   ")

    def test_editing_the_artifact_after_approval_breaks_the_binding(self):
        artifact = self.stamped()
        pv.approve(artifact, note="walked it end to end")
        pv.check(artifact)  # good so far

        tampered = dict(ROOM, platforms=[dict(ROOM["platforms"][0], width=99999)])
        artifact.write_text(json.dumps(tampered))

        with self.assertRaises(pv.ProvenanceError) as c:
            pv.check(artifact)
        self.assertIn("changed after it was approved", str(c.exception))

    def test_editing_between_stamp_and_approval_is_caught(self):
        artifact = self.stamped()
        artifact.write_text(json.dumps(dict(ROOM, room_id="something_else")))
        with self.assertRaises(pv.ProvenanceError) as c:
            pv.approve(artifact, note="fine")
        self.assertIn("changed after it was stamped", str(c.exception))


class Acceptances(ProvenanceCase):
    def test_clean_review_plus_approval_passes(self):
        artifact = self.stamped()
        pv.approve(artifact, note="walked it end to end on a gamepad")
        record = pv.check(artifact)
        self.assertFalse(record["approval"]["override"])

    def test_override_is_allowed_and_recorded_as_such(self):
        artifact = self.stamped(review=REVIEW_OPEN)
        pv.approve(artifact, note="jumped the gap in PIE, clears with room to spare",
                   override=True)
        record = pv.check(artifact)
        self.assertTrue(record["approval"]["override"])
        self.assertEqual(record["approval"]["overridden"], ["REACHABILITY_UNVERIFIABLE"])

    def test_failures_are_recorded_not_discarded(self):
        # A rejected artifact still gets a record: the audit trail is the point.
        artifact = self.stamped(gate=GATE_FAIL)
        record = pv.load_record(artifact)
        self.assertEqual(record["gate"]["status"], "FAIL")
        self.assertEqual(record["gate"]["error_count"], 1)

    def test_unusable_gate_report_is_named(self):
        artifact = self.write("room.json", ROOM)
        bad = self.write("gate.json", {"kind": "room"})
        with self.assertRaises(pv.ProvenanceError) as c:
            pv.stamp(artifact, bad)
        self.assertIn("no usable status", str(c.exception))


if __name__ == "__main__":
    unittest.main()
