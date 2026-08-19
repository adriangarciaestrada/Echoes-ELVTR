#!/usr/bin/env python3
"""
Echoes — Generate / Evaluate / Refine pipeline for room geometry.

ELVTR "Multi-Agent AI for Game Development", assignment #6.

WHAT THIS GUARDS

`GDD-course-scope.md` §7.1 opens its acceptance bands with a hard, build-blocking
assertion:

    "Clearability = 100% — every class clears every room, branch, and boss at
     every bot profile; softlocks = 0."

A room whose critical path the character cannot physically walk IS a softlock,
and that is not a figure of speech: it was found by playing. A generated room
placed its ledges exactly the guaranteed jump apart, which every reach rule
approves, and stacked them directly above one another. Vertical spacing is
measured surface to surface, so a ledge 200 above the last, 40 thick, leaves 160
of air for a body that is 176 tall. The jump reached. The character did not fit.
Clearability was 0% and the generator, the gate and a human reviewer had all
signed it off.

The evaluator here refuses that class of room by arithmetic. See ERR_NO_HEADROOM,
ERR_CLIMB_BLOCKED, ERR_NO_WAY_THROUGH and ERR_JUMP_CLIPPED in REPAIR_GUIDANCE
below, each of which exists because a specific room shipped past the previous
gate and could not be traversed.

THE FOUR PARTS

    Generator       agent 01-level-designer, through a subscription CLI
    Evaluator       validators.validate_room — deterministic, no model
    Refiner         a repair brief scoped to the rules that actually failed
    CircuitBreaker  stops the loop when it is not converging, and says why

The refiner does not resend the raw error list. An error message states what is
wrong; a generator that keeps failing the same rule has not understood the rule.
So each failing code is answered with the constraint behind it and the measured
numbers it comes from, and only for the codes that fired.

The circuit breaker distinguishes three ways of stopping, because a human has to
do something different in each case: NO_PROGRESS means the prompt or the contract
needs work rather than another attempt; REGRESSION means refinement is making
things worse and the best attempt so far should be kept; BUDGET means the loop was
still improving and simply ran out of room.

USAGE

    python3 agents/ger_rooms.py --brief "A tight corridor opening into a shaft"
    python3 agents/ger_rooms.py --brief "..." --attempts 5
    python3 agents/ger_rooms.py --replay production/output/R3_shaft.json

`--replay` runs a spec that already exists through Evaluate → Refine →
CircuitBreaker without calling a model, so the loop can be demonstrated and
tested at no cost. `--dry-run` does the same with a scripted generator.
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "agents"))

import room_rules as rr          # noqa: E402
import validators                # noqa: E402

OUTPUT_DIR = BASE_DIR / "production" / "output"

# --------------------------------------------------------------------------
# Which failures are §7.1 softlocks
# --------------------------------------------------------------------------
# Every code below describes a room a player cannot get through. They are
# separated from the rest of the gate's codes because they alone break the
# build-blocking assertion, and the report has to say so plainly rather than
# reporting "12 errors" and leaving a human to work out which ones matter.
CLEARABILITY_CODES = {
    "ERR_UNREACHABLE",      # a step past the guaranteed reach band
    "ERR_NO_HEADROOM",      # nowhere on the surface to stand up
    "ERR_CLIMB_BLOCKED",    # the next ledge overhangs the one being jumped from
    "ERR_NO_WAY_THROUGH",   # standing room on both sides of an obstruction
    "ERR_JUMP_CLIPPED",     # the ceiling takes the jump the step needs
    "ERR_PATH_GATED",       # the route needs a tool, so one class is locked out
    "ERR_NO_RUNUP",         # not enough floor to reach speed before a gap
    "ERR_DOOR_UNREACHABLE",
    "ERR_ONE_WAY_DROP",     # a descent the player cannot come back from
    "ERR_NOT_CONNECTABLE",
}


def _n(value: float) -> str:
    return f"{value:g}"


# --------------------------------------------------------------------------
# What the generator is told when a rule fails
# --------------------------------------------------------------------------
# Keyed by error code. The numbers are read from room_rules rather than typed
# here, so re-tuning the character cannot leave the teaching text describing a
# character the game no longer has.
REPAIR_GUIDANCE: Dict[str, str] = {
    "ERR_NO_HEADROOM": (
        f"The character is {_n(rr.CAPSULE_HEIGHT)} tall and {_n(2 * rr.CAPSULE_RADIUS)} wide, and needs "
        f"{_n(rr.HEADROOM)} of clear space above a surface to stand on it. Vertical spacing is measured "
        f"surface to surface, so the platform above eats its own thickness out of that space: two ledges "
        f"{_n(rr.RISE_GUARANTEED)} apart and 40 thick leave only 160, and the body does not fit. Raise what "
        f"is above, or lower the surface."
    ),
    "ERR_CLIMB_BLOCKED": (
        "A climb alternates; it does not stack. Never place a step of the critical path directly above the "
        "previous one. Standing clear of an overhanging ledge means jumping almost straight up, and arriving "
        f"over it costs {_n(2 * rr.CAPSULE_RADIUS)} of sideways travel the jump has no height left to buy. "
        f"Since headroom of {_n(rr.HEADROOM)} under a rise of at most {_n(rr.RISE_GUARANTEED)} would demand a "
        "platform of zero thickness, stacking cannot be made to work by adjusting numbers. Offset each ledge "
        "to the other side of the shaft, which also means a shaft must be wide enough for two ledges side by side."
    ),
    "ERR_NO_WAY_THROUGH": (
        "Somewhere to stand is not a way past. A ledge hanging low over a floor leaves both sides perfectly "
        "standable and the route between them shut. Check the stretch the route actually crosses, not the "
        "widest clear stretch on the surface."
    ),
    "ERR_JUMP_CLIPPED": (
        f"A jumping character occupies {_n(rr.JUMPING_HEIGHT)} — {_n(rr.CAPSULE_HEIGHT)} of body plus "
        f"{_n(rr.JUMP_APEX)} of jump. A tight corridor ({_n(rr.TIGHT)}) clips that on purpose, which is what "
        "makes it claustrophobic, so a tight corridor carries no step that has to be jumped. Put the climb in "
        f"a standard floor ({_n(rr.FLOOR)}) or taller."
    ),
    "ERR_UNREACHABLE": (
        f"The critical path is the clearability promise, so every step on it stays inside the guaranteed band: "
        f"at most {_n(rr.RISE_GUARANTEED)} up and {_n(rr.GAP_GUARANTEED)} across. The skill band above that is "
        "for optional content, never for the way forward."
    ),
    "ERR_NO_RUNUP": (
        f"Speed is not free. A gap needs {_n(rr.RUNUP_MIN)} of level floor before it to reach full speed, and a "
        f"breakable wall needs {_n(rr.BASH_RUNUP)} — the bash only breaks at speed, so a cracked wall with no "
        "run-up is sealed to everyone."
    ),
    "ERR_PATH_GATED": (
        "A traverse key opens a reward or a side room, never the way forward. No door on the critical path may "
        "require a tool, and no pocket may sit on it. A gated route does not make the room harder; it locks one "
        "class out of the game, which contradicts the slice's whole thesis."
    ),
    "ERR_OFF_MODULE": (
        f"Heights are not chosen per room. Every carved space is either a tight corridor ({_n(rr.TIGHT)}) or a "
        f"whole number of standard floors ({_n(rr.FLOOR)}, {_n(2 * rr.FLOOR)}, {_n(3 * rr.FLOOR)}...), and "
        f"standing surfaces sit on half-floors — multiples of {_n(rr.HALF_FLOOR)} — so that one landing carries "
        "one floor of climb. A height that is nearly standard teaches the player only that heights are arbitrary."
    ),
    "ERR_POCKET_NOT_EXCLUSIVE": (
        "A pocket base movement can already reach is not a pocket. It must be reachable no other way than by its "
        "class key."
    ),
    "ERR_POCKET_UNSEEN": (
        "A pocket nobody sees teaches nothing. What must be visible from the critical path is the LOCK — the "
        "anchor, the cracked wall — not the reward, which stays occluded by whatever holds it."
    ),
    "ERR_ANCHOR_UNUSABLE": (
        f"An anchor is only a key if it can be used: within {_n(rr.GRAPPLE_RANGE)} of somewhere the character can "
        "stand, with a clear line to it."
    ),
    "ERR_IN_ROCK": (
        "A room is solid material with a cavity carved out of it. Everything placed — solids, anchors, doors, "
        "pockets — sits inside the cavity union. Anything outside it is rock."
    ),
    "ERR_OFF_GRID": (
        "Every coordinate is a multiple of the grid (default 20). Rectilinear geometry on a grid is what keeps "
        "irregular outlines readable and the arithmetic exact."
    ),
    "ERR_ANCHOR_NO_LANDING": (
        f"An anchor is a destination, not only a target: the pull ends at the anchor and the Hunter "
        f"comes down onto whatever is underneath. There must be a surface at most "
        f"{_n(rr.LANDING_DROP_MAX)} below the anchor, with {_n(rr.HEADROOM)} of clear space and a "
        f"body's width to stand on. An anchor over a void, or over a perch pinned under the ceiling, "
        "strands the class it exists for."
    ),
    "ERR_POCKET_NO_FOOTING": (
        f"A reward the right class cannot stand next to is not a reward. The surface a pocket sits on "
        f"needs {_n(rr.HEADROOM)} of clear space above it — the headroom rules guard the critical "
        "path, and a pocket lives off it by definition, so its footing is checked separately."
    ),
    "ERR_LADDER_CLIMB": (
        "A climb that shuffles between two positions is a ladder: the player repeats one input and sees the "
        "same view from every landing. Send the climb across the room, and carve the cavity wide enough to "
        "let it travel — the shape of the route is the room's content."
    ),
    "ERR_UNIFORM_LEDGES": (
        "Width is meaning. A wide ledge is a place to stop and fight, a narrow one is a beat of precision. "
        "Platforms that are all the same width say nothing about what happens on them."
    ),
    "ERR_DEAD_SPACE": (
        f"A gap under a platform that the character cannot enter reads as an oversight rather than a secret. "
        f"Either fill it down so it becomes a step, or raise it until the space below clears "
        f"{_n(rr.HEADROOM)} and can be used."
    ),
    "ERR_ONE_WAY_DROP": (
        f"A drop the player cannot climb back out of commits them with no way to return, which is a softlock "
        f"unless the room is deliberately one-way. Only {_n(rr.RISE_GUARANTEED)} can be climbed back, so break "
        "the fall into landings inside that band."
    ),
    "ERR_ARCHETYPE_NEEDS_HEIGHT": (
        f"The corridor decides what may fight in it. A Shieldbearer is passed over or through, so under a clipped "
        f"jump it stops being a choice and becomes a wall only the Titan opens. A Ledge Gunner needs a ledge that "
        f"does not fit. Both require a standard floor ({_n(rr.FLOOR)}) or taller."
    ),
}

GENERIC_GUIDANCE = (
    "Re-read the injected contract for this field and conform to it exactly rather than to a remembered format."
)


# --------------------------------------------------------------------------
# Evaluator
# --------------------------------------------------------------------------
@dataclass
class Verdict:
    """One deterministic judgment of one candidate room."""
    softlocks: List[Dict] = field(default_factory=list)   # §7.1 violations
    other_errors: List[Dict] = field(default_factory=list)
    warnings: List[Dict] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.softlocks and not self.other_errors

    @property
    def clearable(self) -> bool:
        """Whether the room satisfies the build-blocking assertion specifically."""
        return not self.softlocks

    @property
    def error_count(self) -> int:
        return len(self.softlocks) + len(self.other_errors)

    def signature(self) -> Tuple:
        """What makes two attempts 'the same failure'.

        Code and location, not message: a generator that moves a ledge by ten
        units and fails the identical rule in the identical place has not made
        progress, and the message may well have changed anyway because it quotes
        the new numbers.
        """
        return tuple(sorted((e["code"], e.get("path", "")) for e in self.softlocks + self.other_errors))


class Evaluator:
    """The deterministic gate. No model runs here, and that is the point.

    Reach, fit, budgets and exclusivity are arithmetic. Asking a language model
    to check arithmetic costs money to get a less reliable answer, and the
    project's own experience is that a reviewer agent asked to judge reachability
    produced 'cannot verify' as its most frequent finding.
    """

    kind = "room"

    def evaluate(self, spec: Dict) -> Verdict:
        errors = validators.validate_room(spec)
        verdict = Verdict()
        for e in errors:
            if not e["code"].startswith("ERR_"):
                verdict.warnings.append(e)
            elif e["code"] in CLEARABILITY_CODES:
                verdict.softlocks.append(e)
            else:
                verdict.other_errors.append(e)
        return verdict


# --------------------------------------------------------------------------
# Refiner
# --------------------------------------------------------------------------
class Refiner:
    """Turns a verdict into a repair brief scoped to what actually failed.

    Two rules govern what goes in it. Only the codes that fired are explained,
    because a generator handed the whole contract again will re-read the parts it
    already satisfied and is no more likely to fix the part it did not. And each
    code is answered with the constraint and its measured numbers rather than the
    error text alone, because the error says a room is wrong while the constraint
    says what would make it right.
    """

    def brief(self, verdict: Verdict, attempt: int) -> str:
        lines = [
            f"YOUR PREVIOUS ROOM FAILED DETERMINISTIC VALIDATION (attempt {attempt}).",
            "",
        ]
        if verdict.softlocks:
            lines += [
                "THESE ARE SOFTLOCKS. GDD-course-scope.md §7.1 states 'Clearability = 100% — every class "
                "clears every room; softlocks = 0' as a hard, build-blocking assertion. A room the character "
                "cannot physically traverse cannot enter the game under any circumstances.",
                "",
            ]
        for label, group in (("SOFTLOCK", verdict.softlocks), ("ERROR", verdict.other_errors)):
            for e in group:
                lines.append(f"[{label}] {e['code']} at {e.get('path') or '(room)'}")
                lines.append(f"    what the gate measured: {e['message']}")
                lines.append(f"    the rule behind it: {REPAIR_GUIDANCE.get(e['code'], GENERIC_GUIDANCE)}")
                lines.append("")
        lines += [
            "Correct exactly these. Do not restructure the parts that passed — every other rule was already "
            "satisfied and a rewrite risks breaking one. Re-emit ONLY the corrected JSON object.",
        ]
        return "\n".join(lines)


# --------------------------------------------------------------------------
# Circuit breaker
# --------------------------------------------------------------------------
@dataclass
class Trip:
    reason: str
    diagnosis: str
    human_action: str


class CircuitBreaker:
    """Stops a loop that cannot fix itself, and says which kind of stuck it is.

    Running the retry budget to the end is not a decision, it is the absence of
    one. These three outcomes need three different responses from a human, so
    they are reported as three different things.
    """

    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts
        self.history: List[Verdict] = []

    def record(self, verdict: Verdict) -> None:
        self.history.append(verdict)

    @property
    def best(self) -> Optional[Verdict]:
        if not self.history:
            return None
        return min(self.history, key=lambda v: (len(v.softlocks), v.error_count))

    def check(self) -> Optional[Trip]:
        """Return a Trip if the loop must stop, or None to keep going."""
        if not self.history:
            return None
        latest = self.history[-1]
        if latest.passed:
            return None

        # Not converging: the identical rule failed in the identical place twice
        # running. Another attempt asks the same question and will be told the
        # same thing; what needs changing is the prompt or the contract.
        if len(self.history) >= 2 and latest.signature() == self.history[-2].signature():
            codes = sorted({e["code"] for e in latest.softlocks + latest.other_errors})
            return Trip(
                reason="NO_PROGRESS",
                diagnosis=(
                    f"attempt {len(self.history)} failed exactly as attempt {len(self.history) - 1} did: "
                    f"{', '.join(codes)}. The generator is not able to act on this rule as it is written."
                ),
                human_action=(
                    "Do not raise the retry budget — it will buy identical output. Either the rule is not "
                    "stated in the injected contract, or it is stated in a way that does not tell the "
                    "generator what to do instead. Read the guidance for these codes in REPAIR_GUIDANCE and "
                    "put the missing half in the vault note the agent loads."
                ),
            )

        # Getting worse, twice running. One worsening step is ordinary search —
        # a generator moving geometry to satisfy one rule will routinely break
        # another on the way — so tripping on the first would throw away loops
        # that recover. Two in a row is a trend, and the budget is better spent
        # on a human than on a third.
        #
        # Worse is judged on softlocks first and total errors second, because
        # §7.1 is build-blocking and an off-grid coordinate is not. Trading five
        # cosmetic fixes for one more softlock is a step backwards even though
        # the error count fell.
        def rank(v):
            return (len(v.softlocks), v.error_count)

        prior = self.history[:-1]
        if len(prior) >= 2:
            best_before_last = min(prior[:-1], key=rank)
            regressed_now = rank(latest) > rank(best_before_last)
            regressed_last = rank(prior[-1]) > rank(best_before_last)
            if regressed_now and regressed_last:
                best = min(prior, key=rank)
                return Trip(
                    reason="REGRESSION",
                    diagnosis=(
                        f"attempts {len(self.history) - 1} and {len(self.history)} were both worse than "
                        f"attempt {self.history.index(best_before_last) + 1}: "
                        f"{len(latest.softlocks)} softlock(s) and {latest.error_count} error(s) now, against "
                        f"{len(best_before_last.softlocks)} and {best_before_last.error_count} then "
                        "(softlocks outrank other errors, since only they block the build). Fixing one rule "
                        "is repeatedly breaking another."
                    ),
                human_action=(
                    "Keep the best attempt, which is saved beside the report, and repair it by hand or "
                    "re-brief with the two rules named together. Rules that cannot both be satisfied by "
                    "moving the same geometry usually mean the room's dimensions are wrong, not its contents."
                ),
            )

        if len(self.history) >= self.max_attempts:
            return Trip(
                reason="BUDGET",
                diagnosis=(
                    f"{self.max_attempts} attempts spent and still failing, but each attempt differed from "
                    "the last, so the loop was still working."
                ),
                human_action=(
                    "This one is worth more budget: re-run with a higher --attempts. If it stops improving "
                    "the breaker will trip on NO_PROGRESS instead, which is the signal to change the prompt."
                ),
            )
        return None


# --------------------------------------------------------------------------
# Generators
# --------------------------------------------------------------------------
class AgentGenerator:
    """The real generator: agent 01-level-designer over a subscription CLI.

    Imported lazily so that the loop, the evaluator, the refiner and the breaker
    can all be exercised and tested without a CLI, a login, or a token.
    """

    name = "01-level-designer"

    def __init__(self, timeout: int = 900):
        import runner
        self.runner = runner
        self.timeout = timeout
        self.agent, self.system_prompt, self.info, notes = runner.load_agent_spec("01-level-designer")
        _, self.vault_context = runner.build_context(notes, None)

    def generate(self, brief: str, repair: Optional[str]) -> Optional[Dict]:
        prompt = f"CONTEXT FROM VAULT:\n{self.vault_context}\n\nTASK INSTRUCTION:\n{brief}"
        if repair:
            prompt += "\n\n" + repair
        raw, usage = self.runner.dispatch(self.info, self.system_prompt, prompt, self.timeout)
        self.runner.log_usage(self.agent, self.info["model"], usage)
        return self.runner.extract_json(raw)


class ReplayGenerator:
    """Feeds an existing spec in, then hands back scripted variants.

    Its purpose is to make the other three components testable. A pipeline whose
    failure handling can only be observed by spending money on a model is a
    pipeline whose failure handling does not get observed.
    """

    name = "replay"

    def __init__(self, spec_path: Path, variants: Optional[List[Dict]] = None):
        self.spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
        self.variants = variants or []
        self.calls = 0

    def generate(self, brief: str, repair: Optional[str]) -> Optional[Dict]:
        if self.calls == 0:
            out = self.spec
        elif self.variants:
            out = self.variants[min(self.calls - 1, len(self.variants) - 1)]
        else:
            out = self.spec          # unchanged: the loop should notice and stop
        self.calls += 1
        return out


# --------------------------------------------------------------------------
# The loop
# --------------------------------------------------------------------------
def run(generator, brief: str, max_attempts: int, out_prefix: Optional[str] = None,
        quiet: bool = False) -> Dict:
    evaluator = Evaluator()
    refiner = Refiner()
    breaker = CircuitBreaker(max_attempts)

    def say(*a):
        if not quiet:
            print(*a)

    say(f"\nGENERATE → EVALUATE → REFINE   ·   generator: {generator.name}   ·   budget: {max_attempts}")
    say(f"brief: {brief}\n")

    repair: Optional[str] = None
    accepted: Optional[Dict] = None
    best_spec: Optional[Dict] = None
    trip: Optional[Trip] = None

    for attempt in range(1, max_attempts + 1):
        spec = generator.generate(brief, repair)
        if spec is None:
            verdict = Verdict(other_errors=[{
                "code": "ERR_INVALID_JSON",
                "message": "the generator did not return parseable JSON",
                "path": ""}])
        else:
            verdict = evaluator.evaluate(spec)

        breaker.record(verdict)
        # Keep the best *room*, which an unparseable attempt is not, however few
        # findings it collected — there is nothing there for a human to repair.
        if spec is not None and breaker.best is verdict:
            best_spec = spec

        status = "PASS" if verdict.passed else (
            f"FAIL — {len(verdict.softlocks)} softlock(s), {len(verdict.other_errors)} other error(s)")
        say(f"  attempt {attempt}/{max_attempts}: {status}")
        for e in verdict.softlocks:
            say(f"      SOFTLOCK  {e['code']} @ {e.get('path') or '(room)'}: {e['message'][:110]}")
        for e in verdict.other_errors:
            say(f"      error     {e['code']} @ {e.get('path') or '(room)'}: {e['message'][:110]}")

        if verdict.passed:
            accepted = spec
            break

        trip = breaker.check()
        if trip:
            break
        repair = refiner.brief(verdict, attempt)
        say(f"      → refining: {len(verdict.softlocks) + len(verdict.other_errors)} rule(s) explained back "
            "to the generator")

    report = {
        "brief": brief,
        "generator": generator.name,
        "attempts": len(breaker.history),
        "budget": max_attempts,
        "status": "ACCEPTED" if accepted else "ESCALATED",
        "clearable": bool(accepted) or (breaker.best.clearable if breaker.best else False),
        "history": [
            {"attempt": i + 1,
             "softlocks": [e["code"] for e in v.softlocks],
             "other_errors": [e["code"] for e in v.other_errors],
             "warnings": len(v.warnings)}
            for i, v in enumerate(breaker.history)
        ],
    }
    if trip:
        report["circuit_breaker"] = {
            "tripped": trip.reason,
            "diagnosis": trip.diagnosis,
            "human_action": trip.human_action,
        }

    if accepted:
        say(f"\nACCEPTED after {len(breaker.history)} attempt(s). "
            "Clearability holds: no step of the critical path is closed to either class.")
    else:
        reason = trip.reason if trip else "BUDGET"
        say(f"\nESCALATED — circuit breaker tripped: {reason}")
        if trip:
            say(f"  diagnosis:  {trip.diagnosis}")
            say(f"  what to do: {trip.human_action}")
        say("  Nothing was written to the project. An unclearable room is not a build problem to "
            "work around; it is a room that must not exist.")

    if out_prefix:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = OUTPUT_DIR / f"{out_prefix}.ger.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        say(f"\n  report: {report_path}")
        keep = accepted or best_spec
        if keep is not None:
            spec_path = OUTPUT_DIR / f"{out_prefix}.json"
            spec_path.write_text(json.dumps(keep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            say(f"  {'room' if accepted else 'best failing attempt'}: {spec_path}")

    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[1])
    p.add_argument("--brief", help="what the room should be")
    p.add_argument("--attempts", type=int, default=3, help="retry budget (default 3)")
    p.add_argument("--replay", metavar="SPEC", help="run an existing spec through the loop, no model")
    p.add_argument("--out", metavar="PREFIX", help="write the report and room under production/output")
    p.add_argument("--timeout", type=int, default=900)
    args = p.parse_args()

    if args.replay:
        generator = ReplayGenerator(Path(args.replay))
        brief = args.brief or f"replay of {Path(args.replay).name}"
    else:
        if not args.brief:
            p.error("--brief is required unless --replay is given")
        generator = AgentGenerator(args.timeout)
        brief = args.brief

    report = run(generator, brief, args.attempts, args.out)
    return 0 if report["status"] == "ACCEPTED" else 1


if __name__ == "__main__":
    sys.exit(main())
