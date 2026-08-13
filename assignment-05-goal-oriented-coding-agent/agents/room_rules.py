#!/usr/bin/env python3
"""Geometry rules for RoomSpec. Pure functions, stdlib only, no I/O.

The countable half of room review. Everything here answers a question that used
to come back from the semantic reviewer as "needs an in-engine check" — can the
character make this step, is that pocket actually exclusive, can the player see
it — and answers it with arithmetic instead.

The contract these rules enforce is `vault/04-world/roomspec.md`; the distances
come from `vault/04-world/movement-reach.md`, where each one is recorded as
measured or as judgment. They are constants here rather than parsed prose, so
they must be updated together with that note.
"""

from typing import Dict, Iterable, List, Optional, Tuple

# --- Reach, from vault/04-world/movement-reach.md ---------------------------
RISE_GUARANTEED = 200      # both classes, no timing demanded
RISE_SKILL = 250           # measured ceiling of a perfectly timed double jump
GAP_GUARANTEED = 380
GAP_SKILL = 730            # measured ceiling at full run speed
RUNUP_MIN = 88             # floor needed to reach full speed from rest
BASH_RUNUP = 250           # vault/04-world/junction-and-gates.md [TUNE]
GRAPPLE_RANGE = 800        # vault/04-world/junction-and-gates.md

# The rock a room carries around its cavity. Two joined rooms share one of these
# rather than each keeping its own, so it is what separates their cavities.
# Mirrors ROCK_MARGIN in the importer's room_geometry; they move together.
ROCK_MARGIN = 200.0

# --- The body, read from BP_GreyBoxCharacter's capsule ---------------------
# Reach says how far the character can go. These say whether it fits when it
# gets there, which is a different question and was not being asked: a room
# whose platforms sat exactly RISE_GUARANTEED apart passed every reach rule and
# could not be climbed, because 200 of spacing minus a 40-thick ledge leaves 160
# of air for a 176-tall body.
CAPSULE_HEIGHT = 176.0     # CapsuleHalfHeight 88, doubled
CAPSULE_RADIUS = 34.0
MAX_STEP = 45.0            # CharacterMovement MaxStepHeight
HEADROOM = 200.0           # the body plus room to move in it [TUNE]

JUMP_APEX = 125.0                              # single jump, measured
JUMPING_HEIGHT = CAPSULE_HEIGHT + JUMP_APEX    # 301: the space a jump needs

# --- Standard heights ------------------------------------------------------
# Vertical space is built from two named heights rather than chosen freely.
# Observed in Metroid Dread: main corridors run about 2.5 bodies tall and
# tighter ones about 1.5, with the tight ones carrying fewer and weaker enemies.
# The reason that reads as claustrophobia is exact — a tight corridor is one
# where a full jump does not fit, so the player cannot go over anything and
# combat becomes spacing rather than evasion.
#
# FLOOR is 400 rather than the observed 2.5 bodies (440) for one reason: half of
# it is 200, which is exactly the guaranteed rise. That makes one landing per
# floor climbed, always reachable. At 440 the half-floor would be 220 and every
# climb would sit outside the guaranteed band, which the critical path forbids.
FLOOR = 400.0              # standard: a full jump plus room to fight, 2.27 bodies
HALF_FLOOR = 200.0         # == RISE_GUARANTEED; the climbing module
TIGHT = 260.0              # 1.48 bodies; the jump is clipped to 84 [TUNE]

# A Shieldbearer is passed over or through, which needs the space to hop.
SHIELDBEARER_HEADROOM = 300.0

EPS = 1e-6
WALK_CLEARANCE = 40.0   # a line of sight or of travel runs above the floor,
                        # not scraping it — otherwise a wall standing on that
                        # floor is missed by every test that grazes its base.

# A support is a horizontal surface the character can stand on:
#   (x0, x1, z, source_id)
Support = Tuple[float, float, float, str]


# --------------------------------------------------------------------------
# Cavity
# --------------------------------------------------------------------------
def in_cavity(cavity: List[Dict], x: float, z: float) -> bool:
    return any(c["x"] - EPS <= x <= c["x"] + c["width"] + EPS
               and c["z"] - EPS <= z <= c["z"] + c["height"] + EPS
               for c in cavity)


def box_in_cavity(cavity: List[Dict], b: Dict, samples: int = 8) -> bool:
    """Sample the whole box, not just its corners.

    A box can have both corners inside two different cavity rectangles while
    its middle sits in rock — which is exactly how a sealing wall ends up
    embedded in stone instead of across the passage it seals.
    """
    xs = [b["x"] + b["width"] * i / samples for i in range(samples + 1)]
    zs = [b["z"] + b["height"] * i / samples for i in range(samples + 1)]
    return all(in_cavity(cavity, x, z) for x in xs for z in zs)


def cavity_bounds(cavity: List[Dict]) -> Dict[str, float]:
    """The camera bounds, computed rather than declared."""
    return {
        "min_x": min(c["x"] for c in cavity),
        "max_x": max(c["x"] + c["width"] for c in cavity),
        "min_z": min(c["z"] for c in cavity),
        "max_z": max(c["z"] + c["height"] for c in cavity),
    }


# --------------------------------------------------------------------------
# Supports
# --------------------------------------------------------------------------
def floor_spans(cavity: List[Dict], step: float = 20.0) -> List[Support]:
    """The cavity's own floor, where it is floor.

    A cavity rectangle's bottom edge is only floor where no other cavity sits
    directly beneath it — otherwise it is the open seam between two carved
    volumes, and walking off it means falling through.
    """
    spans: List[Support] = []
    for i, c in enumerate(cavity):
        # A carved space may name itself, and then the route can walk it. Without
        # that, a corridor the player runs the length of cannot appear in the
        # critical path at all, and the two ledges at its ends read as one
        # impossible jump across the room.
        label = c.get("id") or f"floor[{i}]"
        x, run_start = c["x"], None
        while x <= c["x"] + c["width"] + EPS:
            solid_below = not in_cavity(cavity, x, c["z"] - step / 2)
            if solid_below and run_start is None:
                run_start = x
            elif not solid_below and run_start is not None:
                spans.append((run_start, x, c["z"], label))
                run_start = None
            x += step
        if run_start is not None:
            spans.append((run_start, c["x"] + c["width"], c["z"], label))
    return [s for s in spans if s[1] - s[0] > EPS]


def solid_tops(solids: List[Dict]) -> List[Support]:
    """Every solid's upper surface. A breakable wall is not stood on."""
    return [(s["x"], s["x"] + s["width"], s["z"] + s["height"], s["id"])
            for s in solids if not s.get("breakable_by")]


def _walls_at(spec: Dict, x: float, z: float) -> bool:
    """Whether something stands at x that the character cannot step over."""
    for s in spec.get("solids") or []:
        if s["x"] - EPS <= x <= s["x"] + s.get("width", 0) + EPS \
                and s["z"] <= z + EPS \
                and s["z"] + s.get("height", 0) > z + MAX_STEP + EPS:
            return True
    return False


def split_floors(spec: Dict, spans: List[Support]) -> List[Support]:
    """Cut a floor wherever something stands on it that cannot be stepped over.

    A floor run comes from the cavity, which knows nothing about what was put
    back inside it. A four-hundred-tall block in the middle of a hall makes two
    halls, and without this the gate saw one continuous surface: a route could
    step onto the far side of a wall it had no way past, and did.
    """
    out: List[Support] = []
    for x0, x1, z, label in spans:
        cuts = []
        for s in spec.get("solids") or []:
            if s["z"] > z + MAX_STEP + EPS:                       # not resting here
                continue
            if s["z"] + s.get("height", 0) <= z + MAX_STEP + EPS:  # a lip, walked over
                continue
            a, b = s["x"], s["x"] + s.get("width", 0)
            if b <= x0 + EPS or a >= x1 - EPS:
                continue
            cuts.append((max(a, x0), min(b, x1)))
        cur = x0
        for a, b in sorted(cuts):
            if a - cur > EPS:
                out.append((cur, a, z, label))
            cur = max(cur, b)
        if x1 - cur > EPS:
            out.append((cur, x1, z, label))
    return out


def merge_floors(spec: Dict, spans: List[Support]) -> List[Support]:
    """Join floor runs that meet at the same height with nothing between them.

    The cavity is a union, so a hall, a tight corridor and a shaft standing side
    by side produce three rectangles and one floor. Left separate, they invent a
    gap the width of a room between two points the character simply walks
    between — which is what rooms built from standard heights look like.

    Runs are not joined across a wall. A sealed chamber shares the floor's
    height and touches it, and merging through the seal would make a pocket
    reachable on foot.
    """
    merged: List[Support] = []
    for span in sorted(spans, key=lambda s: (s[2], s[0])):
        if merged and abs(merged[-1][2] - span[2]) < EPS and span[0] <= merged[-1][1] + EPS \
                and not _walls_at(spec, span[0], span[2]):
            last = merged[-1]
            merged[-1] = (last[0], max(last[1], span[1]), last[2], last[3])
        else:
            merged.append(span)
    return merged


def all_supports(spec: Dict) -> List[Support]:
    return merge_floors(spec, split_floors(spec, floor_spans(spec["cavity"]))) \
        + solid_tops(spec.get("solids") or [])


# --------------------------------------------------------------------------
# Headroom — whether the body fits where the jump can reach
# --------------------------------------------------------------------------
def in_solid(spec: Dict, x: float, z: float, ignore: Iterable[str] = ()) -> Optional[Dict]:
    """The solid occupying this point, if any."""
    skip = set(ignore)
    for s in spec.get("solids") or []:
        if s.get("id") in skip:
            continue
        if (s["x"] - EPS <= x <= s["x"] + s.get("width", 0) + EPS
                and s["z"] - EPS <= z <= s["z"] + s.get("height", 0) + EPS):
            return s
    return None


def headroom(spec: Dict, support: Support, limit: float = 400.0,
             step: float = 10.0, samples: int = 5) -> float:
    """Free vertical space above a surface the character stands on.

    Probed by sampling upward rather than computed from rectangle algebra,
    because the cavity is a union of overlapping boxes and its ceiling above a
    given span is not a single number.

    A one-way platform counts as a ceiling. It can be passed through from below,
    but a surface whose headroom is another platform is not a place the player
    can stand and act — which is what a support on the route has to be.
    """
    x0, x1, z = support[0], support[1], support[2]
    sid = support[3] if len(support) > 3 else None
    cavity = spec.get("cavity") or []

    # Probe across the span, inset by the body's own radius: at the very edge a
    # neighbouring wall's face reads as a ceiling the character never meets.
    width = x1 - x0
    if width > EPS:
        inset = min(CAPSULE_RADIUS, width / 2.0 - EPS)
        lo, hi = x0 + inset, x1 - inset
        xs = [lo + (hi - lo) * i / (samples - 1) for i in range(samples)] if samples > 1 else [lo]
    else:
        xs = [x0]

    # Solids are computed exactly. Their edges are known numbers, and probing
    # for them would report the answer rounded down to the probe step — a lie
    # small enough to be believed.
    lo, hi = min(xs), max(xs)
    clear = limit
    for s in spec.get("solids") or []:
        if s.get("id") == sid:
            continue
        if s["x"] + s.get("width", 0) <= lo + EPS or s["x"] >= hi - EPS:
            continue
        if s["z"] < z + EPS:
            continue
        clear = min(clear, s["z"] - z)

    # The cavity ceiling is probed, because the cavity is a union of overlapping
    # boxes and the ceiling above a span is not a single number.
    probed = 0.0
    while probed + step <= min(clear, limit):
        if any(not in_cavity(cavity, x, z + probed + step) for x in xs):
            return probed
        probed += step
    return min(clear, limit)


def standable_intervals(spec: Dict, support: Support, needed: Optional[float] = None,
                        step: float = 10.0) -> List[Tuple[float, float]]:
    """The stretches of a surface the body fits above, in order.

    Having somewhere to stand is not the same as being able to walk from one end
    to the other. A ledge hanging low over a corridor leaves the floor on both
    sides perfectly standable and the way through blocked, and a rule that asks
    only for the longest clear stretch is satisfied by the larger side.
    """
    needed = HEADROOM if needed is None else needed
    x0, x1, z = support[0], support[1], support[2]
    sid = support[3] if len(support) > 3 else None

    out: List[Tuple[float, float]] = []
    start = None
    x = x0
    while x <= x1 + EPS:
        blocked = not in_cavity(spec.get("cavity") or [], x, z + needed)
        if not blocked:
            for s in spec.get("solids") or []:
                if s.get("id") == sid or s["z"] < z + EPS:
                    continue
                if (s["x"] - EPS <= x <= s["x"] + s.get("width", 0) + EPS
                        and s["z"] - z < needed - EPS):
                    blocked = True
                    break
        if blocked:
            if start is not None:
                out.append((start, x - step))
                start = None
        elif start is None:
            start = x
        x += step
    if start is not None:
        out.append((start, x1))
    return out


def same_interval(intervals: Iterable[Tuple[float, float]], a: float, b: float) -> bool:
    """Whether two points on a surface are joined by unbroken standing room."""
    lo, hi = (a, b) if a <= b else (b, a)
    return any(i[0] - EPS <= lo and hi <= i[1] + EPS for i in intervals)


def takeoff_point(a: Support, b: Support, from_x: Optional[float] = None) -> float:
    """Where on `a` the character leaves for `b`, having arrived at `from_x`.

    Not the point under `b`: to climb onto a ledge you stand beside its
    footprint, not beneath it. So when `b` sits higher and overlaps `a`, the
    take-off is pulled back clear of its edge by the body's own radius — on the
    side the character is coming from. Which side that is cannot be decided from
    the two shapes alone: the same ledge is approached from the left in one room
    and from the right in another, and guessing sends the route under it.
    """
    if b[1] < a[0]:
        return a[0]
    if b[0] > a[1]:
        return a[1]
    if b[2] > a[2] + EPS:                       # a climb onto something overhead
        origin = a[0] if from_x is None else from_x
        near_left = abs(origin - b[0]) <= abs(origin - b[1])
        edge = b[0] - CAPSULE_RADIUS if near_left else b[1] + CAPSULE_RADIUS
        return min(max(edge, a[0]), a[1])
    return min(max(b[0], a[0]), a[1])


def landing_point(a: Support, b: Support, from_x: Optional[float] = None) -> float:
    """Where on `b` the character arrives from `a`."""
    return min(max(takeoff_point(a, b, from_x), b[0]), b[1])


def rise_available(spec: Dict, x: float, z: float) -> float:
    """How far the character can climb from here before its head is stopped.

    A low ceiling does not only block walking. Standing under one, the jump is
    clipped to whatever is left above the body, which is why a tight corridor
    cannot be left upwards however close the ledge above it is.
    """
    return clear_above(spec, x, z) - CAPSULE_HEIGHT


def standable_run(spec: Dict, support: Support, needed: Optional[float] = None,
                  step: float = 10.0) -> float:
    """The widest continuous stretch of this surface the body fits above.

    Asked as a width rather than a yes/no because part of a ledge being covered
    is normal — what matters is whether the uncovered part is wide enough to
    stand in.
    """
    needed = HEADROOM if needed is None else needed
    x0, x1, z = support[0], support[1], support[2]
    sid = support[3] if len(support) > 3 else None
    cavity = spec.get("cavity") or []

    best = run = 0.0
    x = x0
    while x <= x1 + EPS:
        blocked = not in_cavity(cavity, x, z + needed)
        if not blocked:
            for s in spec.get("solids") or []:
                if s.get("id") == sid or s["z"] < z + EPS:
                    continue
                if (s["x"] - EPS <= x <= s["x"] + s.get("width", 0) + EPS
                        and s["z"] - z < needed - EPS):
                    blocked = True
                    break
        run = 0.0 if blocked else run + step
        best = max(best, run)
        x += step
    return best


def height_class(clear: float, tol: float = EPS) -> Optional[str]:
    """Name the standard height a clear space matches, or None if it matches none.

    Two named heights and multiples of the standard. Anything between them is
    refused rather than rounded: the point of the module is that a player learns
    what one floor means and can judge a room by eye, and a height that is
    nearly standard teaches nothing except that heights are arbitrary.
    """
    if abs(clear - TIGHT) <= tol:
        return "tight"
    if clear >= FLOOR - tol:
        floors = clear / FLOOR
        if abs(floors - round(floors)) * FLOOR <= tol:
            n = int(round(floors))
            return "standard" if n == 1 else f"open x{n}"
    return None


def on_half_floor(z: float, tol: float = EPS) -> bool:
    """Whether a standing surface sits on the climbing module."""
    return abs(z / HALF_FLOOR - round(z / HALF_FLOOR)) * HALF_FLOOR <= tol


def clear_above(spec: Dict, x: float, z: float, limit: float = 4000.0,
                step: float = 10.0) -> float:
    """Clear height over a point: to the first solid, or out of the cavity."""
    cavity = spec.get("cavity") or []
    best = limit
    for s in spec.get("solids") or []:
        if s["x"] - EPS <= x <= s["x"] + s.get("width", 0) + EPS and s["z"] >= z - EPS:
            best = min(best, s["z"] - z)
    probed = 0.0
    while probed + step <= min(best, limit):
        if not in_cavity(cavity, x, z + probed + step):
            return probed
        probed += step
    return min(best, limit)


def surface_under(spec: Dict, solid: Dict, samples: int = 5) -> float:
    """The highest thing the character could stand on beneath a solid.

    The cavity floor unless another solid is in the way, sampled across the
    footprint and taking the highest, since that is what shortens the space.
    """
    x0, x1 = solid["x"], solid["x"] + solid.get("width", 0)
    floor = min((c["z"] for c in (spec.get("cavity") or [])
                 if c["x"] < x1 and c["x"] + c["width"] > x0), default=0.0)
    best = floor
    for i in range(samples):
        x = x0 + (x1 - x0) * i / max(samples - 1, 1)
        for o in spec.get("solids") or []:
            if o.get("id") == solid.get("id"):
                continue
            if o["x"] - EPS <= x <= o["x"] + o.get("width", 0) + EPS \
                    and o["z"] + o.get("height", 0) <= solid["z"] + EPS:
                best = max(best, o["z"] + o.get("height", 0))
    return best


def dead_space_under(spec: Dict, solid: Dict) -> float:
    """Height of the gap beneath a solid, when that gap is too small to enter.

    Returns 0 when the solid rests on what is below it, and 0 when the space is
    big enough to stand in. Anything between is a hole the player can see and
    never reach, which reads as an oversight rather than as a secret.

    A ledge half a floor above the surface below always lands here: half a floor
    is 200 and the platform eats 40 of it, leaving 160 for a 176-tall body. At
    ground level that is the first step of every climb, so it is the case a
    designer meets first — but the arithmetic is the same anywhere.
    """
    gap = solid["z"] - surface_under(spec, solid)
    return gap if EPS < gap < HEADROOM - EPS else 0.0


def overhangs(a: Dict, b: Dict) -> float:
    """How much of solid b sits horizontally over solid a."""
    return min(a["x"] + a.get("width", 0), b["x"] + b.get("width", 0)) - max(a["x"], b["x"])


def climb_is_threaded(spec: Dict, a: Support, b: Support) -> Optional[float]:
    """Overlap width when b sits above a and covers it, else None.

    A platform directly over the one being jumped from turns the climb into
    threading the body through the space between them. That space is the rise
    minus the upper platform's thickness, so for any rise the character can
    actually make it is smaller than the character. Alternating ledges left and
    right is not a stylistic preference; it is the only shape that works.

    One-way platforms would change this, by letting the body pass through from
    below. Nothing in the project implements them — `is_one_way` currently sets
    an actor tag and no collision behaviour — so they are counted as solid.
    """
    if b[2] <= a[2] + EPS:
        return None
    ax0, ax1 = a[0], a[1]
    bx0, bx1 = b[0], b[1]
    overlap = min(ax1, bx1) - max(ax0, bx0)
    return overlap if overlap > EPS else None


def support_of(spec: Dict, element_id: str) -> Optional[Support]:
    """Resolve a critical-path element to the surface it stands on."""
    for s in all_supports(spec):
        if s[3] == element_id:
            return s

    # A named space whose floor merged into a neighbour's keeps no label of its
    # own, because merging takes the first id and drops the rest. Name a corridor
    # that touches a chamber and the name vanishes, so look the space up among
    # the unmerged runs and hand back the whole contiguous floor it belongs to —
    # which is what the player walks anyway.
    for raw in split_floors(spec, floor_spans(spec["cavity"])):
        if raw[3] != element_id:
            continue
        for merged in merge_floors(spec, split_floors(spec, floor_spans(spec["cavity"]))):
            if abs(merged[2] - raw[2]) < EPS \
                    and merged[0] - EPS <= raw[0] and raw[1] <= merged[1] + EPS:
                return merged
        return raw
    for d in spec.get("doors") or []:
        if d["id"] != element_id:
            continue
        return door_support(spec, d)
    return None


def door_wall(spec: Dict, door: Dict) -> Optional[float]:
    """The coordinate of the wall a door is in, taken from the space at its own
    height rather than from the room's outer bound.

    A chamber hanging off one end moves that bound without moving any wall a
    door could be in, so using it puts the door somewhere the room does not have.
    """
    side, at = door.get("side"), door.get("at", 0)
    if side in ("Left", "Right"):
        here = [c for c in spec["cavity"]
                if c["z"] - EPS <= at < c["z"] + c["height"] - EPS]
        if not here:
            return None
        return min(c["x"] for c in here) if side == "Left" \
            else max(c["x"] + c["width"] for c in here)
    here = [c for c in spec["cavity"]
            if c["x"] - EPS <= at < c["x"] + c["width"] - EPS]
    if not here:
        return None
    return min(c["z"] for c in here) if side == "Bottom" \
        else max(c["z"] + c["height"] for c in here)


def door_opens_onto_cavity(spec: Dict, door: Dict, samples: int = 5) -> bool:
    """Whether the space immediately inside a door is carved.

    The most elementary thing a door must be, and the last one to be checked.
    A doorway is punched through the room's outer rock at import, so a door in a
    wall the cavity does not reach opens onto stone: the hole is real, the room
    behind it is not, and two rooms joined there meet through a plug of rock.
    """
    side, at = door.get("side"), door.get("at", 0)
    size = door.get("size", 200)
    # The room's OUTER bound, not the wall local to the door's height: the
    # importer punches the doorway through the rock that surrounds the room, and
    # two rooms are placed against each other by their outer bounds. A door in
    # an interior wall opens into whatever the room has beyond it.
    b = cavity_bounds(spec["cavity"])
    wall = {"Left": b["min_x"], "Right": b["max_x"],
            "Bottom": b["min_z"], "Top": b["max_z"]}.get(side)
    if wall is None:
        return False
    inset = 20.0
    for i in range(samples):
        t = at + size * (i + 0.5) / samples
        if side == "Left":
            x, z = wall + inset, t
        elif side == "Right":
            x, z = wall - inset, t
        elif side == "Bottom":
            x, z = t, wall + inset
        elif side == "Top":
            x, z = t, wall - inset
        else:
            return False
        if not in_cavity(spec["cavity"], x, z):
            return False
    return True


def door_support(spec: Dict, door: Dict) -> Optional[Support]:
    """A door resolves to the surface it opens onto, not to a point in a wall.

    Walking in from a doorway is walking, so the floor beyond it is the support
    the path continues from. Treating the doorway itself as a zero-width perch
    invents a gap the width of the room and a run-up of nothing.
    """
    side = door.get("side")
    if side not in ("Left", "Right"):
        # A door in the ceiling or the floor is a sill at that wall, reached by
        # climbing to it. Taking the first surface that happens to span the same
        # x returned the room's floor for a ceiling exit, and the route then
        # measured the height of the whole room as a fall out of the top of it.
        at, size = door["at"], door.get("size", 200)
        b = cavity_bounds(spec["cavity"])
        wall = b["max_z"] if side == "Top" else b["min_z"]
        for s in all_supports(spec):
            if s[0] - EPS <= at <= s[1] + EPS and abs(s[2] - wall) <= CAPSULE_RADIUS:
                return s
        return (at, at + size, wall, door["id"])

    # A side door opens at a height *in a particular wall*. Matching on height
    # alone let an exit in the right wall resolve to a ledge on the far left of
    # the room: the path then reported a step of zero to a door it never reached.
    # The wall is the one belonging to the space at the door's height, not the
    # room's outer bound: a chamber hanging off one end moves that bound without
    # moving any wall the door could be in.
    at = door["at"]
    # Half-open in z on purpose. A chamber whose ceiling is exactly the door's
    # height is not a space at that height — you are standing on its roof — and
    # counting it pushed the wall out to a side chamber's far edge, inventing a
    # gap between a correctly placed exit platform and its door.
    here = [c for c in spec["cavity"]
            if c["z"] - EPS <= at < c["z"] + c["height"] - EPS]
    if not here:
        return None
    wall = min(c["x"] for c in here) if side == "Left" \
        else max(c["x"] + c["width"] for c in here)
    for s in all_supports(spec):
        if abs(s[2] - door["at"]) >= EPS:
            continue
        edge = s[0] if side == "Left" else s[1]
        if abs(edge - wall) <= CAPSULE_RADIUS:
            return s

    # Nothing in the room reaches that wall at that height — but a doorway has
    # a floor of its own, so the door is a surface even when no ledge meets it.
    # Standing it up here turns "nothing reaches this wall", which a designer
    # cannot act on, into an ordinary reach step measured in numbers: how far
    # the last ledge is from the door, and how far below it.
    body = 2 * CAPSULE_RADIUS
    return (wall, wall + body, door["at"], door["id"]) if side == "Left" \
        else (wall - body, wall, door["at"], door["id"])


# --------------------------------------------------------------------------
# Stepping between supports
# --------------------------------------------------------------------------
def gap_between(a: Support, b: Support) -> float:
    """Horizontal clearance. Overlapping spans mean no gap — the character can
    stand under the target before jumping."""
    return max(0.0, b[0] - a[1], a[0] - b[1])


def step_fits(a: Support, b: Support, rise_max: float, gap_max: float) -> bool:
    rise = b[2] - a[2]
    if rise > rise_max:
        return False
    return gap_between(a, b) <= gap_max


def blocked_between(spec: Dict, a: Support, b: Support) -> bool:
    """A wall standing between two surfaces stops the walk, breakable or not.

    Without this, a chamber sealed behind cracked stone reads as reachable
    simply because the floor on both sides is at the same height.
    """
    ax = (a[0] + a[1]) / 2 if a[1] > a[0] else a[0]
    bx = (b[0] + b[1]) / 2 if b[1] > b[0] else b[0]
    return not clear_line(spec, ax, a[2] + WALK_CLEARANCE, bx, b[2] + WALK_CLEARANCE,
                          ignore=(a[3], b[3]))


def reachable_from(spec: Dict, seeds: List[Support],
                   rise_max: float, gap_max: float) -> List[Support]:
    """Every support the character can work its way to. Breadth-first, because
    a pocket two easy hops off the route is not exclusive however far it looks."""
    supports = all_supports(spec)
    seen = {s[3] + f"@{s[2]}" for s in seeds}
    frontier, out = list(seeds), list(seeds)
    while frontier:
        current = frontier.pop()
        for s in supports:
            key = s[3] + f"@{s[2]}"
            if key in seen:
                continue
            # step_fits already allows a negative rise, so dropping is covered.
            # Testing the reverse direction as well would make every surface
            # mutually reachable and no pocket would ever read as exclusive.
            if step_fits(current, s, rise_max, gap_max) and not blocked_between(spec, current, s):
                seen.add(key)
                frontier.append(s)
                out.append(s)
    return out


# --------------------------------------------------------------------------
# Sight
# --------------------------------------------------------------------------
def clear_line(spec: Dict, ax: float, az: float, bx: float, bz: float,
               samples: int = 64, ignore: Iterable[str] = ()) -> bool:
    """Nothing solid between the two points: inside the cavity the whole way,
    and never inside a solid.

    `ignore` drops solids from the test, for the case where a solid *is* an
    endpoint rather than an obstacle. Every line to a cracked wall ends inside
    it, and every route onto a ledge passes through the ledge — an obstacle test
    that counts its own endpoints finds the world impassable.
    """
    skip = {ignore} if isinstance(ignore, str) else set(ignore)
    solids = [s for s in (spec.get("solids") or []) if s.get("id") not in skip]
    for i in range(samples + 1):
        t = i / samples
        x, z = ax + (bx - ax) * t, az + (bz - az) * t
        if not in_cavity(spec["cavity"], x, z):
            return False
        for s in solids:
            if (s["x"] + EPS < x < s["x"] + s["width"] - EPS
                    and s["z"] + EPS < z < s["z"] + s["height"] - EPS):
                return False
    return True


def visible_from(spec: Dict, supports: List[Support], tx: float, tz: float,
                 samples: int = 5, ignore: Iterable[str] = ()) -> bool:
    """Can the target be seen from anywhere along these surfaces?

    Sampled across each span rather than from its midpoint: the player walks,
    and something hidden from one spot is often in plain view two steps along.
    """
    for s in supports:
        for i in range(samples + 1):
            x = s[0] + (s[1] - s[0]) * i / samples
            skip = ({ignore} if isinstance(ignore, str) else set(ignore)) | {s[3]}
            if clear_line(spec, x, s[2] + WALK_CLEARANCE, tx, tz, ignore=skip):
                return True
    return False


# --------------------------------------------------------------------------
# Shape, for the batch-level variety rules
# --------------------------------------------------------------------------
def floor_levels(spec: Dict) -> int:
    """Distinct heights the character can stand at."""
    return len({round(s[2], 3) for s in all_supports(spec)})


def aspect(spec: Dict) -> float:
    b = cavity_bounds(spec["cavity"])
    height = b["max_z"] - b["min_z"]
    return (b["max_x"] - b["min_x"]) / height if height else float("inf")


def direction_changes(spec: Dict) -> int:
    """How many times the critical path reverses horizontally. A corridor
    scores zero; that is the whole point of measuring it."""
    xs = []
    for eid in spec.get("critical_path") or []:
        s = support_of(spec, eid)
        if s:
            xs.append((s[0] + s[1]) / 2)
    changes, last = 0, 0
    for a, b in zip(xs, xs[1:]):
        d = (b > a) - (b < a)
        if d and last and d != last:
            changes += 1
        if d:
            last = d
    return changes


def ascent_lanes(spec: Dict) -> List[float]:
    """Where each step of the route stands, doors excluded.

    Two landings count as the same lane when their centres are within a body
    width of each other, since a shift smaller than the character is not a shift
    the player travels.
    """
    door_ids = {d.get("id") for d in spec.get("doors") or []}
    lanes: List[float] = []
    for eid in spec.get("critical_path") or []:
        if eid in door_ids:
            continue
        s = support_of(spec, eid)
        if s:
            lanes.append((s[0] + s[1]) / 2)
    return lanes


def longest_two_lane_run(lanes: Iterable[float], tol: Optional[float] = None) -> int:
    """The longest stretch of the route that shuffles between two positions.

    A climb alternating between two lanes is a ladder: the player repeats one
    input and the room stops being a place. Measured because it is what actually
    separated a climb that read as designed from one that read as generic —
    both had the same number of direction changes and covered the same distance.
    """
    tol = 2 * CAPSULE_RADIUS if tol is None else tol
    lanes = list(lanes)
    best = 0
    for start in range(len(lanes)):
        seen: List[float] = []
        for end in range(start, len(lanes)):
            x = lanes[end]
            if not any(abs(x - s) <= tol for s in seen):
                seen.append(x)
            if len(seen) > 2:
                break
            best = max(best, end - start + 1)
    return best


OPPOSITE = {"Left": "Right", "Right": "Left", "Top": "Bottom", "Bottom": "Top"}


def end_doors(spec: Dict) -> Tuple[Optional[Dict], Optional[Dict]]:
    """The doors the route enters and leaves by, in that order."""
    path = spec.get("critical_path") or []
    doors = {d.get("id"): d for d in (spec.get("doors") or [])}
    return (doors.get(path[0]) if path else None,
            doors.get(path[-1]) if len(path) > 1 else None)


def connection(a: Dict, b: Dict) -> Tuple[Optional[Tuple[float, float]], str]:
    """Where b must be placed for its entrance to meet a's exit, or why it cannot.

    A room is authored at its own origin and carries no world position, so
    joining two of them is arithmetic on their doors rather than a field either
    one declares. What has to agree is the pair of walls and the size of the
    opening; the difference in height is absorbed by the placement, provided it
    lands on the climbing module so that the two rooms' floors stay in step.
    """
    _, exit_door = end_doors(a)
    entry_door, _ = end_doors(b)
    if exit_door is None or entry_door is None:
        return None, "one of the rooms does not name its doors on the critical path"

    side_a, side_b = exit_door.get("side"), entry_door.get("side")
    if OPPOSITE.get(side_a) != side_b:
        return None, (f"the exit is in the {side_a} wall and the entrance in the {side_b}; "
                      f"they meet only across facing walls, so this exit needs a "
                      f"{OPPOSITE.get(side_a)} entrance")
    if exit_door.get("size") != entry_door.get("size"):
        return None, (f"the openings differ: {exit_door.get('size')} against "
                      f"{entry_door.get('size')}")

    # The two rooms share one wall rather than touching cavity to cavity. Each
    # carries its own rock margin, so placing B's cavity where A's ends buries
    # each room's edge in the other's stone and leaves the two doorways carved
    # through different walls — open at both ends, joined to nothing.
    ba, bb = cavity_bounds(a["cavity"]), cavity_bounds(b["cavity"])
    wall = ROCK_MARGIN
    if side_a in ("Left", "Right"):
        dx = (ba["max_x"] + wall - bb["min_x"]) if side_a == "Right" \
            else (ba["min_x"] - wall - bb["max_x"])
        dz = exit_door["at"] - entry_door["at"]
        step = HALF_FLOOR
    else:
        dx = exit_door["at"] - entry_door["at"]
        dz = (ba["max_z"] + wall - bb["min_z"]) if side_a == "Top" \
            else (ba["min_z"] - wall - bb["max_z"])
        step = HALF_FLOOR
    off = dz if side_a in ("Left", "Right") else dx
    if abs(off / step - round(off / step)) * step > EPS:
        return None, (f"joining them offsets the second room by {off:g}, which is not a multiple "
                      f"of the {step:g} module, so the two rooms' surfaces would not line up")
    return (dx, dz), ""


def path_profile(spec: Dict) -> str:
    """The shape of the route in section, as one of a small vocabulary.

    Variety rules that only reject the worst cases do not produce variety: four
    rooms were generated against them and all four came out the same archetype,
    a corridor opening into a climb. Naming the shapes makes sameness countable,
    and gives a designer something to be asked for.

    ASCENT   the route rises          DESCENT  it falls
    ARCH     rises, then falls        BASIN    falls, then rises
    TERRACE  long runs at each level, joined at their ends
    FLAT     one level throughout
    """
    zs = []
    for eid in spec.get("critical_path") or []:
        s = support_of(spec, eid)
        if s:
            zs.append(s[2])
    if len(zs) < 2:
        return "FLAT"

    tol = FLOOR / 2.0
    peak, trough = max(zs), min(zs)
    ends_hi, ends_lo = max(zs[0], zs[-1]), min(zs[0], zs[-1])
    if peak - ends_hi > tol:
        return "ARCH"
    if ends_lo - trough > tol:
        return "BASIN"

    net = zs[-1] - zs[0]
    if abs(net) <= tol:
        return "FLAT"

    # A climb up a shaft and a series of stacked corridors both rise. What
    # separates them is how far the player walks between level changes.
    runs, changes = [], 0
    for eid in spec.get("critical_path") or []:
        s = support_of(spec, eid)
        if s:
            runs.append(s[1] - s[0])
    for a, b in zip(zs, zs[1:]):
        if abs(b - a) > EPS:
            changes += 1
    if changes and (sum(runs) / changes) > 3 * GAP_GUARANTEED:
        return "TERRACE"
    return "ASCENT" if net > 0 else "DESCENT"


def door_sides(spec: Dict) -> set:
    return {d["side"] for d in spec.get("doors") or []}


def dominant_orientation(spec: Dict) -> str:
    """Only for the adjacency rule, which asks whether two rooms feel alike.

    The middle band is deliberately wide: two roughly square rooms are not the
    same monotony as two corridors, and a threshold tight enough to call a
    2000x2400 room "a chamber" is measuring the wrong thing.
    """
    a = aspect(spec)
    return "horizontal" if a > 1.25 else "vertical" if a < 0.8 else "chamber"
