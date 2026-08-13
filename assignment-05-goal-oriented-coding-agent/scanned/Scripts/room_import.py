#!/usr/bin/env python3
"""Build a generated room in the editor: to walk it, or to keep it.

This is Layer B of `vault/08-pipeline/authoring-pipeline.md`. The authority stays
outside the editor: provenance is checked and the geometry planned here, in
ordinary Python, and only then is a tool script *emitted* from the finished plan
and handed to the editor in one call. The script is generated from data, never
authored by an agent — an agent that could write it could bypass every gate.

Two modes, and the difference between them is the whole point.

    ./Scripts/room_import.py --preview <room.json>   # walk it, then judge it
    ./Scripts/room_import.py <room.json> [--at-x N]  # keep it; needs approval

**Preview** builds the room in a fixture level and drops the player at its entry
door so it can be played. It requires the gate to have passed and nothing more,
because approval is precisely what the preview exists to inform: a room judged
from its JSON is a room judged from imagination.

**Import** puts the room in the real level and refuses without a human approval
bound to the artifact's hash — so the room that gets kept is the room that was
walked, byte for byte.

`--at-x` shifts the room along X. A RoomSpec is authored at its own origin and
carries no world position, because a room should not know where it is placed;
two rooms imported without an offset land on top of each other. Placement is an
argument here, not a field there.

Idempotent in both modes: actors from a previous build of the same room are
removed first, identified by label prefix and re-checked by label before
deletion. Nothing outside that prefix is touched.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJECT, "Content", "Python"))
sys.path.insert(0, "/home/adriangest/dev/ELVTR/agents")
sys.path.insert(0, HERE)

import mcp  # noqa: E402
import provenance  # noqa: E402
import room_rules as rr  # noqa: E402
from room_geometry import RoomGeometryError, plan_room  # noqa: E402

CUBE = "/Engine/BasicShapes/Cube"

# Markers are signs, not geometry, and a solid 80-unit cube in a 200-tall
# doorway is a plug: the character is 176 tall and cannot pass it. Collision
# cannot be turned off per actor through the bridge — the property reports
# success and does not change — so markers are spawned from a copy of the engine
# cube with its collision shapes stripped. The engine asset is left alone.
MARKER_MESH = "/Game/Greybox/SM_MarkerCube"
MARKER_KINDS = {"checkpoint", "pocket", "anchor"}

# A door is not marked, it is cut. The doorway is a real hole in the rock now,
# so a cube standing in it says nothing the opening does not, and a solid one
# plugs a 200-tall passage for a 176-tall character. Removing the mesh's simple
# collision helps — character movement queries against simple shapes — but line
# traces still hit its triangles, and the surest way for a doorway not to be
# blocked is for nothing to be in it.
SKIP_KINDS = {"door"}
PREVIEW_LEVEL = "/Game/Maps/L_RoomPreview"
TEMPLATE_LEVEL = "/Game/Maps/L_GreyBox"

# Standing half-height is about 90 units (vault/04-world/movement-reach.md), so
# spawning a little above the door sill avoids starting inside the floor.
SPAWN_CLEARANCE = 120

# Mirrors import_room.py: one tag per kind, so a grey box still reads at a glance
# and a later art pass can swap meshes per kind without re-deriving what is what.
KIND_TAGS = {
    "rock": "Rock", "solid": "Platform", "oneway": "OneWay",
    "breakable": "Breakable", "anchor": "Anchor", "door": "Door",
    "checkpoint": "Checkpoint", "pocket": "Pocket",
}

# The emitted script is a fixed body plus injected data. Everything variable
# arrives as JSON, so the logic the editor runs is the same on every build.
SCRIPT_TEMPLATE = '''
import json

PLAN = json.loads(%(plan)s)
PREFIX = %(prefix)s
LEVEL = %(level)s
TEMPLATE = %(template)s
IS_PREVIEW = %(is_preview)s
ENTRY = json.loads(%(entry)s)

SC = "editor_toolset.toolsets.scene.SceneTools."
AC = "editor_toolset.toolsets.actor.ActorTools."
AS = "editor_toolset.toolsets.asset.AssetTools."
OB = "editor_toolset.toolsets.object.ObjectTools."

def T(name, args):
    return execute_tool(name, json.dumps(args))["returnValue"]

def ensure_preview_level():
    """The fixture: the template's lighting and game mode, none of its geometry.

    Duplicating the grey box inherits the GameMode override that possesses the
    player character, which is what makes a preview playable rather than merely
    visible.

    The emptiness is re-established on every run rather than once at creation.
    A fixture stripped only when new stays broken if the creating run failed
    halfway, and it inherits whatever the template happened to contain that day.
    Checking each time costs one pass and cannot drift.
    """
    created = False
    if not T(AS + "exists", {"path": LEVEL}):
        T(AS + "duplicate", {"path": TEMPLATE, "new_path": LEVEL})
        created = True

    # A freshly duplicated level is dirty, and the editor refuses to load a
    # level with unsaved changes. The fixture is ours, so saving is not a
    # decision anyone needs to make.
    if T(AS + "is_dirty", {"asset_path": LEVEL}):
        T(AS + "save_assets", {"asset_paths": [LEVEL]})
    if str(T(SC + "get_current_level", {})) != LEVEL:
        # Deliberately not load_level: it refuses while the target holds unsaved
        # changes, and a fixture's unsaved state is worth nothing by definition —
        # it is rebuilt from the spec on every run. The check that matters, that
        # the level being left behind is clean, already ran above.
        T("EditorToolset.EditorAppToolset.OpenEditorForAsset", {"assetPath": LEVEL})

    # Empty it completely. The fixture holds the one room being judged, so
    # anything solid already here is either the template's movement gym or a
    # room previewed earlier — and a second room overlapping the first is not a
    # test of either.
    stripped = 0
    for actor in T(SC + "find_actors", {"name": "", "tag": "", "collision_channels": []}):
        if "StaticMeshActor" not in str(T(OB + "get_class", {"instance": actor})):
            continue
        T(SC + "remove_from_scene", {"actor": actor})
        stripped += 1

    return ("created" if created else "reused") + ", %%d stray mesh(es) removed" %% stripped

def run():
    out = {}
    if IS_PREVIEW:
        # Switching levels with unsaved work raises a modal the editor waits on,
        # and a modal nobody is looking at is a hung editor. Refuse instead, and
        # let a human decide what those changes were worth.
        current = str(T(SC + "get_current_level", {}))
        if current != LEVEL and T(AS + "is_dirty", {"asset_path": current}):
            return {"blocked": "unsaved changes in " + current +
                    " — save or discard them before previewing"}

        out["fixture"] = ensure_preview_level()
        if str(T(SC + "get_current_level", {})) != LEVEL:
            T(SC + "load_level", {"level_path": LEVEL})

    # Remove this room's previous build. find_actors matches on label, but the
    # match is re-checked here: a deletion loop is the wrong place to trust a
    # filter you did not write.
    removed = 0
    for actor in T(SC + "find_actors", {"name": PREFIX, "tag": "", "collision_channels": []}):
        if str(T(AC + "get_label", {"actor": actor})).startswith(PREFIX):
            T(SC + "remove_from_scene", {"actor": actor})
            removed += 1

    spawned = []
    for p in PLAN:
        x, y, z = p["location"]
        sx, sy, sz = p["scale"]
        ref = T(SC + "add_to_scene_from_asset", {
            "asset_path": p["mesh"],
            "name": p["name"],
            "xform": {"location": {"x": x, "y": y, "z": z},
                       "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                       "scale": {"x": sx, "y": sy, "z": sz}}})
        T(AC + "set_label", {"actor": ref, "label": p["name"]})
        if p["tag"]:
            T(AC + "add_tag", {"actor": ref, "tag": p["tag"]})
        spawned.append(p["name"])

    # Count what is actually in the level, not what the loop believes it made.
    present = 0
    for actor in T(SC + "find_actors", {"name": PREFIX, "tag": "", "collision_channels": []}):
        if str(T(AC + "get_label", {"actor": actor})).startswith(PREFIX):
            present += 1

    # Move the level's own PlayerStart to the room's entry. Passing a spawn
    # override to the play call is not enough: it only applies to sessions this
    # script starts, so pressing Play in the editor would still spawn wherever
    # the template left its PlayerStart — inside the rock, where the pawn fails
    # to spawn and the game comes up with no character at all.
    if IS_PREVIEW and ENTRY is not None:
        for ps in T(SC + "find_actors", {"name": "PlayerStart", "tag": "",
                                          "collision_channels": []}):
            T(AC + "set_actor_transform", {"actor": ps, "xform": {
                "location": {"x": ENTRY[0], "y": 0.0, "z": ENTRY[1]},
                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0}}})
            out["player_start"] = ENTRY

    out.update({"removed": removed, "spawned": len(spawned), "present_after": present})
    return out
'''


def entry_point(spec):
    """Where the player should appear: the first step of the critical path.

    The path names a door, and the door names a wall and a height. Turning that
    into a spawn is the importer's job, not the spec's — a room describes itself,
    not how it is entered for testing.
    """
    path = spec.get("critical_path") or []
    doors = {d.get("id"): d for d in (spec.get("doors") or [])}
    door = doors.get(path[0]) if path else None
    if door is None:
        door = (spec.get("doors") or [None])[0]
    if door is None:
        return None

    cavity = spec.get("cavity") or []
    if not cavity:
        return None
    xs = [r["x"] for r in cavity] + [r["x"] + r["width"] for r in cavity]
    zs = [r["z"] for r in cavity] + [r["z"] + r["height"] for r in cavity]

    side = str(door.get("side", "")).lower()
    at = door.get("at", 0)
    if side == "left":
        return (min(xs) + SPAWN_CLEARANCE, at + SPAWN_CLEARANCE)
    if side == "right":
        return (max(xs) - SPAWN_CLEARANCE, at + SPAWN_CLEARANCE)
    if side == "bottom":
        return (at, min(zs) + SPAWN_CLEARANCE)
    return (at, max(zs) - SPAWN_CLEARANCE)


def build_plan(spec_path, offset, preview, sealed=()):
    """Check provenance, plan the geometry, and shift it by (dx, dz).

    Refuses before anything else.
    """
    if not os.path.isfile(spec_path):
        raise SystemExit(f"[room_import] spec not found: {spec_path}")

    gate = provenance.check_preview if preview else provenance.check
    try:
        record = gate(spec_path)
    except provenance.ProvenanceError as exc:
        raise SystemExit(f"[room_import] REFUSED — {exc}")

    with open(spec_path, encoding="utf-8") as handle:
        spec = json.load(handle)

    try:
        placements = plan_room(spec, sealed=sealed)
    except RoomGeometryError as exc:
        raise SystemExit(f"[room_import] spec is unbuildable: {exc}")

    room_id = spec.get("room_id") or "room"
    plan = []
    for p in placements:
        if p["kind"] in SKIP_KINDS:
            continue
        x, y, z = p["location"]
        tag = KIND_TAGS.get(p["kind"])
        # The planner names every actor GEN_*, since it knows nothing about why
        # the room is being built. Preview actors are renamed PRE_* so that the
        # two can never be confused in a level, or by the cleanup that follows.
        name = p["name"]
        if preview and name.startswith("GEN_"):
            name = "PRE_" + name[4:]
        plan.append({"name": name, "kind": p["kind"],
                     "mesh": MARKER_MESH if p["kind"] in MARKER_KINDS else CUBE,
                     "location": [x + offset[0], y, z + offset[1]],
                     "scale": list(p["scale"]),
                     "tag": f"Room.{tag}" if tag else ""})
    return record, spec, room_id, plan


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("spec", nargs="+",
                        help="one room, or several to join end to end")
    parser.add_argument("--preview", action="store_true",
                        help="build in the fixture level and play it; needs no approval")
    parser.add_argument("--at-x", type=float, default=0.0,
                        help="shift the room along X (import mode; default 0)")
    parser.add_argument("--no-play", action="store_true",
                        help="preview without starting a play session")
    parser.add_argument("--dry-run", action="store_true",
                        help="plan and report without touching the editor")
    args = parser.parse_args()

    tag = "PRE" if args.preview else "GEN"
    base = (0.0 if args.preview else args.at_x, 0.0)
    records, specs, ids, plan = [], [], [], []
    for i, path in enumerate(args.spec):
        if i:
            # Where this room goes is decided by the doors, not declared: the
            # previous room's exit and this one's entrance have to meet.
            with open(path, encoding="utf-8") as handle:
                move, why = rr.connection(specs[-1], json.load(handle))
            if move is None:
                raise SystemExit(f"[room_import] '{ids[-1]}' cannot be followed by "
                                 f"{os.path.basename(path)}: {why}")
            base = (base[0] + move[0], base[1] + move[1])
        # The door the player arrives through opens onto nothing, so it is left
        # as wall: carving it would put a hole in the outside of the world.
        sealed = ()
        if i == 0:
            with open(path, encoding="utf-8") as handle:
                first = json.load(handle)
            entry, _ = rr.end_doors(first)
            sealed = (entry.get("id"),) if entry else ()
        rec, spec, rid, part = build_plan(path, base, args.preview, sealed)
        if i:
            print(f"[room_import] {rid} joined at {base[0]:+.0f}, {base[1]:+.0f}")
        records.append(rec); specs.append(spec); ids.append(rid); plan += part
    record, spec, room_id = records[0], specs[0], ids[0]
    prefix = f"{tag}_"

    kinds = {}
    for p in plan:
        kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1
    summary = ", ".join(f"{n} {k}" for k, n in sorted(kinds.items()))
    print(f"[room_import] {room_id}: {len(plan)} actors ({summary})")

    if args.preview:
        review = record.get("review") or {}
        print(f"[room_import] preview — gate PASS, review {review.get('status', 'MISSING')}"
              f" {review.get('finding_codes') or ''}")
        if not record.get("review"):
            print("[room_import] note: no review on record; the room has not been read yet")
    else:
        print(f"[room_import] approved {(record.get('approval') or {}).get('at', '?')}; "
              f"offset x={offset:+.0f}")

    if args.dry_run:
        print("[room_import] dry run — editor untouched")
        return 0

    spawn = entry_point(spec) if args.preview else None
    script = SCRIPT_TEMPLATE % {
        "plan": repr(json.dumps(plan)), "prefix": repr(prefix), "cube": repr(CUBE),
        "level": repr(PREVIEW_LEVEL), "template": repr(TEMPLATE_LEVEL),
        "is_preview": repr(bool(args.preview)),
        "entry": repr(json.dumps(list(spawn) if spawn else None))}

    session = mcp.connect()
    result = mcp.run_script(session, script)
    print(f"[room_import] {result}")

    if isinstance(result, dict) and result.get("blocked"):
        print(f"[room_import] {result['blocked']}", file=sys.stderr)
        return 1

    if isinstance(result, dict) and result.get("present_after") != len(plan):
        print(f"[room_import] WARNING: planned {len(plan)} but the level holds "
              f"{result.get('present_after')}", file=sys.stderr)
        return 1

    if args.preview and not args.no_play:
        if spawn is None:
            print("[room_import] no entry door found; starting at the level default")
            options = {"bSimulate": False, "playMode": "PlayMode_InViewPort",
                       "warmupSeconds": 1.0}
        else:
            print(f"[room_import] entering at {spawn[0]:.0f}, {spawn[1]:.0f}")
            options = {"bSimulate": False, "playMode": "PlayMode_InViewPort",
                       "warmupSeconds": 1.0,
                       "startTransform": {
                           "location": {"x": float(spawn[0]), "y": 0.0, "z": float(spawn[1])},
                           "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                           "scale": {"x": 1.0, "y": 1.0, "z": 1.0}}}
        mcp.call(session, "EditorToolset.EditorAppToolset", "StartPIE", {"options": options})
        print("[room_import] playing. Stop with Escape in the editor, then decide.")
        return 0

    if args.preview:
        print("[room_import] built in the fixture level; not played.")
    else:
        print("[room_import] verified in the level. Save with Ctrl+S in the editor.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except mcp.McpError as exc:
        print(f"[room_import] {exc}", file=sys.stderr)
        sys.exit(1)
