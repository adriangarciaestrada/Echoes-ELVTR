# The Loom — complete AI dev pipeline, and the game it ships

**ELVTR "Multi-Agent AI for Game Development" — Assignment #10.**
**Student:** Adrián García Estrada

**▶ Play it: https://adrianhawkmoon.itch.io/the-loom**
**Pipeline source: [`agents/`](agents/) — everything in this folder.**

An endless inventory-management autobattler. The player packs relics of
different footprints onto a 7×7 grid — the Loom — then watches them fight on
their own down a lane toward the Beacon they defend. Runs alternate market and
battle; rewards alternate a permanent buff and four new cells, so power and
working space grow together. There is no final wave: the run ends when the
Beacon falls, and depth is the score.

Phaser 3 + TypeScript, bundled by Vite, shipped as an HTML5/WebGL build. Two
pipelines feed it: a retrieval-grounded bilingual copy pipeline that writes
every string a player reads, and an art pipeline that produces every sprite in
the build.

---

## 1. Playable link

**https://adrianhawkmoon.itch.io/the-loom** — version 0.8.0, no install, no
setup, no password.

Verified by playing the published build rather than by loading the page: from
the link, two clicks (language, then class) land in a playable market at wave
1. The embed is 1280×720, the game's own design resolution, so nothing is
letterboxed or cropped, and the session raises no console errors.

---

## 2. Pipeline source code

Everything below is in [`agents/`](agents/), in the order it runs. One
sentence each.

| Agent / stage | What it does | Where |
|---|---|---|
| **Retriever** | BM25 over the design vault; returns the chunks a writer must be grounded in, so copy is written from the game's own law rather than from the model's guess. | [`agents/content/retriever.py`](agents/content/retriever.py) |
| **Writer** (Sonnet) | Writes ONE bilingual `StringRecord` at a time from pinned law plus the retrieved fact, citing which chunk each part came from. | [`agents/content/writer.py`](agents/content/writer.py) |
| **Gate** (deterministic) | Checks what arithmetic can check — widget caps, placeholder parity, banned terminology — and stops the run before any judge is paid to look at illegal content. | [`agents/content/gate.py`](agents/content/gate.py) |
| **Reviewer** (Sonnet) | Judges what a gate structurally cannot: software voice, Spanish that reads as translated, and whether the two languages describe the same mechanic. | [`agents/content/reviewer.py`](agents/content/reviewer.py) |
| **Narrative engine** (Farwatch) | A DM agent that keeps the world in a JSON ledger outside the chat and re-injects it every turn; it answered the game's own opening premise by playing it out. | [`agents/lore/narrative_engine.py`](agents/lore/narrative_engine.py) |
| **Art pipeline** | Spec → generate → deterministic sprite checks (size, palette, transparent background) → import with a provenance sidecar. | [`agents/art/`](agents/art/) |
| **Adversarial QA agent** | Drives the built game in a real browser, fuzzes input, and checks an oracle of invariants rather than screenshots; the only agent whose findings changed the game's rules. | [`agents/qa/`](agents/qa/) |
| **Balance simulator** | Runs the game's own core headless with the frame cap removed, playing full runs under scripted policies; it is what turns "wave 12 is fair" into a measurement, and every balance figure below comes from it. | [`agents/sim/`](agents/sim/) |
| **Shared model wrapper** | One `claude`-CLI headless call path for every agent above: fails loud, never fabricates a response, and logs each call's usage and cost. | [`agents/ai_call.py`](agents/ai_call.py) |

The folder is self-contained: [`vault/`](vault/) carries the design law the
retriever searches and the writer is pinned to, and [`engine/core/`](engine/core/)
the game's rules — the string table the copy pipeline writes into, and the
battle, grid and wave modules the simulator measures. Everything runs from
inside this folder:

```bash
cd agents/content
python3 retriever.py --query "what a Warden knot buff should say" --k 2
python3 gate.py --check-generated          # 109 shipped records, 0 errors

cd ../..
npx tsx agents/sim/run.ts 3 greedy         # full runs, headless, no model
python3 -m pytest agents/lore/test_narrative_engine.py -q
python3 -m pytest agents/art/test_sprite_rules.py -q
```

A complete run is committed as evidence, not just described:
[`production/output/`](production/output/) holds the writer's record, the
gate's verdict, the reviewer's finding, and `usage_log.jsonl` — where every
cost figure below comes from — alongside the narrative engine's saved
transcripts. [`production/screenshots/`](production/screenshots/) has the
build's three store captures. Reproduce the full copy run — the one the cost
figures come from — with:

```bash
cd agents/content
python3 pipeline.py --key "buff.hold_warden.label" --widget-class BuffLabel \
    --brief "a buff that makes the Warden's Knot ultimate grind longer \
             before releasing" --out demo_test
```

---

## 3. Engine integration

**Target engine:** Phaser 3 (WebGL/Canvas), TypeScript, Vite, HTML5 on itch.io.

An approved `StringRecord` is already in the engine's own shape: a key plus
its `en`/`es` pair is exactly a row of `src/core/strings.generated.ts`, the
table the game imports and every scene reads through `t()`. There is no
reformatting step between the two, and two tests keep it that way —
`strings.test.ts` fails on a key the content does not define or content the
keys do not cover, and `literals.test.ts` fails the build if a developer types
a sentence straight into the render layer instead of looking it up.

Art follows the same shape: `art-specs.json` declares each sprite's id and
exact pixel size, the import step writes that file into `tools/art/approved/`
with a provenance sidecar, and the game loads it by the id the spec already
named.

**One manual step remains** in the string path, and it is documented below.

---

## 4. Pipeline audit

### What the pipeline produced, present in the playable build

- **110 bilingual UI records** in `src/core/strings.generated.ts` — every word
  a player reads: class cards, relic and buff names and descriptions, market
  and battle prompts, the score screen.
- **The prologue premise**, played out under a JSON ledger by the narrative
  engine and distilled into `loom-vault/prologue-origin.md`, which the
  class-select copy is written against.
- **20 sprites** in `public/sprites/`: three Weaver cards, three battle backs,
  the battlefield lane, two Remnant tokens, and eleven UI chrome assets — the
  wall, panel and card frames, button plaques, the HUD lintel, offer and buff
  cards, the ultimate's frame.

### What manual steps remain

1. **Image generation is manual.** Art is generated through the Gemini web
   interface and a human picks the candidate; everything after that point —
   crop, downscale, background cut, deterministic checks, provenance sidecar —
   is `import_gemini.py`. An earlier generation API was tried and dropped
   because it could not reliably control a back-view pose, so no image in this
   build came from an API call.
2. **Cutting a generated image into a sprite sometimes needs hand
   measurement.** Automatic background separation works when subject and
   backdrop differ in colour; it failed on the HUD banner, where face and
   backdrop were near-identical greys and the flood fill ate the face.
3. **Merging an approved record into `strings.generated.ts` is manual.** The
   original emitter did not survive the split out of the course monorepo; the
   rebuilt pipeline writes and validates a record but does not append it.
4. **Three boss sprites are not approved yet**; the build ships placeholder
   slabs for them.
5. **Two agents the design describes were never built.** `relic-contract.md`
   names an item agent and `wave-contract.md` an encounter agent; neither
   exists. The relic roster and the wave curve are hand-authored, with the
   simulator doing the checking. Stated explicitly because the rubric asks for
   content *traceably* produced by the pipeline: the strings and the art are,
   and these two are not.

### What it would take to eliminate them

1. An image-generation API behind the same `ai_call.py` contract, so generation
   is a logged call rather than a browser session — this also closes the
   telemetry gap in the cost analysis.
2. Ask the generator for a transparent background, or key against a colour that
   cannot appear in the subject, so the cut is geometric rather than inferred.
3. Rebuild the emitter as `pipeline.py --emit`: append the approved record to
   the table, re-run the drift and orphan tests, and fail the run if either
   breaks. This is the smallest remaining piece and the one that would make the
   copy pipeline fully hands-off.

### Architectural decision to change, and the specific alternative

**Change:** `ai_call.py` exposes one `DEFAULT_MODEL` and every caller inherits
it by omission. That made each stage's model invisible at its call site, and
the two drifted: this project's own commit message and README describe the
reviewer as running on Haiku, while `reviewer.py` never passed a model, so
every review actually ran on Sonnet. Nothing failed and no test could see it.

**Alternative:** make `model` a required positional argument of `call_claude` —
no default at all — so a stage cannot be written without stating what it runs
on, and add a CI check that reads the `model` field already recorded in
`usage_log.jsonl` and fails if a run used a model the stage did not declare.
The routing then lives in one declared table the log can be diffed against,
instead of in an unstated default.

---

## 5. Cost analysis

Measured, not estimated: every figure comes from
[`production/output/usage_log.jsonl`](production/output/usage_log.jsonl), written by `ai_call.py` from the
API's own usage reporting.

| Step | Model | Tokens (in / cache read / cache write / out) | Cost |
|---|---|---|---|
| Writer, turn 1 | Sonnet 5 | 2 / 24,441 / 20,409 / 3,632 | $0.1286 |
| Writer, turn 2 | Sonnet 5 | 4 / 69,296 / 21,818 / 3,158 | $0.1385 |
| Reviewer | Sonnet 5 | 2 / 31,211 / 10,802 / 2,827 | $0.0814 |
| **Total actual run cost** | | | **$0.3485** |

That is one complete record: one bilingual string written from pinned law plus
retrieved fact, gated, and reviewed.

**Most expensive step:** the writer, $0.2671 — **77% of the run**. It carries
the largest prompt (three pinned law documents plus retrieved context) and runs
on the most capable model of the three stages.

**Sustainable for a solo dev / small team: yes, for this class of content.** At
$0.35 per approved record, the game's entire 110-record catalogue costs roughly
$38 to generate with full review — a rounding error against the time it
replaces, and a one-time cost per string rather than a running one. The honest
caveat: this covers the copy pipeline only. The narrative engine ran before
usage logging existed, and the art was generated through a web interface that
bills no API and reports no tokens, so neither has a measured cost. The
pipeline is sustainable; the *telemetry* is not yet complete, and item 1 above
is what closes it.

### Cost-reduction change made mid-project, before / after

**Strategy — before:** the reviewer stage inherited `ai_call.py`'s default
model. Because no call site named a model, the judge ran on the same
writer-grade model as the writer.

**Strategy — after:** the model became an explicit parameter of `review()`, and
the cheaper judge was then measured on the identical record, prompt and gate
report.

| | Model | Tokens (in / cache read / cache write / out) | Cost | Verdict |
|---|---|---|---|---|
| **Before** | Sonnet 5 | 2 / 31,211 / 10,802 / 2,827 | **$0.0814** | `REVISE` — caught the defect |
| **After** | Haiku 4.5 | 10 / 13,620 / 14,113 / 4,203 | **$0.0543** | `PASS` — no findings |

**33% cheaper, and the saving was refused — that is the finding.** The two
models did not return the same verdict. Sonnet returned `REVISE` and named the
defect: the English copy described a *duration* effect while the Spanish had
drifted to an *intensity* effect — two different mechanics promised to two
different players. Haiku returned `PASS` with nothing at all. A deterministic
gate structurally cannot see meaning drift between two languages; catching it
is the only reason the review stage exists, so a 33% saving that blinds it
makes the stage decorative. The reviewer stays on Sonnet, and the model is now
a parameter so the next candidate is measured the same way rather than argued
about.

The cost reduction that **is** in force is architectural and free: the
deterministic gate runs before the reviewer, so a record that violates a cap, a
placeholder rule or a banned term is rejected for $0.00 of model spend instead
of $0.08.
