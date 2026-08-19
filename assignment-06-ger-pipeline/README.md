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

*The three required answers; also standing alone in `PRE-BUILD-DECLARATION.md`.
The blocker they describe was found in play on 10 August, before this pipeline
was designed around it.*

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

Six runs against agent `01-level-designer` on a subscription CLI, across two
generations of the rule set. Full transcripts in
`production/output/R3_ger_run*.ger.json`.

| Run | Rule set | Attempts | Outcome |
|---|---|---|---|
| 2 | v1 | 4 | **ESCALATED** — `NO_PROGRESS` |
| 3 | v1, after the evaluator fix below | 5 | **ACCEPTED** |
| 1 | v1, harder brief | 3 | **ACCEPTED** — later invalidated by v2 |
| 4 | v2 (two rules born from human play) | 5 | **ESCALATED** — `REGRESSION`; best attempt 1 error |
| 5 | v2, re-briefed | 5 | **ESCALATED** — `BUDGET`, improving 4→2→2→1→0 softlocks |
| 6 | v2, more budget | 3 | **ESCALATED** — `REGRESSION` |
| — | v2, run 4's best repaired by hand | — | **ACCEPTED**, then human-validated |

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

### When the rules tightened, the loop stopped converging — and said so usefully

After human play added two rules (next section), the same brief was run again
under the stricter gate. Three runs, three escalations — and each trip named a
different kind of stuck, which is the breaker doing its job rather than failing
at it:

- Run 4 tripped `REGRESSION` holding a best attempt **one error from passing**
  (the room stood 800 tall against a 1000 budget), with the anchor rules already
  satisfied.
- Run 5, re-briefed with the height named, tripped `BUDGET` while still
  improving — 4→2→2→1→0 softlocks — which is the one trip that says *spend more*.
- Run 6, given more budget and a fuller brief, tripped `REGRESSION` again.

At that point the `REGRESSION` playbook was followed as written: **keep the best
attempt and repair it by hand.** Run 4's best needed its shaft raised from two
floors to three and the climb extended to meet the ceiling. The repair is
declared, not hidden — and the gate rejected the first two attempts at it, for
ladder-shape, dead space, and a ceiling inside a jump arc: the same defects it
catches in the generator. **The gate does not know whether the author is a model,
and that is the point of a gate.** The third repair passed with zero findings and
became `room_segment_a_shaft_02`, in
`production/output/R3_ger_run4_repaired.json`.

---

## Human validation, on both sides of the boundary

The evaluator's verdicts were checked against play in both directions: a room it
rejects was walked to confirm the rejection is real, and rooms it accepted were
walked to confirm the acceptance holds. A gate validated only on rooms it
approves is a gate play can never contradict, so the pipeline includes a
**diagnostic mode** (`room_import.py --diagnose`) that builds a gate-rejected
room in a fixture level precisely so a human can experience the failure.

### The FAIL case, confirmed by its mechanism

`room_segment_a_bend_02` — approved by a human before these rules existed, 8
softlocks under the current gate — was walked in engine. (The superseded
approval record travels with this submission; its note, in the original Spanish,
ends *"la sala no se ha visto aún en el motor"* — the room has not yet been seen
in the engine. This walk answered it.)

| the gate's claim | what play found |
|---|---|
| 8 softlocks, `clearable = False` | "the ladder is a lock" |
| `ERR_NO_HEADROOM`: 160 of air for a 176 body | "the platforms aren't separated enough for the character to fit between them" |
| overhangs of 240–280 leave slivers uncovered | reached the third platform only "by exploiting small parts of the platforms" |
| `ERR_LADDER_CLIMB`: one repeated input | "that ladder is no fun at all" |

The tester stopped at the third ledge, and the slivers that allowed even that
are exactly the widths the overhang analysis reports as uncovered: the failure
was confirmed *by its mechanism*, not just its outcome.

### The first PASS case — held, and still taught the gate a rule

`room_segment_a_shaft_01`, run 1's accepted room, was walked next: the climb went
through first try, and the tight corridor read as intended. Two observations came
back that the gate had not made, and they are different in kind:

- **"Somewhat monotonous"** is a judgment about experience, not geometry. It
  belongs to the semantic review layer and the art pass; a deterministic
  evaluator should not pretend to hold an opinion about it.
- **The grapple anchor's perch hung 60 units under the ceiling** — visible,
  correctly out of jumping reach, and impossible to stand on. The Hunter would
  pull to the anchor and arrive nowhere. Reach, range and sight had all passed;
  *arrival* had never been asked about.

The second observation became two rules the same day. An anchor now makes three
promises at once — seen from the route, out of jumping reach, and **standable on
arrival** (`ERR_ANCHOR_NO_LANDING`: a surface at most 200 below the anchor with a
full body of clear space) — and a pocket's own surface must be standable
(`ERR_POCKET_NO_FOOTING`), because the headroom rules guard the critical path and
a pocket lives off it by definition. The contract's worked example carried the
same 60 units of air and is corrected: the third time a defect traced back to the
document teaching it.

### The final PASS case, validated

The repaired `room_segment_a_shaft_02` was then walked under the full rule set:
the six-step climb went through in one go, the anchor read as a place the Hunter
would land and stand, and the high return over the shelf read as a route rather
than a ladder. The tester's verdict: it meets everything asked of it. That room,
with that validation, is this pipeline's accepted output.

---

## What keeps yesterday's PASS from outliving its rules

Re-gating run 1's room exposed the last hole: the provenance record bound the
artifact's bytes but not the law they were judged under, so a PASS issued before
a rule existed walked through the importer while failing the current gate. Every
gate report now carries a **fingerprint of the rule set**
(`validators.rules_fingerprint()`), stamping records it, and the importer refuses
a verdict whose rules have changed since:

> `REFUSED — the validation rules have changed since this artifact was stamped,
> so its PASS was issued by a gate that no longer exists. Re-run the gate,
> re-stamp, and re-approve against the current rules.`

That refusal fired for real on its first exercise: the very room a human had just
validated was stopped at import an hour later, because the rules its PASS was
issued under had been superseded by what that validation found. The importer and
its tests travel under `importer/`.

---

## What was already there, and what this assignment added

The generator, the deterministic gate and a retry loop predate this assignment.
Five things are new, and each came from a failure that had already happened:

1. **Softlocks are separated from quality findings.** §7.1 is build-blocking and
   `ERR_UNIFORM_LEDGES` is not, and a flat error count hid that.
2. **The refiner sends the constraint, not the complaint** — scoped to the codes
   that fired.
3. **The circuit breaker replaces "run out of retries" with a diagnosis.** Three
   named ways of being stuck, each with the action a human should take — and each
   was exercised for real across the six runs above.
4. **Human validation on both sides of the boundary**, with a diagnostic mode
   that exists so play can contradict the gate; two of the evaluator's rules were
   born from it.
5. **The rules fingerprint**, so a verdict cannot outlive the gate that issued
   it.

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
