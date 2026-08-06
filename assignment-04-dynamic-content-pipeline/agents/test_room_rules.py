#!/usr/bin/env python3
"""Tests for the room gate. Stdlib only.

    python3 -m unittest discover -s agents

The fixture is the worked example inside `vault/04-world/roomspec.md`, read from
the document rather than copied here: a contract and an example that can drift
apart teach whichever one the reader happens to open. Every other test mutates
that example in one way and asserts the gate says so — a gate is only worth what
it refuses.
"""

import copy
import json
import re
import unittest
from pathlib import Path

import room_rules as rr
import validators as v

SPEC_DOC = Path(__file__).resolve().parent.parent / "vault" / "04-world" / "roomspec.md"
EXAMPLE = json.loads(re.search(r"```json\n(.*?)\n```", SPEC_DOC.read_text(), re.S).group(1))


def codes(errors):
    return {e["code"] for e in errors}


def mutated(**changes):
    room = copy.deepcopy(EXAMPLE)
    room.update(changes)
    return room


def solid(room, sid):
    return next(s for s in room["solids"] if s["id"] == sid)


class TheContractsOwnExample(unittest.TestCase):
    def test_it_passes(self):
        # If this fails, either the example or the rules moved without the other.
        self.assertEqual(v.validate_room(EXAMPLE), [])

    def test_it_is_not_a_corridor(self):
        self.assertGreaterEqual(rr.floor_levels(EXAMPLE), 3)
        self.assertGreaterEqual(rr.direction_changes(EXAMPLE), 1)
        self.assertIn("Right", rr.door_sides(EXAMPLE))


class Structure(unittest.TestCase):
    def test_a_room_with_no_cavity_is_not_a_room(self):
        self.assertIn("ERR_FIELD", codes(v.validate_room(mutated(cavity=[]))))

    def test_off_grid_coordinates_are_refused(self):
        room = copy.deepcopy(EXAMPLE)
        solid(room, "ledge_a")["x"] = 405
        self.assertIn("ERR_OFF_GRID", codes(v.validate_room(room)))

    def test_a_solid_embedded_in_rock_is_refused(self):
        # A sealing wall belongs across the passage, not in the stone beside it.
        room = copy.deepcopy(EXAMPLE)
        solid(room, "seal_east")["z"] = 900
        self.assertIn("ERR_IN_ROCK", codes(v.validate_room(room)))

    def test_duplicate_ids_are_refused(self):
        room = copy.deepcopy(EXAMPLE)
        solid(room, "ledge_b")["id"] = "ledge_a"
        self.assertIn("ERR_DUPLICATE_ID", codes(v.validate_room(room)))

    def test_the_path_must_run_door_to_door(self):
        room = copy.deepcopy(EXAMPLE)
        room["critical_path"] = room["critical_path"][1:]
        self.assertIn("ERR_PATH_ENDS", codes(v.validate_room(room)))

    def test_a_path_naming_nothing_real_is_refused(self):
        room = copy.deepcopy(EXAMPLE)
        room["critical_path"].insert(2, "ledge_that_does_not_exist")
        self.assertIn("ERR_UNKNOWN_ELEMENT", codes(v.validate_room(room)))


class Reach(unittest.TestCase):
    def test_a_step_beyond_the_guaranteed_rise_is_refused(self):
        room = copy.deepcopy(EXAMPLE)
        solid(room, "ledge_b")["z"] += 200          # 200 -> 400 of rise
        self.assertIn("ERR_UNREACHABLE", codes(v.validate_room(room)))

    def test_a_step_at_exactly_the_guaranteed_rise_passes(self):
        # The band is inclusive; the example already sits on it everywhere.
        self.assertNotIn("ERR_UNREACHABLE", codes(v.validate_room(EXAMPLE)))

    def test_a_gap_beyond_the_guaranteed_span_is_refused(self):
        room = copy.deepcopy(EXAMPLE)
        solid(room, "ledge_b")["x"] += 500
        self.assertIn("ERR_UNREACHABLE", codes(v.validate_room(room)))

    def test_walking_along_the_floor_is_not_a_gap(self):
        # The entry door is 400 from the first ledge, all of it solid floor.
        # An earlier version of these rules called that an unreachable gap.
        self.assertNotIn("ERR_NO_RUNUP", codes(v.validate_room(EXAMPLE)))

    def test_a_breakable_wall_with_no_runup_is_refused(self):
        # The bash only breaks at speed, so a wall with no floor to build it on
        # is sealed to everyone — a soft lock wearing a gate's clothes.
        room = copy.deepcopy(EXAMPLE)
        room["cavity"][0]["x"] = 2300
        room["cavity"][0]["width"] = 100
        self.assertIn("ERR_NO_RUNUP", codes(v.validate_room(room)))

    def test_an_anchor_out_of_range_is_refused(self):
        room = copy.deepcopy(EXAMPLE)
        room["cavity"][1]["height"] = 3000
        room["anchors"][0]["z"] = 3400
        self.assertIn("ERR_ANCHOR_UNUSABLE", codes(v.validate_room(room)))


class PocketsAreExclusiveAndSeen(unittest.TestCase):
    def test_a_pocket_base_movement_reaches_is_refused(self):
        room = copy.deepcopy(EXAMPLE)
        solid(room, "perch")["z"] = 1340            # 340 -> 180 above shaft_4
        room["pockets"][0]["z"] = 1380
        self.assertIn("ERR_POCKET_NOT_EXCLUSIVE", codes(v.validate_room(room)))

    def test_a_sealed_chamber_does_not_count_as_reached(self):
        # The floor either side of the cracked wall is at the same height. The
        # wall is the only thing making that pocket the Titan's.
        self.assertNotIn("ERR_POCKET_NOT_EXCLUSIVE", codes(v.validate_room(EXAMPLE)))

    def test_a_hidden_key_is_refused(self):
        # Visibility is about the lock, not the prize: move the anchor back into
        # the shadow of the ledge it serves and the pocket stops teaching anything.
        room = copy.deepcopy(EXAMPLE)
        room["anchors"][0]["x"] = 2000
        self.assertIn("ERR_POCKET_UNSEEN", codes(v.validate_room(room)))

    def test_a_pocket_whose_verb_has_nothing_to_act_on_is_refused(self):
        room = copy.deepcopy(EXAMPLE)
        room["anchors"] = []
        self.assertIn("ERR_POCKET_NO_MARKER", codes(v.validate_room(room)))


def corridor(room_id, x_span=2400, z_span=1000):
    """A featureless horizontal room — the shape generation drifts towards."""
    return {
        "room_id": room_id, "segment": "SegmentA_Shared", "grid": 20,
        "cavity": [{"x": 0, "z": 0, "width": x_span, "height": z_span}],
        "solids": [], "anchors": [], "checkpoints": [], "pockets": [],
        "doors": [{"id": f"{room_id}_in", "side": "Left", "at": 0, "size": 200,
                   "required_tool": "None"},
                  {"id": f"{room_id}_out", "side": "Right", "at": 0, "size": 200,
                   "required_tool": "None"}],
        "critical_path": [f"{room_id}_in", f"{room_id}_out"],
    }


class VarietyAcrossABatch(unittest.TestCase):
    def test_a_row_of_corridors_is_refused_on_every_count(self):
        found = codes(v.validate_room_batch([corridor("a"), corridor("b"), corridor("c")]))
        self.assertIn("ERR_MONOTONOUS_SEQUENCE", found)   # all horizontal, in a row
        self.assertIn("ERR_FLAT_BATCH", found)            # one floor level each
        self.assertIn("ERR_NO_VERTICAL_ROOM", found)      # nothing taller than wide
        self.assertIn("ERR_TOO_STRAIGHT", found)          # no direction changes
        self.assertIn("ERR_CHAIN_TOPOLOGY", found)        # doors only left and right

    def test_consecutive_rooms_may_not_share_an_orientation(self):
        tall = corridor("tall", x_span=2000, z_span=3000)
        found = codes(v.validate_room_batch([corridor("a"), corridor("b"), tall]))
        self.assertIn("ERR_MONOTONOUS_SEQUENCE", found)

    def test_alternating_orientations_clear_that_rule(self):
        tall = corridor("tall", x_span=2000, z_span=3000)
        found = codes(v.validate_room_batch([corridor("a"), tall, corridor("c")]))
        self.assertNotIn("ERR_MONOTONOUS_SEQUENCE", found)


if __name__ == "__main__":
    unittest.main()
