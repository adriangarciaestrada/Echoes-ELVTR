# Echoes — a Generate / Evaluate / Refine pipeline for room geometry

**ELVTR "Multi-Agent AI for Game Development" — Assignment #6.**

**Echoes** is a 2.5D metroidvania vertical slice in Unreal Engine 5.8. Two
classes, the Hunter and the Titan, run the same map with different traversal
verbs. This pipeline generates the **rooms** they run through, and refuses the
ones neither of them can get out of.

```bash
python3 agents/ger_rooms.py --brief "A tight corridor opening into a two-floor shaft"
python3 agents/ger_rooms.py --brief "..." --attempts 5 --out R3_my_room
python3 agents/ger_rooms.py --replay production/output/R3_shaft.json   # no model called
python3 -m pytest agents/test_ger_rooms.py -q                          # 13 tests, no model
```

The generator runs on a personal subscription through a headless CLI. No API
keys, no paid endpoints.

---

## Pre-Build Declaration

*Submitted before any code was written; also standing alone in
`PRE-BUILD-DECLARATION.md`.*

**What this game generates inconsistently.** Room geometry. An agent writes a
RoomSpec: the carved cavity, its ledges and doors, the class pockets, and the
ordered critical path.

**The rule from the GDD every room must satisfy.** `GDD-course-scope.md` §7.1,
band 1 — *"Clearability = 100%: every class clears every room, branch, and boss
at every bot profile; softlocks = 0. Hard assertion, build-blocking."* §5 adds
its geometric half: *"Neither class out-jumps the other, so exclusivity comes
from where anchors and cracked walls are placed, never from raw reach."*

**What a failure looks like, concretely.** The character jumps to the next ledge,
200 above and inside the guaranteed band, and stops dead. That ledge is 40 thick,
so the space between them is 160 and the body is 176. Reach was satisfied; the
body did not fit. The generator, the gate and a human review all passed that room.

---

## The four parts

| | Component | Where | Model? |
|---|---|---|---|
| **G** | Level Designer agent, writing a RoomSpec | `agents/01-level-designer.md` | yes |
| **E** | Deterministic gate over the geometry | `agents/validators.py`, `agents/room_rules.py` | **no** |
| **R** | Repair brief scoped to the rules that failed | `agents/ger_rooms.py` → `Refiner` | — |
| **CB** | Non-convergence detector with a diagnosis | `agents/ger_rooms.py` → `CircuitBreaker` | **no** |

Only the generator costs a token. Reach, fit, budgets and exclusivity are
arithmetic, and asking a language model to check arithmetic buys a less reliable
answer at a higher price — the project has the receipt for that: an earlier
reviewer agent asked to judge reachability produced "cannot verify" as its single
most frequent finding, which is a question restated rather than answered.

---

## What the evaluator enforces

`GDD-course-scope.md` §7.1 opens the acceptance bands with a hard, build-blocking
assertion:

> **"Clearability = 100%** — every class clears every room, branch, and boss at
> every bot profile; **softlocks = 0.** Hard assertion, build-blocking (§10)."

§5 supplies its geometric half:

> "Neither class out-jumps the other (Lift matches the double jump), so
> exclusivity comes from where anchors and cracked walls are placed, **never from
> raw reach**."

So the evaluator sorts its findings into two piles rather than counting them. Ten
findings that leave the room playable and one that does not are not "eleven
errors"; only the second kind is build-blocking, and the report says which is
which. The **softlock** pile is:

| Code | The room it describes |
|---|---|
| `ERR_UNREACHABLE` | a step past the guaranteed reach band |
| `ERR_NO_HEADROOM` | nowhere on a surface to stand up |
| `ERR_CLIMB_BLOCKED` | the next ledge overhangs the one being jumped from |
| `ERR_NO_WAY_THROUGH` | standing room on both sides of an obstruction, none past it |
| `ERR_JUMP_CLIPPED` | the ceiling takes the jump the step needs |
| `ERR_ONE_WAY_DROP` | a descent the player cannot climb back out of |
| `ERR_PATH_GATED` | the route needs a tool, so one class is locked out |
| `ERR_NO_RUNUP` | not enough floor to reach speed before a gap |

Everything else — `ERR_LADDER_CLIMB`, `ERR_UNIFORM_LEDGES`, `ERR_DEAD_SPACE`,
`ERR_OFF_MODULE` — is a quality rule. A ladder-shaped climb is dull; it is not
impassable, and conflating the two would let a real softlock hide inside a long
list.

The numbers are read from the character, not chosen. `CAPSULE_HEIGHT` 176,
`CAPSULE_RADIUS` 34 and `MaxStepHeight` 45 come from `BP_GreyBoxCharacter`'s own
capsule, and the reach figures from `vault/04-world/movement-reach.md`, where each
one is recorded as measured in play. Re-tune the character and the gate moves with
it instead of silently describing a character the game no longer has.

---

## What it caught

**A room that satisfied every reach rule and could not be climbed.**

The generator placed ledges exactly 200 apart — `RISE_GUARANTEED`, so every reach
check passed — and stacked them one above another. Vertical spacing is measured
surface to surface, so a ledge 40 thick leaves 160 of air, and the character is
176 tall. The jump landed. The body did not fit.

It was found by playing it, not by reading it. The room had passed the
deterministic gate, passed an LLM reviewer, and been approved by a human whose
own approval note reads: *"the room has not been seen in the engine yet."* That
sentence is the whole argument for this assignment — the gate was measuring
distance and calling it clearability.

The arithmetic underneath is worth stating, because it shows the failure was not
a near miss. Headroom of 200 under a rise of at most 200 would require a platform
of zero thickness. **A stacked climb cannot be made to work by adjusting the
numbers**; ledges have to alternate sideways. `ERR_CLIMB_BLOCKED` exists to say
so, and `ERR_NO_HEADROOM`, `ERR_NO_WAY_THROUGH` and `ERR_JUMP_CLIPPED` each exist
because a specific room shipped past the previous gate and could not be traversed.

---

## The refiner sends the rule, not the complaint

An error message says a room is wrong. A generator that keeps failing the same
rule has not understood the rule, and repeating the complaint louder does not
teach it. So each failing code is answered with the constraint behind it and the
numbers it comes from, and **only the codes that actually fired** — a generator
handed the whole contract again re-reads the parts it already satisfied and is no
likelier to fix the part it did not.

```
[SOFTLOCK] ERR_NO_HEADROOM at critical_path
    what the gate measured: 'ledge_2' offers 0 of width with 200 of clear space
        above it, and the character is 176 tall and 68 wide.
    the rule behind it: The character is 176 tall and 68 wide, and needs 200 of
        clear space above a surface to stand on it. Vertical spacing is measured
        surface to surface, so the platform above eats its own thickness out of
        that space: two ledges 200 apart and 40 thick leave only 160, and the
        body does not fit. Raise what is above, or lower the surface.
```

The brief closes by telling the generator **not** to restructure what passed.
Every other rule was already satisfied, and a rewrite trades a fixed rule for a
broken one — which is the failure mode the circuit breaker below exists to catch.

---

## The circuit breaker names which kind of stuck

Spending the whole retry budget is not a decision, it is the absence of one.
These three outcomes need three different responses from a human, so they are
reported as three different things:

| Trip | What happened | What a human should do |
|---|---|---|
| `NO_PROGRESS` | the identical rule failed in the identical place twice running | **do not raise the budget** — it buys identical output. The rule is missing from the contract, or is written in a way that does not say what to do instead |
| `REGRESSION` | two attempts in a row worse than an earlier one | keep the best attempt, saved beside the report. Rules that cannot both be satisfied by moving the same geometry usually mean the room's *dimensions* are wrong, not its contents |
| `BUDGET` | still improving when the attempts ran out | worth more budget; re-run with a higher `--attempts` |

Two details in there are load-bearing.

**A failure is identified by code and location, not by message.** A generator that
shifts a ledge ten units and fails the same rule in the same place has not made
progress, and its error message will have changed anyway because the message
quotes the new numbers.

**One bad step is not a regression.** A generator moving geometry to satisfy one
rule will routinely break another on the way, so tripping on the first worsening
would throw away loops that were about to succeed — there is a test for exactly
that recovery. Two in a row is a trend, and at that point the remaining budget is
better spent on a human than on a third attempt.

Worse is judged on softlocks first and total errors second. Trading five cosmetic
fixes for one more softlock is a step backwards even though the error count fell,
because only one of those piles blocks the build.

---

## The loop, running against the real generator

Three runs against agent `01-level-designer` on a subscription CLI. The full
transcripts are in `production/output/R3_ger_run*.ger.json`.

| Run | Brief | Attempts | Outcome |
|---|---|---|---|
| 2 | one standard-height hall with a Titan pocket | 4 | **ESCALATED** — `NO_PROGRESS` |
| 3 | the same brief, after the fix below | 5 | **ACCEPTED** |
| 1 | a tight corridor into a two-floor shaft, both pockets | 3 | **ACCEPTED** |

### The escalation that found a defect in the evaluator

Run 2 failed `ERR_UNREACHABLE` four times, identically on the last two. The
breaker tripped `NO_PROGRESS` rather than spending the remaining budget, and its
diagnosis was *"the rule is stated in a way that does not tell the generator what
to do instead."*

Reading the failing spec showed the fault was the gate's, not the generator's.
The Titan's breakable wall **divides the floor into two spans**, so the exit hall
stops being walkable from the main hall — and the gate reported that as
`spans 500, past the 380 guaranteed band`. A generator told the distance is wrong
moves things closer together, which cannot possibly help when a wall is what
separates them. It had misdiagnosed the room because the gate had.

The message now names the cause:

> `hall -> door_out spans 400, past the 380 guaranteed band — and the reason is
> 'ledge_1' standing between them, not the distance. Moving them closer cannot
> help; a wall the Titan breaks may not divide the critical path, because the
> Hunter has no verb for it. Route the path around it, or open the way through.`

Run 3 is the same brief against the same model with that one message changed:
2 softlocks → 1 → 1 → 1 → **PASS**.

That is the circuit breaker earning its place. It did not merely stop a loop; its
diagnosis named a defect in the evaluator, and repairing that is what let the
generator finish.

### The room the loop converged on

Run 1 took the harder brief and cleared it in three attempts — **6 softlocks → 1
→ PASS** — producing `room_segment_a_shaft_01`:

```
corridor 800×260  (tight: the jump is clipped, so no step of the route is jumped here)
   ↓
shaft 1600×1200   (three standard floors)
   step_1  x=700    step_2  x=1400    step_3  x=800
   step_4  x=1300   step_5  x=700          ← alternating, never stacked
   anchor_hunter (1800,1160) → perch → Grapple pocket
   ↓
east chamber 400×400, sealed by seal_east → Bash pocket
```

Both pockets are exclusive and visible from the route, no step leaves the
guaranteed band, and the body fits on every landing. This is the shape the rules
were written to force: the tight corridor carries no climb, and the climb
alternates because stacking is arithmetically impossible.

### The honest limitation

Run 3's accepted room is **simpler than its brief asked for**. Told to build a
climb, the generator satisfied the gate by moving the climb off the critical
path. That is not cheating — a pocket may not sit on the critical path, so it is
a correct reading — but it is what a loop like this does: a GER pipeline
converges on the *cheapest* thing the evaluator accepts. The evaluator can prove
a room is clearable. It cannot make a room ambitious, and nothing here should be
read as claiming otherwise.

---

## What was already there, and what this assignment added

The generator, the deterministic gate and a retry loop predate this assignment.
Three things are new, and each came from a failure that had already happened:

1. **Softlocks are separated from quality findings.** §7.1 is build-blocking and
   `ERR_UNIFORM_LEDGES` is not, and a flat error count hid that.
2. **The refiner sends the constraint, not the complaint** — scoped to the codes
   that fired.
3. **The circuit breaker replaces "run out of retries" with a diagnosis.** Three
   named ways of being stuck, each with the action a human should take.

## Running it

```bash
python3 agents/ger_rooms.py --brief "..." --attempts 5 --out R3_my_room
python3 agents/ger_rooms.py --replay production/output/R3_shaft.json
python3 -m pytest agents/test_ger_rooms.py agents/test_room_rules.py -q
```

`--replay` runs an existing spec through Evaluate → Refine → CircuitBreaker with
no model attached. Every path the breaker can take is covered by a test, because
a breaker that has only ever been watched succeed is a breaker nobody has seen
work.
