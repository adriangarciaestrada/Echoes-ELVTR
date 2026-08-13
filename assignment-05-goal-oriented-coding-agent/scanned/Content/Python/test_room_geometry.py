"""Tests for the RoomSpec geometry mapping. Stdlib only, no engine.

    python3 -m unittest discover -s Content/Python

The fixture is a room the crew actually produced and that passed both the
deterministic gate and semantic review — not an invented one — so the numbers
asserted here are numbers the pipeline emits. It is inlined rather than read
from the other repository: a test that needs a second checkout is a test that
stops running.
"""

import unittest

import room_geometry as rg

# A vertical Segment A room: entry on the left at floor level, exit through the
# ceiling, a grapple pocket framed by a lip above its anchor.
SHAFT = {
    "room_id": "room_test_shaft",
    "segment": "SegmentA_Shared",
    "grid": 20,
    "cavity": [
        {"x": 0, "z": 0, "width": 800, "height": 400},
        {"x": 200, "z": 400, "width": 600, "height": 1200},
    ],
    "solids": [
        {"id": "ledge_1", "x": 240, "z": 360, "width": 300, "height": 40,
         "is_one_way": True},
        {"id": "ledge_2", "x": 400, "z": 560, "width": 300, "height": 40,
         "is_one_way": True},
        {"id": "seal", "x": 700, "z": 0, "width": 60, "height": 300,
         "breakable_by": "Bash"},
    ],
    "anchors": [{"id": "anchor_top", "x": 600, "z": 1400}],
    "doors": [
        {"id": "door_in", "side": "Left", "at": 0, "size": 200,
         "required_tool": "None"},
        {"id": "door_out", "side": "Top", "at": 500, "size": 200,
         "required_tool": "None"},
    ],
    "checkpoints": [],
    "critical_path": ["door_in", "ledge_1", "ledge_2", "door_out"],
    "pockets": [{"id": "pocket_high", "x": 600, "z": 1360,
                 "required_tool": "Grapple", "contents": "LoreCache"}],
}


def by_kind(plan, kind):
    return [p for p in plan if p["kind"] == kind]


def named(plan, suffix):
    return next(p for p in plan if p["name"].endswith(suffix))


class Rock(unittest.TestCase):
    def test_the_room_generates_its_own_walls(self):
        # Nothing in the spec describes a wall. They are what was not carved,
        # and if this returns nothing the room has no collision at all.
        self.assertTrue(rg.rock_rects(SHAFT))

    def test_rock_never_overlaps_the_cavity(self):
        for r in rg.rock_rects(SHAFT):
            for c in SHAFT["cavity"]:
                overlap_x = min(r["x"] + r["width"], c["x"] + c["width"]) - max(r["x"], c["x"])
                overlap_z = min(r["z"] + r["height"], c["z"] + c["height"]) - max(r["z"], c["z"])
                self.assertFalse(overlap_x > 0 and overlap_z > 0,
                                 f"rock {r} intrudes into cavity {c}")

    def test_the_carved_space_is_fully_open(self):
        # Sample the cavity densely; no rock rectangle may contain any of it.
        rects = rg.rock_rects(SHAFT)
        for c in SHAFT["cavity"]:
            for i in range(1, 10):
                for j in range(1, 10):
                    x = c["x"] + c["width"] * i / 10
                    z = c["z"] + c["height"] * j / 10
                    for r in rects:
                        inside = (r["x"] < x < r["x"] + r["width"]
                                  and r["z"] < z < r["z"] + r["height"])
                        self.assertFalse(inside, f"({x},{z}) should be open")

    def test_merging_keeps_the_actor_count_sane(self):
        # One actor per grid cell would be tens of thousands. The greedy merge
        # is what makes importing a room practical rather than a demonstration.
        self.assertLess(len(rg.rock_rects(SHAFT)), 60)

    def test_an_l_shape_needs_more_than_one_rectangle(self):
        # If the cavity were treated as a bounding box, the notch would fill in
        # and the room would stop being an L.
        self.assertGreater(len(rg.rock_rects(SHAFT)), 1)


class Placements(unittest.TestCase):
    def test_a_solid_is_centred_on_its_rectangle(self):
        ledge = named(rg.plan_room(SHAFT), "ledge_1")
        self.assertEqual(ledge["location"][0], 390.0)     # 240 + 300/2
        self.assertEqual(ledge["location"][2], 380.0)     # 360 + 40/2

    def test_scale_is_expressed_in_cube_units(self):
        ledge = named(rg.plan_room(SHAFT), "ledge_1")
        self.assertEqual(ledge["scale"][0], 3.0)          # 300 uu / 100 uu cube

    def test_everything_sits_on_the_play_plane(self):
        for p in rg.plan_room(SHAFT):
            self.assertEqual(p["location"][1], 0.0)

    def test_a_breakable_wall_is_distinguishable(self):
        self.assertEqual(len(by_kind(rg.plan_room(SHAFT), "breakable")), 1)

    def test_one_way_platforms_are_distinguishable(self):
        self.assertEqual(len(by_kind(rg.plan_room(SHAFT), "oneway")), 2)

    def test_a_top_door_lands_on_the_ceiling(self):
        door = named(rg.plan_room(SHAFT), "door_out")
        self.assertEqual(door["location"][0], 500.0)      # its offset along the side
        self.assertEqual(door["location"][2], 1600.0)     # the cavity's highest z

    def test_a_left_door_lands_on_the_left_wall(self):
        door = named(rg.plan_room(SHAFT), "door_in")
        self.assertEqual(door["location"][0], 0.0)

    def test_every_element_of_the_spec_is_placed(self):
        plan = rg.plan_room(SHAFT)
        self.assertEqual(len(by_kind(plan, "anchor")), 1)
        self.assertEqual(len(by_kind(plan, "door")), 2)
        self.assertEqual(len(by_kind(plan, "pocket")), 1)
        self.assertEqual(len(by_kind(plan, "checkpoint")), 0)

    def test_names_are_prefixed_so_a_reimport_can_find_them(self):
        # Idempotence depends on the importer being able to recognise what it
        # spawned last time.
        for p in rg.plan_room(SHAFT):
            self.assertTrue(p["name"].startswith("GEN_"))

    def test_the_plan_is_deterministic(self):
        self.assertEqual(rg.plan_room(SHAFT), rg.plan_room(SHAFT))


class Refusals(unittest.TestCase):
    def test_a_spec_without_a_cavity_is_refused(self):
        with self.assertRaises(rg.RoomGeometryError) as caught:
            rg.plan_room({"room_id": "empty"})
        self.assertIn("gate", str(caught.exception))

    def test_a_zero_width_solid_is_refused(self):
        spec = dict(SHAFT, solids=[dict(SHAFT["solids"][0], width=0)])
        with self.assertRaises(rg.RoomGeometryError):
            rg.plan_room(spec)

    def test_an_unknown_door_side_is_refused(self):
        spec = dict(SHAFT, doors=[dict(SHAFT["doors"][0], side="Sideways")])
        with self.assertRaises(rg.RoomGeometryError):
            rg.plan_room(spec)

    def test_duplicate_ids_are_refused(self):
        spec = dict(SHAFT, solids=[SHAFT["solids"][0], SHAFT["solids"][0]])
        with self.assertRaises(rg.RoomGeometryError):
            rg.plan_room(spec)


if __name__ == "__main__":
    unittest.main()
