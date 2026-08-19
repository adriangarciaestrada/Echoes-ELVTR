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
        solid(room, "seal_east")["z"] = 1700   # above the room entirely
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
        # A pillar standing on the hall floor cuts the run-up short. Before
        # floors were split by what stands on them, this changed nothing.
        room = copy.deepcopy(EXAMPLE)
        room["solids"].append({"id": "pillar", "x": 2200, "z": 0,
                               "width": 60, "height": 400})
        room["cavity"][2]["width"] = 300      # and no run-up on the far side either
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
        # Visibility is about the lock, not the prize: tuck the anchor down into
        # the shadow of the perch it serves and the pocket stops teaching anything.
        # (Just above the perch is exactly where a designer would innocently put
        # it — the example itself failed here until the anchor rose to 1700.)
        room = copy.deepcopy(EXAMPLE)
        room["anchors"][0]["z"] = 1560
        self.assertIn("ERR_POCKET_UNSEEN", codes(v.validate_room(room)))

    def test_a_pocket_whose_verb_has_nothing_to_act_on_is_refused(self):
        room = copy.deepcopy(EXAMPLE)
        room["anchors"] = []
        self.assertIn("ERR_POCKET_NO_MARKER", codes(v.validate_room(room)))


class TheKeyMustDeliverItsOwner(unittest.TestCase):
    """Found in play, in a room the gate had accepted: the Hunter's perch hung
    60 under the ceiling, so the pull ended with nowhere to stand and the pocket
    was unclaimable by the very class it belongs to. Reach, range and sight all
    passed; arrival had never been asked about.
    """

    def test_a_perch_pinned_under_the_ceiling_is_refused(self):
        room = copy.deepcopy(EXAMPLE)
        solid(room, "perch")["z"] = 1900          # top 1940; ceiling 2000 -> 60 of air
        room["pockets"][0]["z"] = 1940
        self.assertIn("ERR_POCKET_NO_FOOTING", codes(v.validate_room(room)))

    def test_an_anchor_with_no_landing_below_is_refused(self):
        room = copy.deepcopy(EXAMPLE)
        room["anchors"][0]["x"] = 1500            # over the shaft void; nearest top 900 down
        self.assertIn("ERR_ANCHOR_NO_LANDING", codes(v.validate_room(room)))

    def test_the_example_delivers_its_hunter(self):
        found = codes(v.validate_room(EXAMPLE))
        self.assertNotIn("ERR_ANCHOR_NO_LANDING", found)
        self.assertNotIn("ERR_POCKET_NO_FOOTING", found)


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


class TheBodyHasToFit(unittest.TestCase):
    """The rules that reach alone could not express.

    Every room the pipeline produced before these existed passed the gate and
    could not be climbed: the ledges were spaced exactly the guaranteed rise
    apart and stacked on top of one another.
    """

    def test_stacked_ledges_are_refused(self):
        room = copy.deepcopy(EXAMPLE)
        # Put shaft_2 back over shaft_1, the shape the contract used to show.
        solid(room, "shaft_2")["x"] = solid(room, "shaft_1")["x"] + 60
        self.assertIn("ERR_CLIMB_BLOCKED", codes(v.validate_room(room)))

    def test_alternating_ledges_are_accepted(self):
        self.assertNotIn("ERR_CLIMB_BLOCKED", codes(v.validate_room(EXAMPLE)))

    def test_a_ceiling_the_character_cannot_stand_under_is_refused(self):
        room = copy.deepcopy(EXAMPLE)
        # A slab right over the whole of ledge_b, one body-height too low.
        ledge_b = solid(room, "ledge_b")
        room["solids"].append({
            "id": "low_slab", "x": ledge_b["x"] - 100, "z": ledge_b["z"] + 140,
            "width": ledge_b["width"] + 200, "height": 40})
        self.assertIn("ERR_NO_HEADROOM", codes(v.validate_room(room)))

    def test_headroom_is_measured_not_guessed(self):
        # 200 of spacing minus a 40-thick ledge is 160 of air, and the capsule
        # is 176. The number in the message is the one a designer has to fix.
        ledge_a = solid(EXAMPLE, "ledge_a")
        support = (ledge_a["x"], ledge_a["x"] + ledge_a["width"],
                   ledge_a["z"] + ledge_a["height"], "ledge_a")
        room = copy.deepcopy(EXAMPLE)
        room["solids"].append({"id": "lid", "x": ledge_a["x"], "z": support[2] + 160,
                               "width": ledge_a["width"], "height": 40})
        self.assertEqual(rr.headroom(room, support), 160)


class TheRouteAsksForNoTool(unittest.TestCase):
    def test_a_gated_door_on_the_critical_path_is_refused(self):
        room = copy.deepcopy(EXAMPLE)
        next(d for d in room["doors"] if d["id"] == "door_out")["required_tool"] = "Grapple"
        self.assertIn("ERR_PATH_GATED", codes(v.validate_room(room)))

    def test_a_pocket_on_the_critical_path_is_refused(self):
        # Refused as an unresolvable step rather than by a rule of its own: a
        # pocket is not a surface, so the path cannot be walked through it.
        room = copy.deepcopy(EXAMPLE)
        room["critical_path"].insert(-1, "pocket_high")
        self.assertIn("ERR_UNKNOWN_ELEMENT", codes(v.validate_room(room)))


class HeightsAreStandard(unittest.TestCase):
    """Two named heights and multiples of the larger, observed from Dread.

    The point is that a player learns what one floor means and can then judge a
    room by eye, so a height that is nearly standard is worse than a wrong one.
    """

    def test_a_space_between_the_standard_heights_is_refused(self):
        room = copy.deepcopy(EXAMPLE)
        room["cavity"][0]["height"] = 600          # 1.5 floors
        self.assertIn("ERR_OFF_MODULE", codes(v.validate_room(room)))

    def test_the_tight_corridor_is_a_named_height(self):
        self.assertEqual(rr.height_class(rr.TIGHT), "tight")
        self.assertEqual(rr.height_class(rr.FLOOR), "standard")
        self.assertEqual(rr.height_class(3 * rr.FLOOR), "open x3")
        self.assertIsNone(rr.height_class(600))

    def test_a_surface_off_the_half_floor_module_is_refused(self):
        room = copy.deepcopy(EXAMPLE)
        ledge = solid(room, "ledge_a")
        ledge["z"] += 20                            # surface 220, off the 200 module
        self.assertIn("ERR_OFF_MODULE", codes(v.validate_room(room)))

    def test_a_tight_corridor_clips_the_jump(self):
        # This is what makes it claustrophobic rather than merely low, and it is
        # the reason the height decides which enemies may stand in it.
        self.assertLess(rr.TIGHT, rr.JUMPING_HEIGHT)
        self.assertGreaterEqual(rr.FLOOR, rr.JUMPING_HEIGHT)

    def test_half_a_floor_is_exactly_the_guaranteed_rise(self):
        # The reason the floor is 400 and not the 440 observed in Dread.
        self.assertEqual(rr.HALF_FLOOR, rr.RISE_GUARANTEED)


class OneFloorMadeOfSeveralSpaces(unittest.TestCase):
    """Rooms built from standard heights are several rectangles at one level."""

    def _three_spaces(self):
        return {"cavity": [{"x": 0, "z": 0, "width": 1200, "height": 400},
                            {"x": 1200, "z": 0, "width": 1000, "height": rr.TIGHT},
                            {"x": 2200, "z": 0, "width": 600, "height": 1200}],
                "solids": []}

    def test_adjacent_spaces_share_one_floor(self):
        spec = self._three_spaces()
        floors = rr.merge_floors(spec, rr.floor_spans(spec["cavity"]))
        self.assertEqual([(f[0], f[1]) for f in floors], [(0, 2800)])

    def test_a_wall_between_them_keeps_them_apart(self):
        spec = self._three_spaces()
        spec["solids"] = [{"id": "seal", "x": 1200, "z": 0, "width": 60,
                           "height": 260, "breakable_by": "Bash"}]
        floors = rr.merge_floors(spec, rr.floor_spans(spec["cavity"]))
        self.assertGreater(len(floors), 1)

    def test_a_step_is_not_a_wall(self):
        # MaxStepHeight is 45, so a low lip is walked over, not stopped at.
        spec = self._three_spaces()
        spec["solids"] = [{"id": "lip", "x": 1200, "z": 0, "width": 60, "height": 40}]
        floors = rr.merge_floors(spec, rr.floor_spans(spec["cavity"]))
        self.assertEqual([(f[0], f[1]) for f in floors], [(0, 2800)])


class NoSpaceTheP1ayerCanSeeAndNeverEnter(unittest.TestCase):
    def test_a_ledge_half_a_floor_up_must_be_a_step(self):
        # The first step of every climb lands here: 200 of rise minus a 40-thick
        # platform leaves 160 under a 176-tall character.
        room = copy.deepcopy(EXAMPLE)
        step = solid(room, "ledge_a")
        step["z"], step["height"] = 160, 40          # float it instead of filling
        self.assertIn("ERR_DEAD_SPACE", codes(v.validate_room(room)))

    def test_filling_it_down_resolves_it(self):
        self.assertNotIn("ERR_DEAD_SPACE", codes(v.validate_room(EXAMPLE)))

    def test_a_gap_big_enough_to_stand_in_is_fine(self):
        room = copy.deepcopy(EXAMPLE)
        self.assertEqual(rr.dead_space_under(room, solid(room, "ledge_b")), 0.0)


class AClimbIsARouteNotALadder(unittest.TestCase):
    """Calibrated against two rooms judged in play, not against a preference.

    One read as designed and one as generic filler. Both had four direction
    changes and covered the same lateral distance, so neither of those measures
    the difference. The generic one shuffled between two positions with every
    ledge the same width.
    """

    def test_shuffling_between_two_positions_is_refused(self):
        # shaft_4 is left where it is: it carries the exit door, and moving it
        # breaks the route before this rule is ever reached.
        room = copy.deepcopy(EXAMPLE)
        for sid, x in (("shaft_1", 1690), ("shaft_2", 1140), ("shaft_3", 1750)):
            solid(room, sid)["x"] = x
        self.assertIn("ERR_LADDER_CLIMB", codes(v.validate_room(room)))

    def test_a_climb_that_moves_across_the_room_is_accepted(self):
        self.assertNotIn("ERR_LADDER_CLIMB", codes(v.validate_room(EXAMPLE)))

    def test_two_lanes_are_fine_briefly(self):
        # Alternating twice is a rhythm; doing it four times is a ladder.
        self.assertEqual(rr.longest_two_lane_run([0, 500, 0]), 3)
        self.assertEqual(rr.longest_two_lane_run([0, 500, 0, 500]), 4)

    def test_a_shift_smaller_than_the_body_is_not_a_shift(self):
        self.assertEqual(rr.longest_two_lane_run([0, 500, 20, 520]), 4)

    def test_identical_platform_widths_are_refused(self):
        room = copy.deepcopy(EXAMPLE)
        for sid, x in (("ledge_a", 400), ("ledge_b", 1100), ("shaft_1", 1700),
                       ("shaft_2", 1220), ("shaft_3", 1800), ("shaft_4", 2000)):
            s = solid(room, sid)
            s["x"], s["width"] = x, 400
        self.assertIn("ERR_UNIFORM_LEDGES", codes(v.validate_room(room)))


class RoomsHaveShapes(unittest.TestCase):
    """Named so that sameness is countable. Nine rooms were built before this
    vocabulary existed and every one of them rose."""

    def _path(self, zs):
        """A room whose critical path visits the given heights, in order.

        The end supports reach the side walls and the doors sit at their
        heights: a door resolves to the surface it opens onto, so putting both
        at floor level would make every profile an arch regardless of the climb
        between them.
        """
        room = copy.deepcopy(EXAMPLE)
        room["cavity"] = [{"x": 0, "z": 0, "width": 4000, "height": 1600}]
        last = len(zs) - 1
        room["solids"] = [
            {"id": f"s{i}", "x": 0 if i == 0 else (3700 if i == last else i * 700),
             "z": z - 40, "width": 300, "height": 40}
            for i, z in enumerate(zs)]
        room["doors"] = [{"id": "a", "side": "Left", "at": zs[0], "size": 200,
                          "required_tool": "None"},
                         {"id": "b", "side": "Right", "at": zs[-1], "size": 200,
                          "required_tool": "None"}]
        room["critical_path"] = ["a"] + [f"s{i}" for i in range(len(zs))] + ["b"]
        return room

    def test_it_names_a_climb(self):
        self.assertEqual(rr.path_profile(self._path([200, 400, 600, 800])), "ASCENT")

    def test_it_names_a_descent(self):
        self.assertEqual(rr.path_profile(self._path([800, 600, 400, 200])), "DESCENT")

    def test_it_names_an_arch(self):
        self.assertEqual(rr.path_profile(self._path([200, 600, 1000, 600, 200])), "ARCH")

    def test_it_names_a_basin(self):
        self.assertEqual(rr.path_profile(self._path([1000, 600, 200, 600, 1000])), "BASIN")

    def test_a_batch_of_one_shape_is_refused(self):
        rooms = [self._path([200, 400, 600, 800]) for _ in range(3)]
        for i, r in enumerate(rooms):
            r["room_id"] = f"r{i}"
        self.assertIn("ERR_SAME_SHAPE", codes(v.validate_room_batch(rooms)))

    def test_neighbours_may_not_repeat_a_shape(self):
        up, down = self._path([200, 400, 600, 800]), self._path([800, 600, 400, 200])
        up["room_id"], down["room_id"] = "up", "down"
        self.assertNotIn("ERR_SAME_SHAPE", codes(v.validate_room_batch([up, down])))


class TheCorridorDecidesWhoFights(unittest.TestCase):
    def _encounter(self, archetype, x=200, z=0):
        return {"room_id": EXAMPLE["room_id"],
                "spawns": [{"archetype": archetype, "position": {"x": x, "z": z},
                            "patrol_range": 0, "facing_direction": "Left"},
                           {"archetype": "Crawler", "position": {"x": 100, "z": 0},
                            "patrol_range": 0, "facing_direction": "Left"}],
                "encounter_budget": {"total_enemies": 2, "archetype_count": 2}}

    def test_a_shieldbearer_under_a_ledge_is_refused_too(self):
        # x=1200 sits under ledge_b, whose underside is 360 up. The hop is no
        # more available there than in a tight corridor.
        found = codes(v.validate_encounter(self._encounter("Shieldbearer", x=1200), EXAMPLE))
        self.assertIn("ERR_ARCHETYPE_NEEDS_HEIGHT", found)

    def test_a_shieldbearer_under_a_clipped_jump_is_refused(self):
        tight = copy.deepcopy(EXAMPLE)
        tight["cavity"] = [{"x": 0, "z": 0, "width": 2400, "height": rr.TIGHT}]
        found = codes(v.validate_encounter(self._encounter("Shieldbearer", 0), tight))
        self.assertIn("ERR_ARCHETYPE_NEEDS_HEIGHT", found)

    def test_a_shieldbearer_in_a_standard_floor_is_accepted(self):
        found = codes(v.validate_encounter(self._encounter("Shieldbearer", 0), EXAMPLE))
        self.assertNotIn("ERR_ARCHETYPE_NEEDS_HEIGHT", found)

    def test_a_crawler_belongs_in_a_tight_corridor(self):
        tight = copy.deepcopy(EXAMPLE)
        tight["cavity"] = [{"x": 0, "z": 0, "width": 2400, "height": rr.TIGHT}]
        found = codes(v.validate_encounter(self._encounter("Walking Bomb", 0), tight))
        self.assertNotIn("ERR_ARCHETYPE_NEEDS_HEIGHT", found)


if __name__ == "__main__":
    unittest.main()


class ACarvedSpaceCanBeWalked(unittest.TestCase):
    """A terrace is corridors the player runs the length of, and until a cavity
    rectangle could name itself the route could not say so."""

    def _two_corridors(self, named):
        cavity = [{"x": 0, "z": 0, "width": 2000, "height": 400},
                  {"x": 1800, "z": 400, "width": 200, "height": 400}]
        if named:
            cavity[0]["id"] = "corridor_1"
        return {"cavity": cavity, "solids": [], "doors": [], "critical_path": []}

    def test_an_unnamed_floor_keeps_its_generated_label(self):
        spec = self._two_corridors(named=False)
        self.assertTrue(rr.floor_spans(spec["cavity"])[0][3].startswith("floor["))

    def test_a_named_space_can_be_resolved_by_the_path(self):
        spec = self._two_corridors(named=True)
        support = rr.support_of(spec, "corridor_1")
        self.assertIsNotNone(support)
        self.assertEqual(support[2], 0)


class ADoorIsAHoleOnTheOutside(unittest.TestCase):
    """Three defects hid each other here, and none showed while rooms were
    imported one at a time — an outer wall with no hole is just the world's edge."""

    def test_a_door_opening_onto_rock_is_refused(self):
        room = copy.deepcopy(EXAMPLE)
        # Drop the exit to a height the cavity does not reach at that wall.
        # 600..800 is the one band where nothing reaches the right wall.
        next(d for d in room["doors"] if d["id"] == "door_out")["at"] = 600
        self.assertIn("ERR_DOOR_INTO_ROCK", codes(v.validate_room(room)))

    def test_the_example_opens_onto_carved_space(self):
        for d in EXAMPLE["doors"]:
            self.assertTrue(rr.door_opens_onto_cavity(EXAMPLE, d), d["id"])

    def test_a_drop_that_cannot_be_climbed_back_is_refused(self):
        # Falling obeys no reach band, so nothing else in the gate sees this.
        room = copy.deepcopy(EXAMPLE)
        room["critical_path"] = ["door_in", "shaft_4", "ledge_a", "door_out"]
        self.assertIn("ERR_ONE_WAY_DROP", codes(v.validate_room(room)))

    def test_joined_rooms_share_one_wall(self):
        a, b = copy.deepcopy(EXAMPLE), copy.deepcopy(EXAMPLE)
        b["room_id"] = "second"
        offset, why = rr.connection(a, b)
        self.assertIsNotNone(offset, why)
        ba = rr.cavity_bounds(a["cavity"])
        bb = rr.cavity_bounds(b["cavity"])
        self.assertEqual(bb["min_x"] + offset[0], ba["max_x"] + rr.ROCK_MARGIN)
