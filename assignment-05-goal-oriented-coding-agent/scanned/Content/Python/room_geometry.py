"""RoomSpec to actor placements. Pure functions, no engine, no side effects.

The translation layer between the crew's JSON and the level. It is a component
in its own right rather than arithmetic inlined in an editor script, because
this is where the seam fails quietly: a room built at the wrong scale, or with
half its floor missing, still builds — and reads as a design decision rather
than a bug.

The contract is `vault/04-world/roomspec.md` in the development repository. Its
essential claim, and the reason this module is not a list of platforms:

    A room is solid material with a cavity carved out of it. Floor, walls and
    ceiling are not authored. They are whatever was not carved, and generating
    them is this module's main job.

Scope caveat: `plan_room` returns the whole plan before anything is spawned, so
a spec that fails halfway cannot leave half a room behind.
"""

UNIT_CUBE = 100.0          # /Engine/BasicShapes/Cube, 100 uu per side, centred
DEFAULT_GRID = 20.0
ROCK_MARGIN = 200.0        # how far the surrounding rock extends past the cavity
MARKER_SIZE = 80.0         # door, checkpoint and pocket markers in the greybox
ANCHOR_SIZE = 60.0
PLAY_DEPTH = 200.0         # extent on the frozen axis


class RoomGeometryError(ValueError):
    """A spec that is schema-valid but cannot be built as described."""


# --------------------------------------------------------------------------
# Cavity, and the rock around it
# --------------------------------------------------------------------------
def bounds(spec):
    cavity = spec.get("cavity")
    if not cavity:
        raise RoomGeometryError("spec has no cavity; run the gate before importing")
    return (min(c["x"] for c in cavity),
            min(c["z"] for c in cavity),
            max(c["x"] + c["width"] for c in cavity),
            max(c["z"] + c["height"] for c in cavity))


def _void_grid(spec, grid, sealed=()):
    """Mark every grid cell of the padded bounding box as void or rock."""
    min_x, min_z, max_x, max_z = bounds(spec)
    ox, oz = min_x - ROCK_MARGIN, min_z - ROCK_MARGIN
    cols = int(round((max_x - min_x + 2 * ROCK_MARGIN) / grid))
    rows = int(round((max_z - min_z + 2 * ROCK_MARGIN) / grid))

    rock = [[True] * cols for _ in range(rows)]
    for c in spec["cavity"]:
        i0 = int(round((c["x"] - ox) / grid))
        j0 = int(round((c["z"] - oz) / grid))
        i1 = i0 + int(round(c["width"] / grid))
        j1 = j0 + int(round(c["height"] / grid))
        for j in range(max(0, j0), min(rows, j1)):
            for i in range(max(0, i0), min(cols, i1)):
                rock[j][i] = False

    # A door has to be a hole. The cavity stops at the room's own edge, so the
    # surrounding rock closed every opening: two rooms placed against each other
    # met as two solid walls, and the marker cube in the doorway was the only
    # sign a door had ever been intended. Carve each one through the margin.
    def clear(x0, z0, x1, z1):
        for j in range(max(0, int(round((z0 - oz) / grid))),
                       min(rows, int(round((z1 - oz) / grid)))):
            for i in range(max(0, int(round((x0 - ox) / grid))),
                           min(cols, int(round((x1 - ox) / grid)))):
                rock[j][i] = False

    for d in spec.get("doors") or []:
        # A door is carved because something is on the other side. The one the
        # player arrives through has nothing behind it — it is where the world
        # begins — so leaving it open puts a hole in the outside of the map.
        if d.get("id") in sealed:
            continue
        at, size = d.get("at", 0), d.get("size", 200)
        side = d.get("side")
        if side == "Left":
            clear(min_x - ROCK_MARGIN, at, min_x, at + size)
        elif side == "Right":
            clear(max_x, at, max_x + ROCK_MARGIN, at + size)
        elif side == "Bottom":
            clear(at, min_z - ROCK_MARGIN, at + size, min_z)
        elif side == "Top":
            clear(at, max_z, at + size, max_z + ROCK_MARGIN)

    return rock, ox, oz, cols, rows


def rock_rects(spec, grid=None, sealed=()):
    """The solid material, merged into as few rectangles as possible.

    A cell-per-actor import would spawn tens of thousands of cubes for a room
    this size. Greedy merging — widest run first, then down while the run holds
    — brings a typical room to a few dozen, which is what makes the whole thing
    practical rather than a demonstration.
    """
    grid = grid or spec.get("grid") or DEFAULT_GRID
    rock, ox, oz, cols, rows = _void_grid(spec, grid, sealed)
    used = [[False] * cols for _ in range(rows)]
    rects = []

    for j in range(rows):
        for i in range(cols):
            if not rock[j][i] or used[j][i]:
                continue
            width = 0
            while i + width < cols and rock[j][i + width] and not used[j][i + width]:
                width += 1
            height = 1
            while j + height < rows and all(
                    rock[j + height][i + k] and not used[j + height][i + k]
                    for k in range(width)):
                height += 1
            for jj in range(j, j + height):
                for ii in range(i, i + width):
                    used[jj][ii] = True
            rects.append({"x": ox + i * grid, "z": oz + j * grid,
                          "width": width * grid, "height": height * grid})
    return rects


# --------------------------------------------------------------------------
# Placements
# --------------------------------------------------------------------------
def _box(x, z, width, height, name, kind, source_id=None, depth=PLAY_DEPTH):
    """Bottom-left anchored rectangle to a centred cube placement."""
    if width <= 0 or height <= 0:
        raise RoomGeometryError(f"{name}: extent must be positive, got {width}x{height}")
    return {
        "name": name,
        "kind": kind,
        "source_id": source_id,
        "location": (x + width / 2.0, 0.0, z + height / 2.0),
        "scale": (width / UNIT_CUBE, depth / UNIT_CUBE, height / UNIT_CUBE),
        "size": (width, depth, height),
    }


def _marker(x, z, size, name, kind, source_id):
    """A point element becomes a small cube centred on its coordinate."""
    return _box(x - size / 2.0, z - size / 2.0, size, size, name, kind, source_id,
                depth=size)


def _door_position(spec, door):
    """Doors carry a side and an offset along it, not a coordinate."""
    min_x, min_z, max_x, max_z = bounds(spec)
    side = door.get("side")
    if side == "Left":
        return min_x, door["at"] + door.get("size", MARKER_SIZE) / 2.0
    if side == "Right":
        return max_x, door["at"] + door.get("size", MARKER_SIZE) / 2.0
    if side == "Bottom":
        return door["at"], min_z
    if side == "Top":
        return door["at"], max_z
    raise RoomGeometryError(f"door '{door.get('id')}': unknown side {side!r}")


def plan_room(spec, sealed=()):
    """Every placement for a room, or raise. Nothing is built here.

    Order matters only for readability of the result: rock first, then the
    solids inside it, then the markers that are not geometry at all.
    """
    if not isinstance(spec, dict):
        raise RoomGeometryError("spec must be a JSON object")
    room_id = spec.get("room_id") or "room"

    placements = [
        _box(r["x"], r["z"], r["width"], r["height"],
             f"GEN_{room_id}_Rock_{i}", "rock")
        for i, r in enumerate(rock_rects(spec, sealed=sealed))
    ]

    for s in spec.get("solids") or []:
        kind = "breakable" if s.get("breakable_by") else (
            "oneway" if s.get("is_one_way") else "solid")
        placements.append(_box(s["x"], s["z"], s["width"], s["height"],
                               f"GEN_{room_id}_{s['id']}", kind, s.get("id")))

    for a in spec.get("anchors") or []:
        placements.append(_marker(a["x"], a["z"], ANCHOR_SIZE,
                                  f"GEN_{room_id}_{a['id']}", "anchor", a.get("id")))

    for d in spec.get("doors") or []:
        x, z = _door_position(spec, d)
        placements.append(_marker(x, z, MARKER_SIZE,
                                  f"GEN_{room_id}_{d['id']}", "door", d.get("id")))

    for c in spec.get("checkpoints") or []:
        placements.append(_marker(c["x"], c["z"], MARKER_SIZE,
                                  f"GEN_{room_id}_{c['id']}", "checkpoint", c.get("id")))

    for p in spec.get("pockets") or []:
        placements.append(_marker(p["x"], p["z"], MARKER_SIZE,
                                  f"GEN_{room_id}_{p['id']}", "pocket", p.get("id")))

    names = [p["name"] for p in placements]
    duplicates = {n for n in names if names.count(n) > 1}
    if duplicates:
        raise RoomGeometryError(f"duplicate element ids in spec: {sorted(duplicates)}")

    return placements
