# Combat model — deterministic resolution

Owns how a battle resolves. The engine and the simulator run THIS, or the
simulator's verdicts are fiction.

## The architecture law

**The battle core is a pure, renderer-free module** (plain TypeScript: state
in, events out, fixed timestep). Phaser subscribes to it for drawing; the
headless simulator imports the same module and runs it at full speed. One
implementation, two consumers. This is what makes "wave 7 is fair" a measured
claim — and it is also what the course's QA classes grade toward.

## Determinism

- One seeded PRNG per run (`seed` in the run record). Spawns, market offers,
  and effect procs all draw from it. No damage ranges — a hit deals its
  number (course guidance: deterministic systems unlock replay and testing).
- Fixed timestep: 30 ticks/s `[TUNE]`. Replays are (seed + input log).

## The lane and the Beacon

| | anchor | why |
|---|---|---|
| Lane crossing | **10 s** at base speed `[TUNE]` | the time a build has to kill a walker before it arrives |
| Beacon HP | **100** `[TUNE]` | readable as a percentage, which is what the HP bar shows |

All distances are expressed as fractions of the lane, never in pixels — the
renderer scales them, the simulator does not care.

## Resolution rules

- Single vertical lane. Enemies spawn at seeded times/offsets, descend at
  their speed, stop at the Beacon line, and strike it every `atk_interval`.
- The Beacon holds the only player-side HP. It breaks → run ends → score
  screen (score pays out win or lose).
## Targeting — how the battle decides

Targeting is the autobattler's whole "AI", and it is per-category on purpose:
if every relic picked the same target, category choice would be a stat
decision instead of a tactical one.

**Cooldowns always run.** A relic that has been idle is ready the instant a
valid target exists; it never "wastes" a cycle on an empty lane.

| Category | Picks |
|---|---|
| **Bolt** | the enemy **closest to the Beacon** — most dangerous first |
| **Burst** | the point covering the **most enemies** within its radius; ties broken by closest-to-Beacon. This is what makes a Burst read as smart rather than as a Bolt with splash |
| **Construct** | its own spec — the orbiter strikes what it passes; the turret picks like a Bolt |

### Overkill is prevented, and this matters more than it sounds

Without a guard, six relics dump into one dying walker while the rest of the
wave strolls past, and the player watches their build look stupid for reasons
they cannot see.

The guarantee comes from **resolution order, not bookkeeping**: damage lands
the instant a relic fires, and dead enemies are removed immediately after
each relic's shot. So by the time the next relic in the same tick chooses a
target, anything already killed has left the list — a build cannot pile onto
a corpse because corpses do not exist between shots.

Measured, not asserted: six tier-1 relics against six 20 HP walkers deal
exactly 120 damage. Zero waste, and the core test pins that number.

⚠️ This holds **only while damage is instantaneous.** If projectiles are ever
given travel time, damage-in-flight must be tracked per enemy and excluded
from targeting, or the guarantee silently disappears.

### The reach law

No enemy may stop beyond the shortest relic range in the game
(`wave-contract.md`). Targeting therefore never has to handle the
"unreachable enemy" case — because that case is forbidden at the content
level, not patched at the combat level.
- The class super is the run's only manual combat input; cooldown-gated
  (`bosses.md` and class kit in `loom-design.md`).
## Speed is the player's pacing control

**1× · 2× · 3× · 5× · 10×.** Not a quality-of-life nicety — it is how the
player authors the pace of their own run.

The market phase is untimed by design, so total run length is already the
player's: a deliberate player spends an hour on the same build a decisive
one finishes in fifteen minutes, and both reach the same depth. Battle is
the only clock the designer controls, and the toggle hands that over too.
A player who already knows what their build does should be able to skip to
the part they are playing for.

- Implemented as **N logic ticks per rendered frame**, never by scaling
  delta-time — at a 30 Hz fixed step, 10× is 5 ticks per 60 Hz frame.
  Determinism is preserved exactly, which is also why the headless simulator
  is the same code with the cap removed.
- The setting **persists across waves and across runs** (localStorage).
  Re-arming it every wave would be its own tax.
- **The ultimate stays manual at every speed**, and that is the honest
  trade: at 10× a wave passes too quickly to react, so choosing speed is
  choosing to give up the one live input. Emergent, not enforced — waves you
  can win asleep get fast-forwarded, waves you cannot get watched.
- Automated runs mute audio (documented trap: agents trigger sounds
  thousands of times per second).


## The ultimate, and how it is priced

The only live input in a battle (`reference-game.md`), one per class, on a
cooldown that starts full at every wave.

**It is denominated in SECONDS OF THE RAW LOOM, never a flat number and never
the buffed arsenal.** `pool = (sum of UNBUFFED relic damage/cooldown) x
worthSeconds`, cells and tiers only. A flat ultimate decays to nothing against
a health curve that compounds; pricing on the loom keeps it worth casting at
wave 5 and wave 50.

**Raw, not buffed, and the difference was measured.** Pricing on the buffed
arsenal failed at the one thing the ultimate buffs are for: relic buffs
inflated the ultimate too, so spending a pick on the ultimate starved the
arsenal the ultimate was priced against. Taking EVERY ultimate buff offered
across a whole run moved its share of a late wave from **10% to 11%** — the
buffs paid for themselves and nothing else. Raw pricing separates them:

| wave | share, no investment | share, every ult buff taken |
|---|---|---|
| 3  | 40% | 40% |
| 11 | 24% | 21% |
| 19 | 14% | 14% |
| 27 | 8%  | 10% |
| 35 | **4%** | **9%** |

The uninvested run died on wave 35. The invested one passed 43.

### The ultimate is never weakened on purpose

Its power is held constant and the waves grow around it. Nothing in the code
scales the ultimate down by wave number, and nothing should: the falling share
above is entirely emergent, from two facts already in the design. Waves get
longer (11s to 28s), so a fixed number of arsenal-seconds is a smaller fraction
of each one; and the arsenal grows with the loom AND with every relic buff,
while the ultimate grows only with the loom. It gets no weaker — everything
around it gets bigger.

That is what the three ultimate buffs are for, and why they are the only lever
that closes the gap. Declining to invest is a real choice with a real cost, not
a trap.

**The pool is SHARED by what it catches, not applied per target.** Per-target
scales with the size of the wave, and a late wave holds a hundred Remnants;
one press would delete it.

**Cooldowns are long: one cast per wave, two in the longest.** 26s barrage,
24s wave, 28s knot, against wave durations of 11-28s, and the ultimate starts
every wave ready. The resolved cooldown is floored at 15s so stacked cooldown
buffs cannot turn the one live input into a rotation — heavy investment buys a
second cast in waves that used to allow one, never a fourth in every wave.

**A press that cannot connect costs nothing.** Not the same as "the lane is
empty": the Riven Wave breaks from the Beacon outward and reaches only part of
the lane, so it can be armed, pressed, and touch nothing. The first build
burned the full twenty-second cooldown on exactly that, every time, and the
core tests passed — the browser check found it, because only a real keypress
at a real moment in a real wave exercised the case.

### A sustained zone beats a burst at equal cost, and by a lot

Measured, holding the budget identical at 4.5 seconds of arsenal:

| class | ultimate | first Beacon damage | depth |
|---|---|---|---|
| Hunter | barrage (burst) | wave 10 | 47 |
| Titan | wave (burst) | wave 10 | 49 |
| Warden | knot (sustained) | **wave 25** | 47 |

The knot was cut from 9 seconds to 6 to 4.5 and its gathering removed entirely
(`pull: 0`) — first damage stayed at wave 25 through every one of those. The
cause is not the damage and not the crowd control: a zone spends its pool at a
chokepoint over four seconds, killing Remnants as they arrive, while a burst
spends the same pool at one instant and lets the next arrival through. Equal
budgets do not buy equal prevention.

Kept as the Warden's identity rather than tuned away, because depth parity
holds across all three (44/45/44 on the shipped curve) and the class law is
about the shape of the decisions, not identical numbers.


### The Knot is thrown to the middle, and may only pull backwards

It lands at `MID_LANE` — halfway down the lane, dead centre across it — every
cast, whatever the Remnants are doing. It is a **fixed choke point they must
walk through**, not a shot that follows the thickest crowd. That makes it the
one ultimate whose value is positional rather than reactive, which is also why
"spend it, we are in trouble" is not a reason to throw one: a Knot cannot answer
something already at the wall.

**Its pull may only ever move a Remnant BACK up the lane, never forward.** A
symmetric pull was fine while the Knot landed on the crowd, with roughly as many
Remnants behind it as in front. Pinned mid-lane it is not: most of a young wave
is above the middle, so every cast hauled the whole lane 0.2 closer to the
Beacon — the Warden's own ultimate delivering the wave it exists to hold.
Measured at **median depth 4, against 21 for never casting it at all**.

The law was already written for the halting case — *it gathers the lane, it does
not deliver it* — and this is the same law, enforced where it actually bites.

### An ultimate only good play cannot use is dead weight

The Riven Wave reached 0.62 of the lane in its first build, gated on Remnants
being near the Beacon — and the entire rest of the game exists to stop that
happening. The competent bot cast it **zero times on most waves**. Reach is now
0.85, and it fires on nearly every wave.

The general form: an ability whose trigger condition is the failure state the
player is trying to avoid will be used most by the players who need it least.


## Drawing the game must never advance the run

`buffChoices()` shuffled the pool on every call and returned a fresh three. The
renderer calls it to draw the screen, so:

- **an exploit** — anything that redrew the buff screen dealt three new buffs.
  Clicking the speed toggle mid-choice was a free, unlimited reroll, found in
  playtest.
- **a broken core, which is worse** — the same seed and the same decisions gave
  different runs depending on how often the UI happened to redraw. The
  simulator's verdicts are only worth something while it and the game agree, and
  a renderer that steers the RNG breaks that silently.

Offers are rolled **once per grant and held**, the way the market's already
were. The rule generalises: *a method the renderer calls to draw with must be
free of side effects on the run.* Anything that consumes the RNG belongs on a
transition — taking a buff, clearing a wave, rerolling on purpose.

Held two ways: a core test that calls `buffChoices()` twenty-five times and
asserts the three are unchanged and the run rolls identically afterwards, and a
browser check that clicks the speed toggle six times on a real buff screen. Both
were confirmed to FAIL against the old code before the fix landed.
