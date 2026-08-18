#!/usr/bin/env python3
"""Tests for the GER loop. Stdlib only, and no model is called.

    python3 -m pytest agents/test_ger_rooms.py -q

Every path the circuit breaker can take is exercised here, because a breaker
that has only ever been watched succeed is a breaker nobody has seen work.
"""

import copy
import json
import unittest
from pathlib import Path

import ger_rooms as ger
import room_rules as rr

BASE = Path(__file__).resolve().parent.parent
CLEAN = json.loads((BASE / "production" / "output" / "R3_heights_demo.json").read_text())


def broken_headroom():
    """The failure that shipped: a ledge with the body's own room taken from it.

    A slab 160 above the surface of `ledge_2`. Every reach rule still passes —
    the jump onto it is unchanged — and the character cannot stand there.
    """
    room = copy.deepcopy(CLEAN)
    room["solids"].append({"id": "lid", "x": 2400, "z": 560, "width": 320, "height": 40})
    return room


def worse_than_broken():
    """The same failure twice over: a second slab, on a second landing."""
    room = broken_headroom()
    room["solids"].append({"id": "lid2", "x": 2200, "z": 960, "width": 440, "height": 40})
    return room


def worse_a_different_way():
    """Worse again, failing a different rule.

    A sustained regression needs two worsening attempts that are not the *same*
    failure: identical code and location twice is NO_PROGRESS, which is a
    different diagnosis with a different answer for the human.
    """
    room = broken_headroom()
    room["doors"][1]["required_tool"] = "Grapple"      # gates the way forward
    return room


class ScriptedGenerator:
    """Hands back a fixed series of rooms, then repeats the last one."""

    name = "scripted"

    def __init__(self, *rooms):
        self.rooms = list(rooms)
        self.calls = 0

    def generate(self, brief, repair):
        room = self.rooms[min(self.calls, len(self.rooms) - 1)]
        self.calls += 1
        return room


class TheEvaluatorEnforcesClearability(unittest.TestCase):
    """GDD §7.1: 'Clearability = 100% ... softlocks = 0', build-blocking."""

    def test_a_clean_room_passes(self):
        self.assertTrue(ger.Evaluator().evaluate(CLEAN).passed)

    def test_a_room_the_body_does_not_fit_through_is_a_softlock(self):
        verdict = ger.Evaluator().evaluate(broken_headroom())
        self.assertFalse(verdict.clearable)
        self.assertTrue(verdict.softlocks)

    def test_softlocks_are_separated_from_quality_findings(self):
        # A ladder-shaped climb is dull, not impassable; the two must not be
        # reported as the same kind of problem.
        verdict = ger.Evaluator().evaluate(broken_headroom())
        codes = {e["code"] for e in verdict.softlocks}
        self.assertIn("ERR_DEAD_SPACE", {e["code"] for e in verdict.other_errors})
        self.assertTrue(codes <= ger.CLEARABILITY_CODES)

    def test_the_signature_ignores_the_message(self):
        # Two attempts failing the same rule in the same place are the same
        # failure even when the message quotes different numbers.
        a = ger.Verdict(softlocks=[{"code": "ERR_NO_HEADROOM", "path": "critical_path", "message": "160"}])
        b = ger.Verdict(softlocks=[{"code": "ERR_NO_HEADROOM", "path": "critical_path", "message": "180"}])
        self.assertEqual(a.signature(), b.signature())


class TheRefinerTeachesTheRule(unittest.TestCase):
    def test_it_explains_only_the_rules_that_failed(self):
        verdict = ger.Evaluator().evaluate(broken_headroom())
        brief = ger.Refiner().brief(verdict, 1)
        self.assertIn("ERR_NO_HEADROOM", brief)
        self.assertNotIn("ERR_POCKET_UNSEEN", brief)     # never fired

    def test_it_carries_the_constraint_and_not_just_the_complaint(self):
        verdict = ger.Evaluator().evaluate(broken_headroom())
        brief = ger.Refiner().brief(verdict, 1)
        self.assertIn(str(int(rr.CAPSULE_HEIGHT)), brief)   # the measured body
        self.assertIn("§7.1", brief)                        # why it is fatal


class TheCircuitBreaker(unittest.TestCase):
    def _run(self, generator, attempts=4):
        return ger.run(generator, "test", attempts, quiet=True)

    def test_a_clean_room_is_accepted_on_the_first_attempt(self):
        report = self._run(ScriptedGenerator(CLEAN))
        self.assertEqual(report["status"], "ACCEPTED")
        self.assertEqual(report["attempts"], 1)

    def test_it_trips_on_no_progress_instead_of_spending_the_budget(self):
        bad = broken_headroom()
        report = self._run(ScriptedGenerator(bad, bad, bad, bad), attempts=4)
        self.assertEqual(report["status"], "ESCALATED")
        self.assertEqual(report["circuit_breaker"]["tripped"], "NO_PROGRESS")
        self.assertEqual(report["attempts"], 2)          # stopped early, on purpose

    def test_it_trips_on_regression(self):
        report = self._run(ScriptedGenerator(
            broken_headroom(), worse_than_broken(), worse_a_different_way()), attempts=5)
        self.assertEqual(report["status"], "ESCALATED")
        self.assertEqual(report["circuit_breaker"]["tripped"], "REGRESSION")

    def test_one_bad_step_does_not_trip_a_loop_that_recovers(self):
        # A generator moving geometry to satisfy one rule routinely breaks
        # another on the way. Tripping on the first worsening would throw away
        # loops that were about to succeed.
        report = self._run(ScriptedGenerator(
            broken_headroom(), worse_than_broken(), CLEAN), attempts=5)
        self.assertEqual(report["status"], "ACCEPTED")
        self.assertEqual(report["attempts"], 3)

    def test_a_repaired_room_is_accepted_mid_loop(self):
        report = self._run(ScriptedGenerator(broken_headroom(), CLEAN), attempts=4)
        self.assertEqual(report["status"], "ACCEPTED")
        self.assertEqual(report["attempts"], 2)

    def test_escalation_always_names_an_action_for_a_human(self):
        bad = broken_headroom()
        report = self._run(ScriptedGenerator(bad, bad, bad), attempts=3)
        breaker = report["circuit_breaker"]
        self.assertTrue(breaker["diagnosis"].strip())
        self.assertTrue(breaker["human_action"].strip())

    def test_nothing_is_accepted_while_a_softlock_stands(self):
        report = self._run(ScriptedGenerator(broken_headroom()), attempts=2)
        self.assertNotEqual(report["status"], "ACCEPTED")
        self.assertFalse(report["clearable"])


if __name__ == "__main__":
    unittest.main()
