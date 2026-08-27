# WaveSpec — the endless escalation and the simulator gate

Owns the enemy roster, the escalation curve, and the fairness bands. The
encounter agent writes WaveSpecs; the deterministic gate checks shape; the
SIMULATOR checks truth.

## The run has no ceiling

**Waves escalate forever; the run ends when the Beacon breaks.** Depth is the
score, and the progression the player experiences lives between runs, in their
own decisions: early runs die shallow because the packing is bad, later runs
go deep because it isn't. That learning curve IS the product, and a fixed
ending would delete it.

The course accepts this explicitly: for infinite modes, "playing until you die
is an end."

## Enemy roster

Two minion forms, distinguished by **how they threaten the Beacon** — that
difference is what makes relic range and placement matter.

| id (working) | reaches | behaviour |
|---|---|---|
| `remnant_walker` | **the Beacon** | closes all the way down the lane and strikes the Beacon in melee. Stopping it is a damage race |
| `remnant_gunner` | **halts inside everyone's range** | stops at a standoff distance and shoots the Beacon from there — but that distance is always close enough for **every** relic to hit it |

### Enemy anchors (wave 1, before scaling)

| | HP | speed | attack | notes |
|---|---|---|---|---|
| `remnant_walker` | **20** | crosses the lane in 10 s | **5 dmg / 1.0 s** melee at the Beacon | two tier-1 relic hits |
| `remnant_gunner` | **15**, on its own curve (below) | halts at ~⅔ lane `[TUNE]` | **3 dmg / 1.5 s** ranged | starts early and stacks |

`hp_scale` and `speed_scale` multiply these as the wave number rises; the
attack values scale more slowly `[TUNE]`, because rising enemy *damage* kills
runs abruptly while rising *count* kills them legibly.

### Nothing parks out of reach

**No enemy may stop beyond the shortest relic range in the game.** Position
creates pressure; it never creates immunity.

This is a law, not a preference. An enemy that short-range relics cannot
touch turns every short-range relic into a trap pick against that enemy —
and this game has no trap picks (`economy.md`). Gate-checkable: for every
enemy with a stop distance, `stop_distance < min(range)` across all relics
at tier 1.

So the two minions differ in **time**, not reach:

- The **walker** only deals damage at the end of the lane. The whole lane is
  time to kill it, and killing it anywhere means it never hurt you.
- The **gunner** starts dealing damage the moment it halts and keeps dealing
  it until it dies. It is a throughput race that begins early — and gunners
  **stack into a firing line** if a build cannot clear them fast enough.

The question the pair asks is therefore "do you have enough throughput,
soon enough", never "did you bring the correct weapon type". Bosses are the
third kind of threat (`bosses.md`).

Names come from the copy pipeline; the terminology guard binds them.

## Escalation

Waves are **generated from a curve, not hand-authored** — an endless game
cannot ship a finite list. The curve owns four things, all rising with wave
number:

- **Count** — the number of enemies per wave grows continuously; this is the
  primary pressure and the most legible one to the player.
- **HP scale** and **speed scale**.
- **Mix** — early waves are nearly all walkers; gunners enter around wave
  `[TUNE]` and their share climbs, so the answer a build needs changes as the
  run deepens.

Every 5th wave is a boss wave (`bosses.md`).

```json
{"wave": 17,
 "spawns": [{"enemy":"remnant_walker","count":14,"from_s":0,"over_s":11},
            {"enemy":"remnant_gunner","count":5,"from_s":3,"over_s":8}],
 "hp_scale": 3.4, "speed_scale": 1.6}
```

### Health growth is exponential, and it has to be

Player power is **multiplicative** — more cells × higher tiers × stacking
buffs — so health that grows linearly loses to it permanently. Measured: with
roughly linear growth the simulator reported a median depth of **146** and
wave durations flat at 20 s. Waves had stopped being a threat and had become
longer piles.

`hpScale(wave) = BASE ^ (wave − 1)`, `BASE = 1.10` `[TUNE]`, swept on 40
seeded runs per value:

| BASE | competent depth | naive depth | gradient |
|---|---|---|---|
| 1.10 | **34** | 24 | 1.42× |
| 1.16 | 19 | 17 | 1.12× |
| 1.22 | 15 | 9 | 1.67× |
| 1.35 | 9 | 8 | 1.13× |

**Bosses scale on their own gentler exponent.** Scaling them with trash put
98% of deaths on boss waves against the 20% chance alone gives — a wall, not a
spike, and four waves in five became decoration. A trash wave is a throughput
problem spread over eighteen seconds; a boss is one pool that must be deleted
before it crosses, so identical scaling makes the boss the only real check.
`bossHpScale = hpScale ^ 0.60` `[TUNE]` brings boss deaths to **24%**, which
is a spike sitting just above chance.

### Rate sets how long a run is; the FLOOR sets how much of it is dangerous

These are separate knobs and conflating them cost the run its entire middle.
With one shared curve the probe measured the deepest enemy of each wave holding
at **0.79–0.90 of the lane for forty-six waves** — dying at the far edge, never
crossing — and then going 0.41, 0.02, 0.00. The Beacon took its first damage on
wave **52 of a run that ended on wave 54**: 91% of every run passed with the
resource the whole economy is built around sitting untouched, followed by a
three-wave collapse.

The cause is not any enemy's statline. Relic range spans 0.55–1.0 and enemies
enter at 1.0, so the entire arsenal fires from the first second of a wave, and
enemy health grows at close to the rate player power does. Two exponentials that
near-parallel cross **once**, so whatever gap exists at wave 1 persists for most
of the run and closes only at the end. Every per-enemy fix failed against this:
armouring the gunner moved the cliff earlier and shortened the run, leaving the
quiet stretch at the same ~82%; front-loading its curve did nothing; raising
boss scaling to `^0.90` moved first damage by three waves.

What works is raising the **floor** — a flat multiplier applied to every enemy,
independent of the rate — because the fault was the wave-1 gap, not the growth.

`hpScale(wave) = LEVEL × BASE ^ (wave − 1)`, `LEVEL = 3.44`, `BASE = 1.05` `[TUNE]`.

| BASE | LEVEL | median depth | quiet fraction |
|---|---|---|---|
| 1.10 | 1.0 | 54 | **91%** |
| 1.22 | 1.0 | 19 | 59% |
| 1.08 | 2.4 | 59 | 41% |
| **1.08** | **2.6** | **54** | **19%** |
| 1.08 | 3.0 | 49 | 11% |

**Both knobs were recalibrated again when Burst's splash was bounded.**
Capping blast targets removed a large amount of player power — the mixed build
was almost entirely Burst, so the whole curve had been calibrated around one
category — and the pair moved to LEVEL 2.9 / BASE 1.05. Median depth 46/44/49
across the three classes, first Beacon damage on waves 10/5/25.

**LEVEL rose from 2.6 to 3.6 when the ultimate shipped**, and that is the
ultimate's real cost. It is a large block of player power arriving at once:
switched on, it moved first Beacon damage from wave 5 to wave 25 and the quiet
fraction from 19% to 71%, measured against the identical curve with the ability
unused. The floor absorbed it. Every class now takes its first damage between
waves 5 and 10 at a median depth of 44-45.

Raising the *rate* buys pressure only by ending runs — depth 19 at BASE 1.22 —
and depth is the score in an endless game. Raising the *floor* buys it at no
cost to depth at all: the chosen pair holds median depth at 54, exactly where
the old curve sat, while first damage moves from wave 49 to wave **10**.

**Quiet fraction is the metric to hold**, not the wave number. Absolute waves
move every time the curve is retuned; the fraction of a run that passes before
anything threatens the Beacon does not, so it is what the harness reports.

### Bosses are the pressure channel, and that is a deliberate trade

`bossHpScale = hpScale ^ 0.90` `[TUNE]`, raised from `^0.60`, with boss damage
per hit cut roughly threefold (bulwark 18→6, splitter 12→4, disruptor 8→3).
The split matters: a boss that **arrives** and a boss that **kills** are
different problems, and the old numbers had them fused, so the only way to stop
bosses ending runs was to stop them arriving at all.

The result is a legible rhythm — minion waves are for building, boss waves cost
Beacon health. Measured on one seed: wave 5 takes 45, then 3, 60, 184, 429.
The first boss lands a real hit the player survives at 75/120, which is what
makes Mend a live decision from wave 5 instead of wave 50.

**The cost, recorded rather than hidden: boss deaths sit at 57%** against the
20% chance alone gives. Backing the exponent down to `^0.72` brings that to 38%
— and sends the quiet fraction straight back to 69%. They are one knob pulled
in two directions: bosses being the pressure channel *is* what buys the early
bleed. 57% is accepted because the deaths are no longer surprises — the Beacon
visibly bleeds across waves 35, 40 and 45 before one ends the run — where the
original 98% wall killed from full health with no warning.

**Skill gradient: ~5× — and the 2× band is now the open question.** (competent vs naive median depth), close to the 2×
band. It rose from 1.42× when the economy was implemented — the earlier figure
was measuring a game with no gold sink, so spending could not distinguish good
play from bad, and 1.83× still measured one with an unlimited gold exploit.

**The 1.97× figure does not describe the shipped game and should not be quoted.**
It was measured before LEVEL was separated from BASE, on a curve soft enough
that careless play still reached wave 29. On the current floor the naive bot
reaches wave 8-9 while the competent one reaches 44-45, so the gradient is
**4.9-5.5×**, roughly 2.5x the band this contract set.

Recorded, not corrected, because it is not yet clear the band is right. The
naive bot is deliberately awful — first offer, first buff, ultimate fired the
instant it lights up — and a real beginner is better than that, so 5× is an
upper bound on the spread between competent play and the worst play possible,
not between good and bad players. Whether the floor is too punishing is a
playtest question, and playtesting is what the number is waiting on.

### The depth targets are the curve's only real input

Run *length* is not a design number — the market is untimed and the speed
toggle exists (`combat-model.md`), so the player authors their own pace.
What the curve owns is **depth**, and the shape to tune toward `[TUNE]`:

| player | dies around |
|---|---|
| first run, no idea | wave 8–12 |
| competent, has learned to pack and merge | wave 25–35 |
| expert, thinning the pool and stacking one category | wave 50+ |

Roughly 3–5× depth between a first run and a competent one: enough that
improvement is unmistakable, not so much that early runs feel like a tax.
A wave should take **~12–20 s at 1×** `[TUNE]`, so a competent run is
around 8 minutes of battle plus whatever the player spends deciding.

The gradient between those rows is what the simulator measures below; the
absolute numbers are free to move as long as the ratio holds.

## The simulator gate

An endless game cannot be gated on "is it clearable." The bands that matter:

- **Difficulty anchor:** a competent reference build reaches a median wave
  inside a target band `[TUNE]` — deep enough to feel earned, shallow enough
  that depth still means something.
- **Skill gradient (the important one):** an optimal-play harness must reach
  meaningfully further than a random-play harness — target ≥2× median depth
  `[TUNE]`. If good and bad decisions land in the same place, the decisions
  are decoration and the game has no content.
- **No wall:** no single wave where survival probability craters relative to
  its neighbours. A cliff reads as unfairness, not difficulty.
- **Class parity:** both classes' median depth within ±10% `[TUNE]` — the
  asymmetry contract's law, measured.
- **No dead relic:** every relic appears in some deep run; none strictly
  dominates its category on damage-per-cell.

Verdicts carry the rules fingerprint: a PASS dies with the gate that issued it.


## The ultimate must be strong, never required

The curve is tuned so a run that **never presses the ultimate** still reaches
the mid-twenties, against low fifties when it is used. That ratio is the target,
and it is a design law rather than a preference:

> Choosing 10x is choosing to give up the one live input (`combat-model.md`).
> That trade is only honest while the game is survivable without it. Tuned so
> the ultimate is the difference between playing and dying, the speed control
> stops being a pacing tool and becomes a trap.

Measured at `LEVEL 3.44`, medians across hunter/titan/warden:

| | hunter | titan | warden |
|---|---|---|---|
| ultimate used | 52 | 59 | 54 |
| never pressed | 26.5 | 27.5 | 21.5 |

At `LEVEL 3.5` the same comparison read 57/55/53 against **14/9/18** — the
ability had become mandatory. Six hundredths of the floor is the whole distance
between "strong" and "required", which is why this ratio is worth re-measuring
after any change to player power.

## Class parity, and a measurement that was lying

**Spread 1.13x** (52 / 59 / 54), hunter to titan, on 55 seeded runs per class
with bootstrap intervals. Hunter [46, 56] against titan [50, 67] — they overlap,
so the ordering is suggestive rather than established.

Two corrections got it there, and both were faults in the harness rather than
in the game:

1. **The bot was overvaluing ultimate buffs**, scoring them at `0.30 x cells`
   against a category buff's full weight, so it bought them over buffs worth
   two to four times more. The tell was absurd on its face: the no-ultimate
   control, which skips those buffs, *out-ran the bot that had the ability*.
   Repriced to `0.12 / 0.10 / 0.06`. Spread fell from **1.26x to 1.07x** on that
   change alone — most of the apparent Hunter gap was bad shopping, not a class.
2. **The bootstrap was not resampling.** It drew on a fixed stride, which is a
   permutation, so every replicate returned the identical median and the
   interval printed as a point: `90% CI [39, 39]`. A CI that never varies is
   broken, not precise.

Only after both did widening the Blade Barrage's blasts (0.10 to 0.15) close the
rest, worth 51 to 53.5.

**`sim/run.ts` no longer runs its CLI on import.** Importing `simulate` printed
the whole batch, so every harness reusing the simulator emitted lines that
looked exactly like its own output — a floor sweep came back reading
"median median 44" and the first pass of these numbers was nonsense.
