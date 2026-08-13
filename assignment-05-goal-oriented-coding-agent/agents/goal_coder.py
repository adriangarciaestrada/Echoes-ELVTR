#!/usr/bin/env python3
"""Goal-oriented coding agent: read the design, read the code, build what is missing.

    python3 agents/goal_coder.py                 # full run, writes the chosen feature
    python3 agents/goal_coder.py --plan-only     # stop after prioritising
    python3 agents/goal_coder.py --top 5         # show more of the ranking

Five stages, and the split between them is the point:

    1. READ THE DESIGN     a model, because a GDD is prose
    2. SCAN THE CODE       deterministic, because a symbol either exists or does not
    3. DETECT GAPS         deterministic
    4. PRIORITISE          deterministic, and it shows its arithmetic
    5. WRITE THE FEATURE   a model, because code is prose too

Only the ends are model work. The reasoning in the middle — what is missing, what
matters most, and why — is arithmetic that can be read, argued with and re-run. A
ranking produced by asking a model "what should I build first?" cannot be checked
by anyone, including the model.

The scoring signals are not invented for this exercise. They come from what this
project has actually cost:

  ALREADY REFERENCED  Something in the repository already writes or reads this
                      feature's data while nothing implements the behaviour. That
                      is not a missing feature, it is a promise being broken now,
                      and it is how `is_one_way` shipped as an actor tag that no
                      collision code has ever honoured — discovered by a human
                      walking into a platform that should have let them through.

  OBSERVED FAILURE    There is recorded evidence it has already caused a defect.
                      Nothing else in a backlog carries that.

  ON THE SLICE PATH   The scoped GDD lists it as required for the deliverable.

  BLOCKS OTHERS       Other missing features name it as a dependency.

  COST                Which layer it lands in. C++ is cheapest here because the
                      compiler checks it and a diff can review it; an asset is
                      dearest because only a human eye can.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runner  # noqa: E402  (subscription lanes, model routing, token logging)

BASE = Path(__file__).resolve().parent.parent
GDD = BASE / "GDD" / "GDD-course-scope.md"
VAULT = BASE / "vault"
PROJECT = BASE / "Echoes-58"
if not PROJECT.exists():
    # A submission cannot carry the whole game repository, so the trees the scan
    # reads travel under `scanned/`. Without this the scan finds only its own
    # source, every described system reads as missing, and the numbers printed
    # here stop matching the ones written up.
    PROJECT = BASE / "scanned"
OUT = BASE / "production" / "output"

# Where a feature can land, and what it costs to put it there. The ordering is
# the repository's own routing rule: anything a compiler or a diff can check
# belongs in code, and only what needs a human eye belongs in an asset.
LAYER_COST = {"cpp": 0, "python": 0, "blueprint": 1, "asset": 2, "unknown": 1}

SEARCH_ROOTS = [
    PROJECT / "Source",
    PROJECT / "Content" / "Python",
    PROJECT / "Scripts",
    BASE / "agents",
]

READER = {"provider": "claude", "model": "claude-sonnet-5"}
WRITER = {"provider": "claude", "model": "claude-sonnet-5"}

READER_PROMPT = """You extract a build list from a game's design documents.

Return ONLY JSON: {"features": [ ... ]}. Each feature is a concrete, buildable
system the design requires, not a theme or a feeling. For each one give:

  "id"        short slug, lowercase, underscores
  "name"      one line
  "source"    which document said so
  "layer"     one of: cpp | python | blueprint | asset
  "symbols"   identifiers whose presence in source would prove it is built
              (class names, function names, field names) — 1 to 4 of them
  "assets"    asset name fragments that would prove it, if it is content
  "depends_on" ids of other features that must exist first, or []
  "required_for_slice" true if the scoped GDD lists it as needed for the
              deliverable slice rather than the long-term vision

Be specific. "Combat" is not a feature; "dodge with invincibility frames" is.
Prefer things a reader could verify by grepping the repository."""

WRITER_PROMPT = """You are the coding half of a goal-oriented agent for a game in
Unreal Engine 5.8, C++ and Blueprint hybrid, no GAS.

You are given one missing feature, the design text that requires it, and the
existing code around it. Write the smallest complete implementation that makes
the design true, in the layer named. Match the surrounding code's conventions.

Return ONLY JSON: {"files": [{"path": "...", "contents": "..."}], "notes": "..."}
Paths are relative to the project root. Include every file needed to compile.
Do not restate the design in comments; explain only what the code does not say."""


# --------------------------------------------------------------------------
# 1. Read the design
# --------------------------------------------------------------------------
def read_design(timeout=600):
    docs = [(GDD.relative_to(BASE).as_posix(), GDD.read_text(encoding="utf-8"))]
    for note in sorted(VAULT.rglob("*.md")):
        docs.append((note.relative_to(BASE).as_posix(), note.read_text(encoding="utf-8")))
    corpus = "\n\n".join(f"=== {name} ===\n{text}" for name, text in docs)
    raw, usage = runner.dispatch(READER, READER_PROMPT,
                                 f"DESIGN DOCUMENTS:\n\n{corpus}", timeout)
    runner.log_usage("goal_coder:reader", READER["model"], usage)
    parsed = runner.extract_json(raw)
    if not parsed or "features" not in parsed:
        raise SystemExit("[goal_coder] the reader returned no feature list")
    return parsed["features"]


# --------------------------------------------------------------------------
# 2. Scan the code
# --------------------------------------------------------------------------
def scan():
    """Every identifier the repository defines or mentions, and every asset name."""
    text = []
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix.lower() in {".h", ".cpp", ".cs", ".py"} and path.is_file():
                text.append((path.relative_to(BASE).as_posix(),
                             path.read_text(encoding="utf-8", errors="ignore")))
    assets = [p.stem for p in (PROJECT / "Content").rglob("*.uasset")]
    assets += [p.stem for p in (PROJECT / "Content").rglob("*.umap")]
    # Binary content cannot travel with a submission, so the asset names are
    # also kept as a manifest. Without it the scan sees no assets at all and
    # every piece of content in the design reads as missing.
    manifest = BASE / "production" / "output" / "goal_coder_assets.txt"
    if not assets and manifest.exists():
        assets = manifest.read_text(encoding="utf-8").split()
    elif assets:
        manifest.write_text("\n".join(sorted(assets)) + "\n", encoding="utf-8")
    files = {p.name: p.relative_to(BASE).as_posix()
             for root in SEARCH_ROOTS if root.exists() for p in root.rglob("*") if p.is_file()}
    return text, assets, files


def evidence_for(feature, sources, assets, files):
    """Where a feature's symbols appear, split by whether they are implemented.

    A symbol inside a comment, a docstring or a JSON contract is a mention, not
    an implementation. The distinction is the whole point: a field that only
    appears in the document describing it is exactly the gap being looked for.

    Evidence is looked for in three places, because a design document names
    things that live in three: a class in source, an asset in the content tree,
    and a script by its filename. Searching only source text reported Enhanced
    Input as missing while five Input Action assets sat in the project, and
    reported the room importer as missing while two files implemented it.
    """
    hits = {"implemented": [], "mentioned": []}
    for symbol in (feature.get("symbols") or []) + (feature.get("assets") or []):
        found = False

        for name in assets:                                  # an asset by name
            if symbol.lower().rstrip(".uasset") in name.lower():
                hits["implemented"].append(f"asset {name}")
                found = True
                break
        if found:
            continue

        if "." in symbol or "/" in symbol:                   # a file by path
            tail = symbol.split("/")[-1]
            if tail in files:
                hits["implemented"].append(f"file {files[tail]}")
                continue
            # The reader names files from memory of the design and gets the
            # ordinal wrong: it asked for 03-level-designer.md when the crew
            # numbers it 01. Match on the descriptive part, since that is what
            # the design actually specified.
            stem = re.sub(r"^\d+[-_]", "", tail)
            near = [v for k, v in files.items() if re.sub(r"^\d+[-_]", "", k) == stem]
            if near:
                hits["implemented"].append(f"file {near[0]}")
                continue

        pattern = re.compile(r"\b" + re.escape(symbol) + r"\b")
        for path, body in sources:                            # a symbol in source
            for line in body.splitlines():
                if not pattern.search(line):
                    continue
                stripped = line.strip()
                is_comment = stripped.startswith(("#", "//", "*", '"""', "'"))
                hits["mentioned" if is_comment else "implemented"].append(
                    f"{path}: {stripped[:90]}")
                found = True
                break
            if found:
                break
    return hits


# --------------------------------------------------------------------------
# 3 & 4. Detect gaps, and rank them
# --------------------------------------------------------------------------
def score(feature, hits, gaps_by_id):
    """The reasoning layer. Every term is named so the ranking can be argued with."""
    reasons, points = [], 0

    if hits["mentioned"] and not hits["implemented"]:
        points += 4
        where = hits["mentioned"][0].split(":")[0]
        reasons.append(f"+4 already referenced — {where} names it, nothing implements it")

    if feature.get("observed_failure"):
        points += 3
        reasons.append(f"+3 observed failure — {feature['observed_failure']}")

    if feature.get("required_for_slice"):
        points += 3
        reasons.append("+3 the scoped GDD requires it for the slice")

    dependents = [g["id"] for g in gaps_by_id.values()
                  if feature["id"] in (g.get("depends_on") or [])]
    if dependents:
        points += 2 * len(dependents)
        reasons.append(f"+{2 * len(dependents)} blocks {', '.join(dependents)}")

    if feature.get("depends_on"):
        blocked = [d for d in feature["depends_on"] if d in gaps_by_id]
        if blocked:
            points -= 5
            reasons.append(f"-5 itself blocked by {', '.join(blocked)}")

    layer = feature.get("layer", "unknown")
    cost = LAYER_COST.get(layer, 1)
    points -= cost
    reasons.append(f"-{cost} lands in {layer}")

    return points, reasons


# --------------------------------------------------------------------------
# Evidence of past failure, read rather than assumed
# --------------------------------------------------------------------------
def observed_failures():
    """Features this project has already been bitten by, taken from its history.

    Read from the repository rather than hard-coded opinion: a warning written
    into a contract is the record of something that went wrong.
    """
    found = {}
    for note in VAULT.rglob("*.md"):
        body = note.read_text(encoding="utf-8", errors="ignore")
        for match in re.finditer(r"⚠️\s*`?(\w+)`?[^\n]*", body):
            found[match.group(1)] = match.group(0)[:120].strip()
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--refresh", action="store_true",
                        help="re-read the design instead of reusing the cache")
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    cache = OUT / "goal_coder_features.json"
    if cache.exists() and not args.refresh:
        features = json.loads(cache.read_text(encoding="utf-8"))
        print(f"1. design already read — reusing {cache.name} (--refresh to re-read)")
    else:
        print("1. reading the design…")
        features = read_design(args.timeout)
        cache.write_text(json.dumps(features, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"   {len(features)} features declared")

    print("2. scanning the code…")
    sources, assets, files = scan()
    print(f"   {len(sources)} source files, {len(assets)} assets")

    print("3. detecting gaps…")
    failures = observed_failures()
    gaps = []
    for f in features:
        hits = evidence_for(f, sources, assets, files)
        if hits["implemented"]:
            continue
        for symbol in f.get("symbols") or []:
            if symbol in failures:
                f["observed_failure"] = failures[symbol]
        gaps.append((f, hits))
    print(f"   {len(gaps)} of {len(features)} are missing")

    print("4. prioritising…\n")
    by_id = {f["id"]: f for f, _ in gaps}
    # Ties are broken by which layer the work lands in, not by list order. The
    # repository's routing rule already says why: what a compiler and a diff can
    # check is worth more than what only an eye can, so equal urgency goes to
    # the cheaper layer to verify. Anything else would make the top of a build
    # list depend on the order a model happened to emit its features in.
    ranked = sorted(((score(f, h, by_id), f, h) for f, h in gaps),
                    key=lambda r: (-r[0][0], LAYER_COST.get(r[1].get("layer"), 1), r[1]["id"]))

    if len(ranked) > 1 and ranked[0][0][0] == ranked[1][0][0]:
        print(f"   note: {ranked[0][1]['id']} and {ranked[1][1]['id']} tie at "
              f"{ranked[0][0][0]}; broken toward the layer a compiler can check\n")

    for (points, reasons), f, _ in ranked[:args.top]:
        print(f"   [{points:>3}] {f['id']} — {f['name']}")
        for r in reasons:
            print(f"          {r}")
        print()

    (OUT / "goal_coder_plan.json").write_text(json.dumps(
        [{"score": p, "reasons": r, "feature": f} for (p, r), f, _ in ranked],
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"   ranking written to {(OUT / 'goal_coder_plan.json').name}")

    if args.plan_only or not ranked:
        return 0

    (_, reasons), chosen, hits = ranked[0]
    print(f"\n5. writing '{chosen['id']}'…")
    context = "\n\n".join(
        f"=== {p} ===\n{b}" for p, b in sources
        if any(s in b for s in (chosen.get("symbols") or []))
        or p.endswith(("GameFeelComponent.h", "GameFeelComponent.cpp", "Echoes.Build.cs")))
    raw, usage = runner.dispatch(WRITER, WRITER_PROMPT, json.dumps({
        "feature": chosen, "why_first": reasons,
        "where_it_is_referenced": hits["mentioned"][:8],
        "existing_code": context[:60000]}, ensure_ascii=False), args.timeout)
    runner.log_usage("goal_coder:writer", WRITER["model"], usage)

    result = runner.extract_json(raw)
    if not result or "files" not in result:
        raise SystemExit("[goal_coder] the writer returned no files")
    for entry in result["files"]:
        # The writer is told paths are relative to the project root and sometimes
        # prefixes them with the project directory anyway. Accept both rather
        # than nesting Echoes-58 inside itself.
        rel = entry["path"]
        if rel.startswith(PROJECT.name + "/"):
            rel = rel[len(PROJECT.name) + 1:]
        path = PROJECT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(entry["contents"], encoding="utf-8")
        print(f"   wrote {path.relative_to(BASE).as_posix()}")
    if result.get("notes"):
        print(f"\n   {result['notes']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
