# RelicSpec — the relic contract

What a relic is, field by field. The item agent writes to it, the gate
enforces it, the engine loads it. This note owns every relic number.

## Schema

```json
{
  "relic_id": "bolt_needle",
  "category": "Bolt | Burst | Construct",
  "footprint": [[0,0],[0,1]],
  "tiers": [
    {"damage": 10, "cooldown_s": 1.20, "range": 420},
    {"damage": 17, "cooldown_s": 1.05, "range": 420},
    {"damage": 29, "cooldown_s": 0.90, "range": 440, "effect": "slow_20pct_1s"},
    {"damage": 49, "cooldown_s": 0.78, "range": 460, "effect": "stun_10pct"},
    {"damage": 83, "cooldown_s": 0.66, "range": 480}
  ],
  "stacking": "stacks | one_of",
  "display_name_key": null
}
```

- `footprint`: cell offsets from an anchor cell; rotation is always legal and
  is the player's, never baked into the spec.
- `display_name_key` is null at generation. Names come from the copy pipeline
  and land as String Table keys — a relic never carries a literal name.

## The roster (10 archetypes)

| id (working) | category | footprint | stacking |
|---|---|---|---|
| bolt_needle | Bolt | 1×1 | stacks |
| bolt_shuttle | Bolt | 1×2 | stacks |
| bolt_long | Bolt | 1×3 | stacks |
| bolt_heavy | Bolt | 2×2 | stacks |
| burst_bomb | Burst | 1×1 | stacks |
| burst_arc | Burst | L (3 cells) | stacks |
| burst_field | Burst | S/Z (4 cells) | stacks |
| burst_lane | Burst | 2×1 | **one_of** (knockback) |
| construct_orbit | Construct | plus (5 cells) | **one_of** (bouncing slow) |
| construct_turret | Construct | 2×1 | stacks |

### The tier values above are the balance anchor

A tier-1 relic at **10 damage / 1.2 s ≈ 8.3 dps** is the unit everything else
is measured against, and the ladder rises ~1.7× per tier (law 1).

The arithmetic that makes wave 1 work, and the reason these numbers rather
than others:

- One starting relic kills a 20 HP walker in **2 hits ≈ 2.4 s**.
- Wave 1 is ~6 walkers ≈ 120 HP → **~15 s**, inside the 12–20 s target
  (`wave-contract.md`).
- A walker that leaks deals 5 dmg/s into a 100 HP Beacon: **20 s to die from
  one leak.** Early mistakes cost, without being fatal.
- Three parked gunners deal 6 dmg/s: **~17 s.** Real pressure, answerable by
  throughput.

**The simulator owns the final values.** These anchors exist so the first
build is playable and so the curve has somewhere to start; every one is
`[TUNE]` and expected to move once seeded runs report median depth and the
skill gradient (`wave-contract.md`).

## The tier ladder

Five tiers. Tier is shown as the **cell background colour** behind the relic
(reference pattern — the sprite never changes).

| # | Colour | Rarity |
|---|---|---|
| 1 | White | Common |
| 2 | Green | Uncommon |
| 3 | Blue | Rare |
| 4 | Purple | Legendary |
| 5 | Yellow | Epic |

Merging is same-relic, same-tier. Sixteen Commons make one Epic, so an Epic
is a genuine event in a run rather than a mid-game default.

## The four laws (gate-enforced, arithmetically)

1. **Merging is lossy:** `damage(N+1) ≤ 1.8 × damage(N)` and
   `≥ 1.5 ×` `[TUNE within band]` — never ≥ 2×. Merging buys space and
   effects; two separate copies always out-damage one merged. This law is
   the game; see `reference-game.md` for the evidence.
2. **Tiers gate effects:** Blue and Purple each add an `effect`; White and
   Green never carry one, and Epic adds no new effect — it is the ceiling of
   what the Purple already does. This is why lossy merging is still tempting:
   the ladder buys capability, not just numbers.
3. **Cooldown improves with tier**, monotonically.
4. **One-ofs declare themselves:** `stacking: one_of` relics must name the
   non-stacking effect in their description key.

## What the gate checks

Schema; footprint fits the smaller class's starting grid in some rotation;
all four laws; merge chains terminate at Epic; category is one of three;
**the shortest tier-1 range is greater than every enemy stop distance**
(the reach law, `wave-contract.md`);
per-category damage-per-cell inside the balance band (`wave-contract.md`
owns the band).


## Damage-per-cell follows a curve, and the curve is per category

Fitted against the shipped roster rather than invented. Every relic's tier-0
damage-per-cell sits on a power law in its own footprint size:

    DPC = A × cells^-k

| category | A | k | R² |
|---|---|---|---|
| Bolt | 8.37 | 0.360 | 0.995 |
| Burst | 6.28 | 0.511 | 0.997 |
| Construct | 5.50 | 0.426 | **0.584** |

Two of the three were tuned by hand into a near-perfect fit and nobody wrote the
law down. Construct never joined them: `construct_turret` sits 40% above its own
category's curve, and `construct_node` was accepted *below* the two-cell relic,
inverting the ordering the other two categories keep. `[TUNE]` both constants.

`k` is the price of size, and it is not the same price in each category — Burst
charges 0.51 against Bolt's 0.36, which no one decided. Choosing one `k` for the
game is a design decision waiting to be made, not a fact to be preserved.

**A curve is not a target.** A relic may sit off it deliberately; what it may not
do is sit off it by accident, which is what happened here. The gate reports the
distance from the curve so the deviation is a decision on the record.

## An awkward shape is an asset, not a defect

The roster's shapes range from a single cell to a 3×3 cross at 0.56 density, and
that range is the point: the Loom is a packing problem, and a roster that all
packs the same way has no problem left to solve. Relics must differ in shape and
in effect, or they are the same relic in different colours.

So the gate does NOT reward density. What it refuses is the relic that is hard to
place **and** unremarkable once placed — awkward geometry has to buy something.
A low-density footprint must come with either an effect or damage-per-cell at or
above its category's curve.

Measured, for reference: pick rate tracks packing density far more closely than
it tracks damage-per-cell. `bolt_heavy` and `burst_field` both cost four cells;
the square is taken three times as often as the S.

## Reach is the categories' identity, and it has to be enforced

| category | band | cap no buff may pass |
|---|---|---|
| Bolt | 0.85 - 1.00 | 1.00 |
| Construct | 0.60 - 0.72 | 0.78 |
| Burst | 0.40 - 0.50 | **0.55** |

For a long time these bands did not exist. Bolt ran 0.75-1.00 and Burst
0.70-0.80, so `burst_arc` at 0.80 outranged `bolt_needle` at 0.75 — the two
overlapped almost entirely, and a playtest that took the range buff twice had
Burst relics striking the spawn line, which is Bolt's whole job.

The **cap** is what makes it a law rather than a starting value: a global range
buff that stacks will otherwise erase the one property the categories read most
clearly. Buffs raise a relic toward its category's limit and stop. A core test
buffs range twelve times and asserts no Burst can outreach the shortest Bolt.

Burst fighting at the wall is also what gives the Titan's knockback something
to answer, which is the pairing a playtest reached for unprompted.

## Burst fires a CONE, tipped on the Beacon

The lane has a real lateral axis. It did not for a long time: a Remnant's
across-the-lane position was decoration derived from its id inside the
renderer, which is why every area weapon had to hit the lane's full width —
there was no across-the-lane to miss in.

A Burst now fires a cone whose **tip is the Beacon**, so it widens with
distance the way a shot leaving a barrel does, and **widens again with every
tier** — that growth is what a Burst relic buys by merging. Half-angles run
from 20&deg; to 46&deg; across the pool, doubled for the full cone.

This replaced a slab that spanned the lane's full width at a fixed depth, and
the slab was the single largest cause of the category dominating: everything at
a given distance was caught, whatever side of the lane it stood on. A playtest
put it plainly after watching the shapes drawn in-game &mdash; the zone was too
big, and it should come out of the gun.

**The old target cap is gone with it.** `BURST_MAX_TARGETS = 3` had been the
blunt fix for the same fault, and it was invisible: the slab drew far wider
than the three it actually hit. Geometry is the limit now, and the player can
see it.

**Burst damage returned to roughly its original values.** It had been cut twice
to pay for the slab. The geometry was the fault, not the numbers.

### The rule, whole

The relic **aims at a Remnant within its reach**, it shoots, and **every Remnant
the cone touches takes the damage** — the one it aimed at and everything else
standing in the shape.

The region is a **true sector**: straight sides from the muzzle, closed by an
**arc**. Both bounds are measured from the Beacon:

- **reach is a RADIUS** — `hypot(x, pos) <= range`, distance from the muzzle,
  not depth down the lane;
- **the cone** is an interval of bearing, `±spread`.

Held by a test that places four Remnants: the aimed one, one alongside it inside
the cone, one inside the bearing but past the reach, and one within reach but
outside the bearing. The first two take damage; the last two do not.

### Radial reach forces the lane's width, and that is the whole trick

Measured radially, a walker resting against the wall out at the lane's edge is
`|x|` from the Beacon. Let the lane be wider than the shortest reach in the pool
and that walker grinds the Beacon down where **no build can answer it** — a
Burst-only run lost to geometry rather than to play.

So the lane's width is not chosen, it is **derived**:

```
LANE_HALF_WIDTH   = min(reach of every relic)          = 0.45
spawnSpanFor(halt) = sqrt(minReach² − halt²) × 0.94
```

A gunner halts 0.34 down the lane, so it rests at `hypot(0.34, x)` and is
allowed less room across than a walker: ±0.28 against ±0.42. Measured resting
distances are 0.42 for anything reaching the wall and 0.44 for the gunner,
against a shortest reach of 0.45.

Deriving it means lowering any relic's reach narrows the lane instead of
silently stranding an enemy outside it, and `spawnSpanFor` throws outright if a
halt is ever set beyond every reach. The law asserts resting distance, not
halting depth — depth is no longer the measurement that decides anything.

### No column is ever unreachable

The fear a cone invites is that a Remnant spawns at an `x` no Burst can cover
and the run is lost to geometry. It cannot happen, and the reason is structural
rather than tuned:

- reachability is filtered by `pos` **alone**, never by `x`;
- a cone is *aimed at* a chosen Remnant, so that Remnant sits at bearing zero
  inside its own cone and is always hit;
- every enemy that halts does so inside the shortest reach in the pool, which
  the reach law above already enforces.

Held by two tests using the worst case the pool allows — `burst_lane`, the
narrowest cone on the shortest reach, alone on the loom, against a Remnant
pinned to each lane edge while the rest cluster opposite to pull the cone away.

**What is real is softer: a lone flanker is served last.** The cone aims at the
densest point, so a Remnant out on its own is the last thing a Burst build
attends to, and it will reach the wall while the crowd is worked. That is a
consequence of the targeting rule, not a defect — but it is the shape of the
risk a committed Burst build is taking, and it should stay visible rather than
be tuned away quietly.

### What the slab cost, measured

An unbounded blast is not a strong category, it is a category that cannot lose:
its output scales with how many Remnants are on the lane while Bolt and
Construct stay single-target, and wave count rises forever.

Measured, single-category builds by median depth:

| | uncapped | capped at 3, retuned |
|---|---|---|
| Bolt only | 14 | 58 |
| Burst only | **69** | 70 |
| Construct only | 4 | 4 |

Burst outreached Bolt **5.8x** before the cap and 1.2x after. The finding
arrived from two directions at once: the simulator measured it, and a playtest
independently reached its deepest run to date on Burst alone.

### Open: Construct is not playable on its own

Four against four against **two** — there are only two Construct relics in a
pool of ten, so a Construct-only build starves on offers before its power is
even tested. Its 4 is not a balance number, it is a content gap. Either the
category needs more relics or it is not meant to be a standalone strategy, and
the contract should say which.

### Focus beats spread, and that is not a bug

Single-category builds outrun the mixed bot (58 and 70 against 34) because
merging needs two of the SAME relic, and category buffs compound on a board
that commits. Specialising is the intended shape of the decision. The mixed
figure measures the bot's shopping, not a balance baseline.
