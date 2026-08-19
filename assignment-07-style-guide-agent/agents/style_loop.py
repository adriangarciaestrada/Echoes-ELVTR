#!/usr/bin/env python3
"""
Echoes — Generate / Evaluate / Refine loop for the game's style guide.

ELVTR "Multi-Agent AI for Game Development", assignment #7.

WHAT IT ENFORCES

Three constraint types, each read live from the contract that owns it rather
than restated here. A style rule copied into a second place is a rule that will
eventually disagree with itself, and the one that gets obeyed is whichever the
reader happened to open.

  1. VOCABULARY & IP   vault/00-core/terminology-guard.md
     Working Destiny placeholders are banned from all shipped text and each has
     one approved replacement: Traveler/Light -> Architects/Weave, Ghost ->
     Beacon, Hive/Vex/Fallen -> Remnants/Facets, Witch -> La Costurera,
     Guardians -> Weavers. The ban is on the CAPITAL, not the word: "Light" is
     the placeholder, "light" is a noun. A second table bans naming the setting's
     country or its off-allowlist iconography — the place is recognised, never
     announced.

  2. TONE               vault/05-lore/architects-cosmology.md
     "Sci-fi melancholic, ancient architectural mystery, cryptic yet diegetically
     grounded." A civilisation that wove reality and left silent, decaying
     structures. Nothing cheerful, nothing that addresses the player as a player.

  3. FORMAT & LENGTH    vault/07-ui-and-controls/ui-budgets.md
     Per-widget-class character caps, applied to English and Spanish
     independently, plus the Spanish overflow allowance. Spanish runs longer, so
     it is the language that decides whether a string fits.

THE LOOP

    Generator  -> writes a candidate string for a named widget class
    Evaluator  -> SCORE 1-10 + REASON, per rule, against the guide
    Refiner    -> takes the REASON and rewrites to clear it

No human intervenes. The loop runs until the score reaches the threshold or the
attempt budget is spent.

WHY THE JUDGE IS HANDED EVIDENCE

This project's standing preference is deterministic check > LLM judge with an
explicit rubric > LLM judge with a vague prompt. A score is not a deterministic
check, so the two are composed rather than chosen between: the exact, countable
half — banned capitals, region leaks, character counts — is measured in Python
first and handed to the judge as findings it must account for. The judge owns
the score, as it must, but it cannot invent a vocabulary violation that is not
there or miss one that is, and its reason is anchored to something checkable.
Tone, which no regex reaches, is the judge's alone.

USAGE

    python3 agents/style_loop.py --brief "A menu label for abandoning the run"
    python3 agents/style_loop.py --demo            # the three violation classes
    python3 agents/style_loop.py --demo --out A7   # ...and write the transcript
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "agents"))

import ui_rules      # noqa: E402
import validators    # noqa: E402

VAULT = BASE_DIR / "vault"
OUTPUT_DIR = BASE_DIR / "production" / "output"

PASS_SCORE = 9          # out of 10; below this the refiner runs again
MAX_ATTEMPTS = 3

TONE_NOTE = VAULT / "05-lore" / "architects-cosmology.md"
TERMS_NOTE = VAULT / "00-core" / "terminology-guard.md"
BUDGET_NOTE = VAULT / "07-ui-and-controls" / "ui-budgets.md"


# --------------------------------------------------------------------------
# The style guide, assembled from the contracts that own each rule
# --------------------------------------------------------------------------
def _tone_statement() -> str:
    """The narrative tone, quoted from the lore note rather than paraphrased."""
    text = TONE_NOTE.read_text(encoding="utf-8")
    match = re.search(r"##\s*Narrative Tone\s*\n(.+?)(?:\n##|\Z)", text, re.S)
    return match.group(1).strip() if match else "sci-fi melancholic"


def _term_table() -> List[str]:
    """Banned placeholder -> approved term, as the guard states them."""
    rows = []
    for line in TERMS_NOTE.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) >= 2 and cells[0] and not cells[0].startswith("-") \
                and "Banned Destiny" not in cells[0]:
            if cells[1] and "Required" not in cells[1]:
                # The note is written for humans and marks the approved column in
                # bold; a prompt has no use for the asterisks.
                rows.append(f"{cells[0]}  ->  {cells[1].replace('**', '')}")
        if "Banned Region" in line:
            break
    return rows


def style_guide(widget_class: Optional[str] = None) -> str:
    """The prompt-side guide. Every clause traces to a vault note."""
    terms = _term_table()
    cap = ui_rules.cap_for(widget_class) if widget_class else None
    denylist = ", ".join(sorted(ui_rules.load_region_denylist())[:10])

    guide = [
        "THE ECHOES STYLE GUIDE",
        "",
        "Echoes is a 2.5D metroidvania. An ancient non-human civilisation, the ARCHITECTS,",
        "wove reality from luminous threads called the WEAVE, and left colossal stone and",
        "metal structures now silent and decaying. Their automated constructs still haunt",
        "the corridors. The player is a Weaver of one of two classes, Hunter or Titan, and",
        "the slice ends at LA COSTURERA, an alien witch who re-stitches the knights she",
        "commands.",
        "",
        "RULE 1 — VOCABULARY AND IP (vault/00-core/terminology-guard.md)",
        "The world must feel Destiny-adjacent and ship legally clean. These working",
        "placeholders are PROHIBITED in shipped text; each has exactly one replacement:",
    ]
    guide += [f"    {row}" for row in terms]
    guide += [
        "The ban is on the CAPITALISED form, matched case-sensitively: 'Light' is the",
        "placeholder and is banned; 'light' is an ordinary noun and is fine.",
        "",
        "The setting's country is never named, in either language, and its off-allowlist",
        f"iconography is never invoked. Banned outright: {denylist}.",
        "The place is carried by geology, light, vegetation and plausible toponymy.",
        "",
        "RULE 2 — TONE (vault/05-lore/architects-cosmology.md)",
        f"    {_tone_statement()}",
        "Consequences: no cheerfulness, no exclamation marks, no congratulating the",
        "player, no addressing them as a player or as a gamer, no marketing register, no",
        "modern casual idiom. The text speaks from inside the world or not at all.",
        "",
        "RULE 3 — FORMAT AND LENGTH (vault/07-ui-and-controls/ui-budgets.md)",
        "Every string is authored in BOTH English and Spanish, and the cap applies to each",
        "language independently. Spanish runs longer, so it is the language that decides",
        "whether a string fits.",
    ]
    if cap is not None:
        guide.append(f"    This string is a '{widget_class}': hard cap {cap} characters, each language.")
    guide += [
        "    Interface text carries no terminal punctuation and no ALL CAPS shouting.",
        "    A key is written ST_UI.<Name>; the text never contains the key.",
    ]
    return "\n".join(guide)


# --------------------------------------------------------------------------
# Deterministic findings — the evidence the judge must account for
# --------------------------------------------------------------------------
def measure(record: Dict, widget_class: str) -> List[Dict]:
    """The countable half of the guide, checked in Python.

    Not a verdict. These become evidence in the evaluator's prompt so its score
    rests on measured facts rather than on impressions of them.
    """
    findings: List[Dict] = []
    terms = validators.load_banned_and_approved()

    for lang in ("text_en", "text_es"):
        text = record.get(lang) or ""
        hits, _ = validators.ip_term_hits(text, terms["banned"])
        for hit in hits:
            findings.append({"rule": "vocabulary", "field": lang,
                             "detail": f"banned placeholder {hit!r} appears in shipped text"})
        leak = ui_rules.region_leak(text)
        if leak:
            findings.append({"rule": "vocabulary", "field": lang,
                             "detail": f"region reference {leak!r}; the country is never named"})
        # over_cap returns the cap that was exceeded, not the overage; the
        # number a writer needs is how much has to go.
        cap = ui_rules.over_cap(widget_class, text)
        if cap:
            findings.append({"rule": "length", "field": lang,
                             "detail": f"{len(text)} characters against a cap of {cap} "
                                       f"for {widget_class} — {len(text) - cap} to cut"})
        for glyph in ui_rules.glyph_literals(text):
            findings.append({"rule": "format", "field": lang,
                             "detail": f"literal glyph {glyph!r}; buttons are named by token"})

    en, es = record.get("text_en") or "", record.get("text_es") or ""
    if en and es and not ui_rules.es_within_budget(en, es):
        findings.append({"rule": "length", "field": "text_es",
                         "detail": f"Spanish is {len(es)} against English {len(en)}, past the "
                                   f"allowance of {ui_rules.es_allowance(en)}"})
    return findings


# --------------------------------------------------------------------------
# The three agents
# --------------------------------------------------------------------------
class Llm:
    """One subscription-backed model call. Loaded lazily so tests need no CLI."""

    def __init__(self, provider: str = "claude", model: str = "claude-haiku-4-5",
                 timeout: int = 300):
        import runner
        self.runner = runner
        self.info = {"provider": provider, "model": model, "name": "style-loop"}
        self.timeout = timeout

    def __call__(self, system_prompt: str, user_prompt: str) -> str:
        raw, usage = self.runner.dispatch(self.info, system_prompt, user_prompt, self.timeout)
        self.runner.log_usage("style-loop", self.info["model"], usage)
        return raw


GENERATOR_SYSTEM = """You write user-facing text for the game Echoes.

Emit ONLY a JSON object, no prose around it:
{"key": "ST_UI.<Name>", "widget_class": "<class>", "text_en": "...", "text_es": "..."}

Both languages are authored, not translated: write the Spanish as Spanish rather
than as English wearing Spanish."""

EVALUATOR_SYSTEM = """You are the Style Evaluator for the game Echoes.

You grade one piece of text against the style guide you are given. You do not
rewrite it and you do not soften your judgment.

A deterministic checker has already measured the countable rules and its findings
are in your input. Treat them as facts: every finding is a real violation and
must appear in your reason. They do not cover TONE, which is yours alone to
judge, and they may miss a disguised violation — a placeholder rephrased rather
than removed still breaks Rule 1.

Score out of 10, where 10 is text that could ship today:
  10      every rule met, and the tone is right rather than merely inoffensive
  8-9     no rule broken; tone slightly off, or wording forgettable
  5-7     one rule broken, or the tone belongs to a different game
  1-4     several rules broken, or the text is off-brand at the concept level

Any banned placeholder, any region reference, or any string over its cap keeps
the score at 6 or below no matter how good the writing is: those three ship
broken.

Output EXACTLY this shape and nothing else:

SCORE: [X/10]
REASON: [What is wrong, rule by rule, naming the offending words and the numbers.
Be specific enough that a rewriter can act on it without seeing the guide. If
nothing is wrong, say what makes the text right rather than padding.]"""

REFINER_SYSTEM = """You are the Style Refiner for the game Echoes.

You receive a piece of text, the style guide, and an evaluator's reason. Rewrite
the text so it would score 10/10.

Rules of the rewrite:
- Fix every violation the reason names. Do not fix only the easy ones.
- Keep the string's PURPOSE — the same widget, the same thing communicated. A
  rewrite that solves a length problem by discarding the meaning has failed.
- Replace banned placeholders with their approved terms; do not merely delete
  them and leave a sentence that says less.
- Author the Spanish as Spanish. Spanish runs longer, so if a cap is the problem
  it is usually the Spanish that has to be re-thought, not padded down.

Emit ONLY the corrected JSON object, in the same shape as the input."""


def parse_verdict(raw: str) -> Dict:
    """Pull SCORE and REASON out of the evaluator's reply."""
    score = None
    match = re.search(r"SCORE:\s*\[?\s*(\d+(?:\.\d+)?)\s*/\s*10\s*\]?", raw, re.I)
    if match:
        score = float(match.group(1))
    reason = ""
    match = re.search(r"REASON:\s*\[?(.+?)\]?\s*$", raw, re.I | re.S)
    if match:
        reason = match.group(1).strip()
    return {"score": score, "reason": reason, "raw": raw.strip()}


def extract_record(raw: str) -> Optional[Dict]:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except ValueError:
        return None


# --------------------------------------------------------------------------
# The loop
# --------------------------------------------------------------------------
@dataclass
class Round:
    attempt: int
    record: Dict
    findings: List[Dict]
    score: Optional[float]
    reason: str


def evaluate(llm: Llm, record: Dict, widget_class: str) -> Round:
    findings = measure(record, widget_class)
    evidence = ("DETERMINISTIC FINDINGS (facts, already measured):\n"
                + ("\n".join(f"  - [{f['rule']}] {f['field']}: {f['detail']}" for f in findings)
                   if findings else "  (none — the countable rules are all met)"))
    prompt = (f"{style_guide(widget_class)}\n\n{evidence}\n\n"
              f"TEXT UNDER REVIEW:\n{json.dumps(record, ensure_ascii=False, indent=2)}")
    verdict = parse_verdict(llm(EVALUATOR_SYSTEM, prompt))
    return Round(0, record, findings, verdict["score"], verdict["reason"])


def run(brief: str, widget_class: str, llm: Llm, seed: Optional[Dict] = None,
        max_attempts: int = MAX_ATTEMPTS, quiet: bool = False) -> Dict:
    """Generate, then evaluate and refine until the score clears the bar."""
    def say(*a):
        if not quiet:
            print(*a)

    if seed is None:
        raw = llm(GENERATOR_SYSTEM, f"{style_guide(widget_class)}\n\nWRITE: {brief}")
        record = extract_record(raw)
        if record is None:
            raise SystemExit("[style_loop] the generator returned no parseable JSON")
    else:
        record = dict(seed)
    record.setdefault("widget_class", widget_class)

    say(f"\nGENERATE → EVALUATE → REFINE   ·   {widget_class}   ·   pass mark {PASS_SCORE}/10")
    say(f"brief: {brief}\n")

    rounds: List[Round] = []
    for attempt in range(1, max_attempts + 1):
        r = evaluate(llm, record, widget_class)
        r.attempt = attempt
        rounds.append(r)
        say(f"  attempt {attempt}: EN {record.get('text_en')!r}")
        say(f"              ES {record.get('text_es')!r}")
        say(f"     SCORE {r.score}/10")
        for f in r.findings:
            say(f"       measured  [{f['rule']}] {f['field']}: {f['detail']}")
        say(f"     REASON {r.reason[:300]}")

        if r.score is not None and r.score >= PASS_SCORE:
            say(f"\n  ACCEPTED at {r.score}/10 after {attempt} attempt(s).")
            break
        if attempt == max_attempts:
            say(f"\n  STOPPED at the budget with {r.score}/10. Handing the last reason to a human.")
            break

        say("     → refining\n")
        prompt = (f"{style_guide(widget_class)}\n\n"
                  f"THE TEXT:\n{json.dumps(record, ensure_ascii=False, indent=2)}\n\n"
                  f"THE EVALUATOR'S REASON:\n{r.reason}")
        rewritten = extract_record(llm(REFINER_SYSTEM, prompt))
        if rewritten is None:
            say("     the refiner returned no parseable JSON; stopping")
            break
        rewritten.setdefault("widget_class", widget_class)
        record = rewritten

    return {
        "brief": brief,
        "widget_class": widget_class,
        "attempts": len(rounds),
        "accepted": bool(rounds and rounds[-1].score is not None
                         and rounds[-1].score >= PASS_SCORE),
        "before": {k: rounds[0].record.get(k) for k in ("text_en", "text_es")},
        "after": {k: rounds[-1].record.get(k) for k in ("text_en", "text_es")},
        "score_before": rounds[0].score if rounds else None,
        "score_after": rounds[-1].score if rounds else None,
        "rounds": [
            {"attempt": r.attempt, "record": r.record, "score": r.score,
             "reason": r.reason, "deterministic_findings": r.findings}
            for r in rounds
        ],
    }


# --------------------------------------------------------------------------
# The three violation classes, as deliberately off-brand seeds
# --------------------------------------------------------------------------
DEMOS = [
    {
        "name": "vocabulary and IP",
        "widget_class": "ProseBlock",
        "brief": "the run-complete screen's closing line, told from inside the world",
        "seed": {
            "key": "ST_UI.RunComplete_SecondRun",
            "text_en": "The Light guided your Ghost through the Hive nest, Guardian. "
                       "The Traveler watched over this Mexican valley and its pyramid.",
            "text_es": "La Light guio a tu Ghost por el nido Hive, Guardian. El Traveler "
                       "vigilaba este valle mexicano y su pirámide.",
        },
    },
    {
        "name": "tone",
        "widget_class": "ClassTagline",
        "brief": "the Titan's tagline on the class-select screen",
        "seed": {
            "key": "ST_UI.ClassSelect_TitanTagline",
            "text_en": "Awesome tank build, champ!",
            "text_es": "¡Tanque increíble, campeón!",
        },
    },
    {
        "name": "format and length",
        "widget_class": "MenuLabel",
        "brief": "the pause-menu label for abandoning the current run",
        "seed": {
            "key": "ST_UI.Pause_ExitRun",
            "text_en": "Abandon the current run and return to the main menu!",
            "text_es": "Abandonar la partida actual y volver al menú principal para "
                       "empezar de nuevo!",
        },
    },
]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[1])
    p.add_argument("--brief", help="what to write")
    p.add_argument("--widget-class", default="MenuLabel")
    p.add_argument("--demo", action="store_true",
                   help="run the three violation classes from deliberately off-brand seeds")
    p.add_argument("--attempts", type=int, default=MAX_ATTEMPTS)
    p.add_argument("--out", metavar="PREFIX", help="write the transcript under production/output")
    p.add_argument("--model", default="claude-haiku-4-5")
    p.add_argument("--provider", default="claude")
    args = p.parse_args()

    llm = Llm(args.provider, args.model)
    results = []

    if args.demo:
        for demo in DEMOS:
            print(f"\n{'=' * 78}\nVIOLATION CLASS: {demo['name'].upper()}")
            result = run(demo["brief"], demo["widget_class"], llm,
                         seed=demo["seed"], max_attempts=args.attempts)
            result["violation_class"] = demo["name"]
            results.append(result)
    else:
        if not args.brief:
            p.error("--brief is required unless --demo is given")
        results.append(run(args.brief, args.widget_class, llm, max_attempts=args.attempts))

    if args.out:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / f"{args.out}.style.json"
        path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        print(f"\ntranscript: {path}")

    return 0 if all(r["accepted"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
