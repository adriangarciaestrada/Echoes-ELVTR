# RoomSpec — the room contract

The single definition of what a room is. The Level Designer writes to it, the
deterministic gate enforces it, and the importer builds from it. When it changes,
those three change together; nothing here is restated elsewhere.

## Coordinates

- **x** runs horizontally, **z** vertically. Depth is frozen: the play plane is a
  single slice, and no spec expresses it.
- **Every rectangle is `(x, z, width, height)` with `(x, z)` at its bottom-left
  corner.** One convention, no exceptions. A platform's walkable surface is
  therefore `z + height` — a ledge you stand on at 300 is `{"z": 260, "height": 40}`.
- All coordinates are multiples of **`grid`** (default 20). Rectilinear geometry
  on a grid is what makes irregular outlines readable and keeps arithmetic exact.

## The room is solid rock with a hole cut in it

This is the part that differs most from a naive platformer level. A room is not
an empty box with ledges floating in it; it is **solid material with a cavity
carved out**. Floor, walls and ceiling are not authored — they are whatever was
not carved.

- **`cavity`** is a list of rectangles. Their union is the empty space. Because
  it is a union, an L, a T, a shaft with a side chamber or a notched hall all
  fall out of two or three rectangles with no new primitive.
- **`solids`** are put back *inside* the cavity: ledges, pillars, and the
  breakable walls that seal a pocket.

Anything outside the cavity union is rock. A pocket is sealed by placing a solid
across its only opening, not by leaving a gap in the cavity.

`camera_bounds` is **not** a field. It is the bounding box of the cavity union,
computed rather than declared — a bound that cannot disagree with the geometry
it is supposed to contain.

## Fields

| Field | Shape | Notes |
|---|---|---|
| `room_id` | string | unique |
| `segment` | enum | `SegmentA_Shared` · `SegmentB_Hunter` · `SegmentB_Titan` · `Convergence` |
| `grid` | number | default 20; every coordinate is a multiple |
| `cavity` | `[{x, z, width, height}]` | union = the carved space. At least one |
| `solids` | `[{id, x, z, width, height, is_one_way?, breakable_by?}]` | inside the cavity. `breakable_by` is `Bash` or absent |
| `anchors` | `[{id, x, z}]` | grapple points. Hunter's key |
| `doors` | `[{id, side, at, size, required_tool}]` | `side` is `Left/Right/Top/Bottom`; `at` is the offset along that side |
| `checkpoints` | `[{id, x, z}]` | zero enemies in a checkpoint room |
| `critical_path` | `[id]` | ordered: entry door, the supports between, exit door |
| `pockets` | `[{id, x, z, required_tool, contents}]` | optional, class-exclusive, visible |

`required_tool` is `None`, `Grapple`, `Bash` or `Keycard`.

## `critical_path` is the load-bearing field

It declares the intended route as an ordered list of element ids. Everything not
on it is optional by definition, which is what finally lets the gate tell the
difference between a route and a pocket — and therefore lets it prove the thing
the whole design rests on: **the critical path is passable by both classes on
base movement alone.** See `movement-reach.md` for the bands and
`../01-classes/class-asymmetry-contract.md` for why exclusivity lives off it.

## Example — a room that is not a corridor

An L: a hall with a shaft rising from its right end, a bash pocket sealed behind
the hall's right wall, and a grapple ledge above the top of the shaft.

```json
{
  "room_id": "room_segment_a_bend_01",
  "segment": "SegmentA_Shared",
  "grid": 20,
  "cavity": [
    {"x": 0,    "z": 0,    "width": 2400, "height": 600},
    {"x": 1800, "z": 600,  "width": 600,  "height": 1000},
    {"x": 2400, "z": 0,    "width": 500,  "height": 400}
  ],
  "solids": [
    {"id": "ledge_a",   "x": 400,  "z": 160,  "width": 500, "height": 40, "is_one_way": true},
    {"id": "ledge_b",   "x": 1100, "z": 360,  "width": 500, "height": 40, "is_one_way": true},
    {"id": "shaft_1",   "x": 1840, "z": 560,  "width": 400, "height": 40, "is_one_way": true},
    {"id": "shaft_2",   "x": 1900, "z": 760,  "width": 400, "height": 40, "is_one_way": true},
    {"id": "shaft_3",   "x": 1840, "z": 960,  "width": 400, "height": 40, "is_one_way": true},
    {"id": "shaft_4",   "x": 1900, "z": 1160, "width": 400, "height": 40, "is_one_way": true},
    {"id": "perch",     "x": 1840, "z": 1500, "width": 300, "height": 40, "is_one_way": false},
    {"id": "seal_east", "x": 2400, "z": 0,    "width": 60,  "height": 400, "breakable_by": "Bash"}
  ],
  "anchors": [
    {"id": "anchor_top", "x": 2300, "z": 1560}
  ],
  "doors": [
    {"id": "door_in",  "side": "Left", "at": 0,    "size": 200, "required_tool": "None"},
    {"id": "door_out", "side": "Right", "at": 1200, "size": 200, "required_tool": "None"}
  ],
  "checkpoints": [],
  "critical_path": ["door_in", "ledge_a", "ledge_b", "shaft_1", "shaft_2", "shaft_3", "shaft_4", "door_out"],
  "pockets": [
    {"id": "pocket_high", "x": 2000, "z": 1540, "required_tool": "Grapple", "contents": "LoreCache"},
    {"id": "pocket_east", "x": 2600, "z": 0,    "required_tool": "Bash",    "contents": "HealthCache"}
  ]
}
```

Read the steps against the reach bands. Every rise on the critical path is 200
or under, so both classes make it. `perch` sits 340 above `shaft_4` — far past
the 250 ceiling — so it is Hunter-only, and `anchor_top` is the only way up.
`pocket_east` is sealed by `seal_east`, which the Hunter has no verb to open,
and the hall gives 2400 units of run-up, well past the 250 the bash needs. Both
pockets are in open sight of the critical path.

## What the gate checks

**Structural** — coordinates on the grid; cavity non-empty; every solid, anchor,
door and pocket inside the cavity union; ids unique; `critical_path` referencing
ids that exist and beginning and ending at doors.

**Reach** — consecutive supports on the critical path within the guaranteed
band (≤200 up, ≤380 across). **The cavity floor is a support**: walking along it
is not a gap, and the band applies only where a rise, or a span of open space
with nothing underneath, lies between one support and the next. Then: at least
88 units of run-up before any gap; a breakable wall with its own run-up; an
anchor within 800 units with nothing solid in the line to it.

**Exclusivity and visibility** — no base-movement route into a pocket from the
critical path; an unobstructed sight line to each pocket from somewhere on it.

**Variety, measured across a batch rather than per room** — no two adjacent
rooms sharing a dominant orientation; at least one room with three or more floor
levels; at least one taller than wide and one wider than tall; a mean of two or
more direction changes along the critical path; at most a third of rooms with
doors only on Left and Right.

That last family is what keeps rooms from converging on the shape that is
easiest to emit. It constrains the experience — how much a room makes you turn
and climb — rather than naming shapes, so form stays free.

## Deliberately absent

Hazards, moving platforms, wall-jump surfaces, non-rectilinear geometry, and
room-to-room stitching. Each would cost importer, gate and reviewer work, and
none is needed to show that rooms are spaces rather than corridors.
