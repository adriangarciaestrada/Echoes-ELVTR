"""
Grey-box GYM map for R1 movement testing (Hunter).

Run inside the UE editor Python console:   py build_gym_map
(Requires the editor OPEN — this cannot run headless from outside.)

Spawns labelled cube platforms on the 2.5D lateral plane (X = horizontal,
Z = up, Y = 0), each one a station to feel ONE mechanic in isolation.
Re-running clears the previous GYM_* actors first, so it is safe to iterate.

Gap widths are first guesses — once the jump/dodge feel is tuned in
DT_GameFeel, nudge the X positions below so each station reads the way you
want (a gap the double jump *barely* clears teaches more than a trivial one).
"""
import unreal

CUBE = unreal.load_object(None, "/Engine/BasicShapes/Cube.Cube")
_eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def _clear_previous():
    for a in _eas.get_all_level_actors():
        try:
            if a.get_actor_label().startswith("GYM_"):
                _eas.destroy_actor(a)
        except Exception:
            pass


def _slab(label, x, top_z, length, thickness=40.0, depth=200.0):
    """A platform whose TOP surface sits at top_z, centered at x on the Y=0 plane."""
    center_z = top_z - thickness / 2.0
    actor = _eas.spawn_actor_from_object(CUBE, unreal.Vector(float(x), 0.0, float(center_z)))
    actor.set_actor_scale3d(unreal.Vector(length / 100.0, depth / 100.0, thickness / 100.0))
    actor.set_actor_label(label)
    return actor


def build():
    _clear_previous()

    # Station 1 — RUN LANE + COYOTE LEDGE: long ground ending in an edge at x=+800.
    #   Test: basic move + turnaround; then walk off the edge and jump ~0.1 s late (coyote).
    _slab("GYM_1_RunLane_Coyote", x=0, top_z=0, length=1600)

    # Station 2 — DOUBLE-JUMP GAP: a landing platform across a wide gap.
    #   Test: a gap too far for a single jump; needs the double jump to clear.
    _slab("GYM_2_DoubleJumpGap", x=1500, top_z=0, length=700)

    # Station 3 — HIGH PLATFORM (up): only reachable with the second jump.
    #   Test: double jump for height, not distance.
    _slab("GYM_3_HighUp", x=2300, top_z=350, length=500)

    # Station 4 — DROP + INPUT BUFFER: a lower platform under the high one.
    #   Test: drop off GYM_3 and press jump just BEFORE landing here -> it should fire on land.
    _slab("GYM_4_BufferDrop", x=2300, top_z=-160, length=500)

    # Station 5 — DODGE GAP: two platforms with a gap only the dodge burst crosses.
    #   Test: a gap a jump won't reach but a horizontal i-frame dodge will.
    _slab("GYM_5a_DodgeStart", x=3100, top_z=-160, length=400)
    _slab("GYM_5b_DodgeLand", x=3800, top_z=-160, length=400)

    unreal.log("[build_gym_map] GYM_* platforms spawned. Save the level with Ctrl+S.")


if __name__ == "__main__":
    build()
