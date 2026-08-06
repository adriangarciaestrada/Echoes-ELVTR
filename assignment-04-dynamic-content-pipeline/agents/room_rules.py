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
        x, run_start = c["x"], None
        while x <= c["x"] + c["width"] + EPS:
            solid_below = not in_cavity(cavity, x, c["z"] - step / 2)
            if solid_below and run_start is None:
                run_start = x
            elif not solid_below and run_start is not None:
                spans.append((run_start, x, c["z"], f"floor[{i}]"))
                run_start = None
            x += step
        if run_start is not None:
            spans.append((run_start, c["x"] + c["width"], c["z"], f"floor[{i}]"))
    return [s for s in spans if s[1] - s[0] > EPS]


def solid_tops(solids: List[Dict]) -> List[Support]:
    """Every solid's upper surface. A breakable wall is not stood on."""
    return [(s["x"], s["x"] + s["width"], s["z"] + s["height"], s["id"])
            for s in solids if not s.get("breakable_by")]


def all_supports(spec: Dict) -> List[Support]:
    return floor_spans(spec["cavity"]) + solid_tops(spec.get("solids") or [])


def support_of(spec: Dict, element_id: str) -> Optional[Support]:
    """Resolve a critical-path element to the surface it stands on."""
    for s in all_supports(spec):
        if s[3] == element_id:
            return s
    for d in spec.get("doors") or []:
        if d["id"] != element_id:
            continue
        return door_support(spec, d)
    return None


def door_support(spec: Dict, door: Dict) -> Optional[Support]:
    """A door resolves to the surface it opens onto, not to a point in a wall.

    Walking in from a doorway is walking, so the floor beyond it is the support
    the path continues from. Treating the doorway itself as a zero-width perch
    invents a gap the width of the room and a run-up of nothing.
    """
    threshold = door["at"] if door["side"] in ("Left", "Right") else None
    for s in all_supports(spec):
        if threshold is not None:
            if abs(s[2] - threshold) < EPS:
                return s
        elif s[0] - EPS <= door["at"] <= s[1] + EPS:
            return s
    return None


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
