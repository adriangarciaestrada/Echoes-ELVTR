"""
Editor automation: build a crew-produced room in the level.

Run inside the UE editor. Two consoles, two syntaxes — `py <file> <args>` is a
Cmd-mode command, and typing it in Python mode is a syntax error:

    Python mode:  import import_room; import_room.import_room("/path/to/room.json")
    Cmd mode:     py import_room /path/to/room.json

Re-importing after editing this file needs the module reloaded, since Python
caches it for the editor session:

    import importlib, import_room; importlib.reload(import_room)

This is the Import stage of Generate → Validate → Review → Import, and the only
one of the four that touches the real project. It therefore refuses more than it
accepts.

Nothing is built unless the artifact carries a provenance record showing that the
deterministic gate passed, that a review happened, and that a human approved it —
with the artifact's hash matching, so a spec edited after approval is caught. See
`provenance.py`; the whole plan is computed in memory before the first actor is
spawned, so a spec that fails halfway cannot leave half a room behind.

Idempotent: re-running clears the actors it spawned last time, identified by the
`GEN_<room_id>_` prefix, so importing twice leaves one room rather than two.
"""
import json
import os
import sys

import unreal

from provenance import ProvenanceError, check
from room_geometry import RoomGeometryError, plan_room

CUBE = unreal.load_object(None, "/Engine/BasicShapes/Cube.Cube")
_eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# Every kind gets a distinct tag so a grey box can still be read at a glance,
# and so a later pass can swap art per kind without re-deriving what is what.
KIND_TAGS = {
    "rock": "Rock", "solid": "Platform", "oneway": "OneWay",
    "breakable": "Breakable", "anchor": "Anchor", "door": "Door",
    "checkpoint": "Checkpoint", "pocket": "Pocket",
}


def _clear_previous(room_id):
    prefix = f"GEN_{room_id}_"
    removed = 0
    for actor in _eas.get_all_level_actors():
        try:
            if actor.get_actor_label().startswith(prefix):
                _eas.destroy_actor(actor)
                removed += 1
        except Exception:
            pass
    return removed


def _spawn(placement):
    x, y, z = placement["location"]
    actor = _eas.spawn_actor_from_object(CUBE, unreal.Vector(float(x), float(y), float(z)))
    sx, sy, sz = placement["scale"]
    actor.set_actor_scale3d(unreal.Vector(float(sx), float(sy), float(sz)))
    actor.set_actor_label(placement["name"])
    tag = KIND_TAGS.get(placement["kind"])
    if tag:
        actor.tags = [unreal.Name(f"Room.{tag}")]
    return actor


def import_room(spec_path):
    if not os.path.isfile(spec_path):
        raise RuntimeError(f"spec not found: {spec_path}")

    # Refuse before reading anything into the level. An unapproved artifact is
    # not a build error to recover from; it is content that has not earned entry.
    try:
        record = check(spec_path)
    except ProvenanceError as exc:
        raise RuntimeError(f"[import_room] REFUSED — {exc}") from exc

    with open(spec_path, "r", encoding="utf-8") as handle:
        spec = json.load(handle)

    # Plan everything first: a spec that fails partway through cannot leave a
    # half-imported room behind, because nothing has been spawned yet.
    try:
        plan = plan_room(spec)
    except RoomGeometryError as exc:
        raise RuntimeError(f"[import_room] spec is unbuildable: {exc}") from exc

    room_id = spec.get("room_id") or "room"
    removed = _clear_previous(room_id)

    spawned = []
    for placement in plan:
        spawned.append(_spawn(placement))

    if len(spawned) != len(plan):
        raise RuntimeError(
            f"[import_room] planned {len(plan)} actors but spawned {len(spawned)}")

    counts = {}
    for placement in plan:
        counts[placement["kind"]] = counts.get(placement["kind"], 0) + 1
    summary = ", ".join(f"{n} {k}" for k, n in sorted(counts.items()))

    approved_at = (record.get("approval") or {}).get("at", "?")
    unreal.log(
        f"[import_room] {room_id}: {len(spawned)} actors ({summary}); "
        f"{removed} from a previous import removed. Approved {approved_at}. "
        "Save the level with Ctrl+S."
    )
    return spawned


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: py import_room <room.json>")
    import_room(sys.argv[1])
