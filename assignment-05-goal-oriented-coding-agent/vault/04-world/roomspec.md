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
| `cavity` | `[{id?, x, z, width, height}]` | union = the carved space. At least one. `id` optional, and only needed when the route walks that space's floor |
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

**A space carved above another has no floor of its own.** Carving is subtraction,
so two rectangles stacked in the same column make one tall volume rather than two
rooms with a floor between them: the upper one's lower edge is an open seam.

This is not usually a defect. A chamber stacked on another is a shaft, and a
shaft is *climbed*, not walked — so it is the ledges inside it that belong in
`critical_path`, never the space itself. Name a carved space only where the
player runs along its floor, which means only where that floor rests on rock.

Where a surface really is wanted mid-column, build a solid and put **its** id in
the path. A solid's top is a support; a cavity's floor is only a support where
nothing is carved beneath it.

**A door must sit on the room's outer edge, and open onto carved space.** The
importer punches a doorway through the rock that surrounds the room's bounding
box, and two rooms are placed against each other by those bounds. A door in an
interior wall therefore has its hole cut somewhere the room does not end: it
opens onto whatever lies beyond, which is stone. So the cavity has to reach the
bounding box across the whole opening — if a pocket chamber juts out past the
wall a door is in, that door is not on the outside of the room.

This was invisible while rooms were imported one at a time: an outer wall with no
hole in it is just the edge of the world. It only becomes a defect the moment two
rooms are meant to meet.

**Name a carved space to walk it.** The floor of a cavity rectangle is a surface
like any ledge, but it can only appear in `critical_path` if that rectangle
carries an `id`. Without one, a corridor the player runs the length of cannot be
named, the two ledges at its ends sit next to each other in the path, and the
gate measures the whole room as a single impossible jump. This is what a terrace
is made of, and it was unbuildable until the spaces could be named.

No door on the critical path may require a tool, and no pocket may sit on it.
A traverse key opens a reward or a side room; it never opens the way forward. A
gated route does not make the room harder, it locks one class out of the game.

### Reach is not fit

A jump landing somewhere the body does not fit is not a jump. Three rules follow,
and every room generated before they existed failed at least one of them while
passing every reach check:

- **Headroom.** A surface on the route needs a stretch at least as wide as the
  character with a full character-height of clear space above it. Spacing is
  measured surface to surface, so a ledge eats its own thickness out of the air
  above the one below: ledges 200 apart and 40 thick leave 160 for a 176-tall
  body.
- **No overhang on a climb.** Consecutive steps must not sit one above the other.
  Standing clear of an overhanging ledge means jumping almost straight up, and
  arriving over it costs horizontal travel the jump has no height left to buy.
  A climb is alternating ledges, not stacked ones — which also means a shaft
  narrower than two ledges cannot be climbed by widening the ledges.
- **The numbers come from the character, not from taste.** They are recorded in
  `movement-reach.md` and read from the capsule, so changing the character
  changes the rules rather than silently invalidating them.

⚠️ `is_one_way` currently sets an actor tag and nothing else — no collision
behaviour implements it. Until something does, treat every solid as solid: a
one-way platform overhead blocks a climb exactly like a floor would.

### Vertical space is built from two heights

Heights are not chosen per room. There are two, and multiples of the larger.
Observed in Metroid Dread: main corridors run about two and a half bodies tall,
tighter ones about one and a half, and the tight ones carry fewer and weaker
enemies while making combat more interesting rather than less.

| | height | what it is |
|---|---|---|
| **Tight corridor** | **260** | The jump does not fit. The player cannot go over anything |
| **Standard floor** | **400** | A full jump with room to fight |
| Open space | 800 · 1200 · 1600 | whole multiples of the floor |
| **Half-floor** | **200** | where a standing surface may sit; one landing per floor climbed |

A tight corridor is not merely a low one. A jumping character occupies 301, so at
260 the jump is clipped to 84 and evasion stops being available: combat becomes
spacing. That is the design intent, and it is why the height also decides what
may fight there — see `../02-enemies/enemy-palette-overview.md`.

A tight corridor holds no ledges. A landing at 200 would leave 60 of headroom, so
tight corridors are flat by construction: they are for travel and for fighting,
never for climbing.

The floor is 400 rather than the observed two and a half bodies (440) for one
reason: half of 400 is 200, which is exactly the guaranteed rise. That makes one
landing carry one floor of climb, always. At 440 the half-floor would be 220,
past the guaranteed band, and no climb could sit on the critical path.

The module governs **the carved spaces**, not the clearance left above a ledge:
in a two-floor shaft the space over a landing at 200 is 600, and no arrangement
of standard heights makes that a multiple.

### Rooms have shapes, and a segment uses several

Variety rules that only reject the worst cases do not produce variety. Four rooms
were generated against them and all four came out the same archetype — a corridor
that opens into a climb — and of the nine rooms this project had built by then,
not one descended.

So the shapes are named, and the gate classifies each room by the profile of its
critical path in section:

| Shape | The route |
|---|---|
| **ASCENT** | rises; a shaft climbed by alternating landings |
| **DESCENT** | falls; the player commits downward and the way back is the question |
| **ARCH** | rises to a peak, then falls to leave lower than it entered |
| **BASIN** | drops in, crosses a floor, climbs out |
| **TERRACE** | long runs at each level, joined by a climb at their ends. **The ends must open to standard height**: a tight corridor cannot be left upwards, so a terrace built only of tight corridors has no way between its levels |
| **FLAT** | one level throughout; a corridor or a hall |

A batch may not be all one shape, and consecutive rooms may not repeat one. The
contrast is what the player reads: a descent means nothing after another descent.

Descents deserve their own care. Falling costs nothing and obeys no reach band,
so a route downward is always passable and can silently become one-way. If the
player must be able to return, the climb back is a separate route that the
critical path does not describe — say so in the room's design, or make the exit
lead onward rather than back.

### A climb is a route, not a ladder

Two rooms were built on the standard heights and played. They had the same number
of direction changes and covered the same lateral distance, and one read as
designed while the other read as generic filler. What separated them:

- The generic one **shuffled between two positions**, so the player repeated one
  input and saw the same view from every landing. Four or more steps in a row
  confined to two lanes is refused.
- Every one of its platforms was **the same width**. Width is meaning: a wide
  ledge is a place to stop and fight, a narrow one is a beat of precision. Three
  or more platforms on the route sharing one width is refused.

Counting direction changes is not the same as measuring interest, which is why
neither rule counts them. A climb needs a space wide enough to wander across; a
shaft with room for only two ledges can produce nothing but a ladder.

**The first step up from any surface is a step, not a platform.** Half a floor is
200 and a platform eats 40 of it, leaving 160 under a 176-tall character — a gap
that can be seen and never entered, which reads as an oversight rather than as a
secret. Give it its full height from the surface below and it becomes a plinth.
The gate refuses the alternative: a solid either rests on what is under it, or
leaves enough room to stand there.

## Example — a room that is not a corridor

An L: a hall with a shaft rising from its right end, a bash pocket sealed behind
the hall's right wall, and a grapple ledge above the top of the shaft.

```json
{
  "room_id": "room_segment_a_bend_01",
  "segment": "SegmentA_Shared",
  "grid": 20,
  "cavity": [
    {"x": 0,    "z": 0,   "width": 2400, "height": 800},
    {"x": 1200, "z": 800, "width": 1700, "height": 800},
    {"x": 2400, "z": 0,   "width": 500,  "height": 400}
  ],
  "solids": [
    {"id": "ledge_a",   "x": 400,  "z": 0,    "width": 500, "height": 200},
    {"id": "ledge_b",   "x": 1100, "z": 360,  "width": 500, "height": 40, "is_one_way": true},
    {"id": "shaft_1",   "x": 1700, "z": 560,  "width": 420, "height": 40, "is_one_way": true},
    {"id": "shaft_2",   "x": 1220, "z": 760,  "width": 420, "height": 40, "is_one_way": true},
    {"id": "shaft_3",   "x": 1800, "z": 960,  "width": 300, "height": 40, "is_one_way": true},
    {"id": "shaft_4",   "x": 2140, "z": 1160, "width": 760, "height": 40, "is_one_way": true},
    {"id": "perch",     "x": 1800, "z": 1500, "width": 300, "height": 40},
    {"id": "seal_east", "x": 2400, "z": 0,    "width": 60,  "height": 400, "breakable_by": "Bash"}
  ],
  "anchors": [
    {"id": "anchor_top", "x": 2300, "z": 1560}
  ],
  "doors": [
    {"id": "door_in",  "side": "Left",  "at": 0,    "size": 200, "required_tool": "None"},
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
