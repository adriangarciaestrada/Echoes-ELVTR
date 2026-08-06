# Echoes — Dynamic Content Pipeline (UI Copy)

**ELVTR "Multi-Agent AI for Game Development" — Assignment #4 (Dynamic Content Pipeline).**

A retrieval-augmented pipeline that writes the player-facing text of **Echoes**, a
2.5D sci-fi metroidvania in Unreal Engine 5.7.4. It retrieves from the project's own
design corpus, generates bilingual EN/ES strings, gates them deterministically, and
submits them to a semantic reviewer before anything can reach the engine.

> Everything here ran on personal subscriptions through headless CLIs. **No API keys,
> no paid endpoints, no vector database.** The retriever is stdlib-only and
> deterministic, so it runs in a fresh clone even though the model half cannot.

---

## Where the graded evidence lives (read this first)

| Looking for | Go to |
|---|---|
| **The knowledge base** and why it is game-anchored | [§2](#2-the-knowledge-base) |
| **Query → retrieved chunk → output, side by side** — all three content types | [§4](#4-retrieval-shown-and-measured) |
| **Retrieval accuracy**, measured, with its caveat stated | [§4](#recall-over-a-labelled-set) |
| **The critic catching and correcting** a real defect | [§5](#5-consistency-checking) and [§6](#borderline--productionoutputst_ui_runcompletejson) |
| **The quality boundary**: PASS · BORDERLINE · FAIL · retrieval miss | [§6](#6-sample-output-and-where-the-boundaries-are) |
| **Self-assessment** and the tweaks made for game-fit | [§7](#7-voice-judgment) |
| **Commands that reproduce every number above** | [§8](#8-reproducing-this) |

The runnable evidence is five string tables under
[`production/output/`](production/output/), each with its `.gate.json` and
`.review.json` siblings — the deterministic verdict and the semantic one, persisted
beside every run rather than printed to a terminal and lost. Together they carry a
full loop: `REVISE → apply → FAIL → resolve → PASS → PASS`.

**New in this assignment**, on top of the crew delivered for #3: `retriever.py`
(chunking, BM25, the labelled evaluation), `ui_rules.py` (the UI arithmetic),
`validators.py --kind strings`, and two agents — **13 UI Copy Writer** and
**14 UI Copy Reviewer**, the semantic layer the UI half of the crew never had.

---

## 1. The gap this fills

*Echoes* had roughly 31,000 words of design documentation and **zero words of text
a player would read.**

The vault declares four screens — `HUD_Main`, `Screen_ClassSelect`, `Screen_Pause`,
`Screen_RunComplete` — and the layout agent that serves them emits *references* to
string-table keys. Nothing wrote the strings behind those keys, so every layout
pointed into an empty table. A search of the committed output directory for
`ST_UI`, `ST_Lore` or `string_table_key` returned nothing at all.

The three content types this pipeline produces are the ones that empty table owes
the game, and each lands in an engine seam that already exists:

| Content type | Engine seam | Why the slice needs it | Produced |
|---|---|---|---|
| **Menu and accessibility copy** | `ST_UI` | Pause, input remap, toggles and the locale switch are all in scope by contract; a menu with no text is not "minimal", it is broken | `st_ui_pause.json` |
| **Contextual prompts and HUD state** | `ST_UI` | The interact prompt and the post-boss keycard state are the game's only signals that an action exists | `st_ui_hud.json` |
| **The hero screen** | `ST_UI` | Run-Complete carries the replay hook of the entire slice in one paragraph | `st_ui_runcomplete.json` |

The third row is the load-bearing one. The design's replay hook — *"names what this
class never saw"* — is a paragraph that did not exist. In a normal metroidvania that
job belongs to a map with grey rooms and a completion percentage; this slice cuts
the map deliberately, so the job falls to prose. That is the whole argument for why
this content is needed rather than merely possible.

---

## 2. The knowledge base

The corpus is the project's own design documents, not a placeholder lore file:

```
178 chunks · 31 files · ~26,400 tokens
  vault/**.md              the design canon, one note per subject
  GDD/GDD-course-scope.md  the slice's specification
```

*(The master GDD — the full game's vision document, three campaigns wider than
this slice — is part of the corpus during development but is not shipped in this
folder. Every figure below is measured against what is here, so every command in
§8 reproduces them.)*

Chunks are cut on markdown headings, so every chunk carries the address that
produced it — `path#heading` — and every generated record cites the chunks it was
written from in a `source_chunks` field the gate requires to be non-empty. There is
no new canon without a source.

**The lore layer is load-bearing, not decorative.** UI copy for this game cannot be
written without it, so two lore artifacts are pinned into every single call: the
cosmology bible (`vault/05-lore/architects-cosmology.md`), which is where the tone
and the world's vocabulary come from, and the term table
(`vault/00-core/terminology-guard.md`), which decides which words may ship at all
and forbids naming the region the setting is built on. A menu label in *Echoes* is
governed by the lore document as strictly as a mural inscription is — the difference
is only how much of it shows.

**Pinned versus retrieved.** Those two, plus the UI contract, the design law and the
budgets, are never retrieved and always injected. They are jurisdiction rather than
relevant material — a query that happens not to mention the term table must not be
able to drop it. Retrieval answers only the other question: *what does this screen,
at this moment of the game, need to say?*

The two failure modes differ, which is why the split exists. A pinned rule ignored
is a contract violation the deterministic gate catches. A bad retrieval produces
copy that is perfectly legal and perfectly generic, and only a reviewer sees it.

---

## 3. The pipeline

```
retriever.py  ──query──▶  BM25 over 206 chunks  ──top-k + addresses──┐
                                                                     ▼
pinned notes (contract · law · budgets · terms) ──────────▶  13 UI Copy Writer
                                                             (Sonnet 5)
                                                                     │ StringTable JSON
                                                                     ▼
                                          validators.py --kind strings   ← deterministic gate
                                                                     │ PASS
                                                                     ▼
                                                          14 UI Copy Reviewer
                                                             (Haiku 4.5)
                                                                     │
                                          both verdicts persisted beside the artifact
```

The layout half of a screen is produced separately by an existing agent and is
fully checkable by arithmetic, which is why it never had a semantic reviewer. Copy
is the half that is not, and agent 14 is that missing layer.

**The gate checks** the key grammar and table membership; the screen and
`widget_class` enums; non-empty provenance; each string against its class's
character cap **in both languages**; the Spanish allowance; substitution parity
between languages; banned terms; named regions; cut features; hardcoded button
glyphs; placeholder text; duplicate strings; the per-screen key budget; and the
cross-reference against the layout specs. Sixteen error codes, no model involved.

---

## 4. Retrieval, shown and measured

### Query → retrieved chunk → output, for all three content types

**1 — Menu copy.** Query: *what the pause menu offers the player, accessibility
toggles, locale switch, exit run*. Top chunk, BM25 **27.15**, from
`vault/07-ui-and-controls/hud-and-screens.md#Screen Roster`:

> **Pause Menu:** Minimalist settings, accessibility toggles, exit run.

| Key | `text_en` | `text_es` | Cites |
|---|---|---|---|
| `ST_UI.Pause_Resume` | Resume | Continuar | `hud-and-screens.md#Screen Roster` + `ui-constraints.md#Screens have jobs` |
| `ST_UI.Pause_Controls` | Controls | Controles | `hud-and-screens.md#Screen Roster` |
| `ST_UI.Pause_Accessibility` | Accessibility | Accesibilidad | `hud-and-screens.md#Screen Roster` + `ui-constraints.md#Accessibility is a valve, not a mode` |
| `ST_UI.Pause_Language` | Language | Idioma | `bilingual-string-tables.md#Origin Rule` |
| `ST_UI.Pause_ExitRun` | Exit Run | Abandonar | `hud-and-screens.md#Screen Roster` + `ui-constraints.md#Screens have jobs` |

Every retrieved item became exactly one row of the menu the chunk describes, in the
order the chunk lists them. Gate `PASS`, reviewer `PASS`.

**2 — Contextual prompts.** Query: *contextual interact prompt keycard state after
boss one, health pips, what the in-run HUD shows*. Top chunk from
`hud-and-screens.md#Minimalist Dread HUD Philosophy`:

> **Contextual Prompts:** Minimalist interact prompts (`[X]`), keycard status icon post-Boss 1.

| Key | `text_en` | `text_es` |
|---|---|---|
| `ST_UI.HUD_Interact` | `<Interact>` | `<Interact>` |
| `ST_UI.HUD_KeycardUnlock` | `<Interact> Unlock` | `<Interact> Desbloquear` |

The reflection here is worth reading closely: the retrieved chunk literally
specifies `[X]`, and the output does **not** contain it. The writer took the
*content* from retrieval — that a prompt exists, and that a keycard state follows
Boss 1 — while obeying a pinned rule that outranks it. That is the pinned/retrieved
split doing its job: retrieval supplies facts, jurisdiction supplies law, and a
conflict resolves in the same direction every time.

**3 — The hero screen.** Query: *run complete screen names what this class never
saw, the branch it could not enter, sells the second run*. Top chunk, BM25
**37.11**, same roster note:

> **Run-Complete Screen:** Displays completion time, stats, and names what this class never saw (sells the 2nd run for opposite class).

Second chunk, BM25 20.86, `room-constraints.md#The visibility rule`:

> At the junction, **both** branch gates are in frame: one opens to the player's key, the other stays sealed and legibly class-locked.

| Key | `text_en` |
|---|---|
| `ST_UI.RunComplete_SecondRun` | You saw one half. A door stayed sealed, and nooks stayed out of reach, waiting for the other class. |

*"A door stayed sealed"* is the second chunk's sealed gate; *"nooks stayed out of
reach"* is its optional pockets. The output is traceable clause by clause to
retrieved text — which is also why its failure was a *voice* failure and not a
factual one.

### Provenance is verified, not declared

Requiring a citation only proves the writer typed something. Every address in
`source_chunks` is now resolved against the corpus, so a plausible-looking citation
that does not exist is a hard failure:

```
ERR_UNRESOLVED_SOURCE  cited chunk 'architects-cosmology.md#A Heading That Does
                       Not Exist' does not exist in the retrieval corpus
```

Across the three real runs: **20 citations, 20 resolve** against this folder's corpus. The generators were
already honest; the difference is that this is now checked rather than trusted, and
the check was added after noticing that the earlier deliberately-broken test payload
cited `"x#y"` and passed.

### Recall over a labelled set

Sixteen hand-labelled queries, each naming the note that must appear in the top *k*.
Labels are at file granularity: labelling exact headings would mean asserting which
section of a note is the right answer, which is a judgment the labeller would be
grading their own work on.

| Retriever | recall@3 | recall@5 |
|---|---|---|
| Flat BM25 | 15/16 (0.94) | 16/16 (1.00) |
| \+ vault ahead of the GDD, filename indexed | **16/16 (1.00)** | **16/16 (1.00)** |

Measured on the development corpus, which also holds the master GDD, flat BM25
scored 13/16 and each fix is visible separately. The effect is the same and larger
there, which is the point rather than a caveat: **how much a scope-aware retriever
buys you scales with how much off-scope material the corpus holds.**

**That last figure is in-sample and must not be read as an accuracy estimate.** Both
fixes were found *by* this set. What the measurement supports is narrower and still
useful: two specific defects existed, and no longer do. A held-out set is the next
measurement.

Both defects are worth naming because neither was a tuning problem.

**Flat BM25 lost three queries to the scoped GDD.** It is long and covers
everything, so its chunks beat short focused notes on raw term overlap. Length
normalisation dampens this and cannot fix it, because those sections genuinely do
contain more matching words. The fix is a statement about the corpus rather than a
weight: the vault is the canon the crew reads, the GDDs are where that canon came
from, and one of them describes a game three campaigns wider than this slice. The
GDD is now a fallback tier that fills slots the vault could not — never a
competitor for the top of the list. **This is a scope boundary enforced in the
retriever**, and without it the pipeline would happily write copy for features the
slice cut.

**The filename was not indexed.** The remaining misses were queries naming their
subject exactly — *"titan kit charge bash"* failing to return `titan-kit.md` — which
is the easy case a retriever has no excuse to miss. In this corpus a filename is a
curated topic label, one note per subject, so indexing it is using evidence that was
already there. It closed all three.

---

## 5. Consistency checking

Agent 14 reviews what arithmetic cannot: software voice, copy that explains a
mechanic instead of naming a moment, Spanish that reads as translation, a screen
serving the wrong job, and text doing the world's job. Two rules make its findings
auditable rather than decorative:

- Where a finding is a contradiction, it must **quote the line of injected context
  it contradicts**. A finding with a quote is verifiable; one without is an opinion.
- Every finding carries a `suggestion` with concrete replacement text in both
  languages, so a correction can be *shown* rather than described.

Two prohibitions keep it from wasting calls. It may not speculate that a string
"may overflow" — that is arithmetic, it already ran, and its report is in the
reviewer's input. And it may not ask for typography, contrast or emphasis: a
`StringRecord` carries no font by design, the art pass that does will never read the
report, and a finding nobody can act on is worse than silence.

Both were pre-empted from a measured precedent in this project's room pipeline,
where the reviewer's most frequent finding was a question the geometry rules had
already answered — a model paid, repeatedly, to raise a settled question.

`RULE_SUSPECT` is the one sanctioned way for the reviewer to disagree with the
gate. Every character cap was chosen before a single real string existed, and the
note holding them says so; if a cap forces copy to drop something the design
wanted, that code is how a human finds out.

---

## 6. Sample output, and where the boundaries are

The quality boundary is exhibited at four levels rather than asserted. Each is a
real artifact from a real run except where marked.

### Where the boundary actually sits

Every example below is one row of this table. The boundary is not a single line —
it is three, and knowing which one a defect falls against is the whole skill:

| What refuses it | What it can decide | What it cannot | Caught in this run |
|---|---|---|---|
| **Arithmetic** (`validators.py`) | anything countable: length, ratio, parity, membership in a list, whether a key or citation resolves | whether the words are any good | `"Tiempo de Supervivencia"` — 23 chars against a cap of 20 |
| **Judgment** (agent 14) | voice, register, whether the Spanish was authored or translated, whether a screen does its job | anything requiring a count, which is why it is forbidden from trying | `"Completion Time"` — legal, permitted, and placeless |
| **Nobody, yet** | — | — | Spanish IP terms; whether `text_es` has equivalent weight in origin; held-out retrieval accuracy |

The middle row is the one worth dwelling on. `"Completion Time"` is not merely
allowed by the gate — the cut-feature denylist was **deliberately written not to
catch it**, because "completion time" is a stat this screen legitimately shows and
only *completion percentage* was cut. The gate was right, and the string was still
wrong. A pipeline whose only quality signal is its deterministic gate would have
shipped it and reported success.

The bottom row is the part a report is normally not honest about, so it is stated
first rather than buried: three things nothing in this pipeline checks.

### PASS — `production/output/st_ui_pause.json`

Five menu labels, gate `PASS` on the first attempt, reviewer `PASS`. Worth noting
*why* it passes rather than only that it did: every record cites a chunk, both
languages fit the `MenuLabel` cap of 20, and the reviewer judged the plainness
correct for the screen's job — a pause menu with voice in it is a pause menu getting
in the way.

### PASS — `production/output/st_ui_hud.json`, and a rule proving itself

Two contextual prompts, gate `PASS`, reviewer `PASS`. The record worth pointing at:

| Key | `text_en` | `text_es` |
|---|---|---|
| `ST_UI.HUD_KeycardUnlock` | `<Interact> Unlock` | `<Interact> Desbloquear` |

The writer emitted an **action token** rather than a button glyph, unprompted. That
rule exists because the HUD note specifies a hardcoded `[X]` while input remap is in
scope — a contradiction found while writing the budgets and deliberately left
flagged rather than silently patched, since it is a design decision. The law states
the argument for tokens; the generator read it and complied; the gate would have
refused the alternative. Three layers agreeing about a question a human has not
formally settled yet.

Note also that both languages carry the same token, which is what the
substitution-parity check exists to enforce: a prompt that loses its `<Interact>` in
one language breaks at runtime rather than at review.

### BORDERLINE — `production/output/st_ui_runcomplete.json`

**Gate `PASS`, 0 errors, 1 attempt. Reviewer `REVISE`, two findings.** This is the
level the whole review layer exists for: copy that breaks no countable rule and is
still not this game's.

What the writer produced:

| Key | `text_en` | `text_es` |
|---|---|---|
| `ST_UI.RunComplete_Time` | Completion Time | Duración total |
| `ST_UI.RunComplete_SecondRun` | You saw one half. A door stayed sealed, and nooks stayed out of reach, waiting for the other class. | Solo viste una mitad. Una puerta quedó sellada, y quedaron rincones fuera de alcance, a la espera de la otra clase. |

**Finding 1 — `SOFTWARE_VOICE` on `RunComplete_Time`.** *"'Completion Time' is
generic software copy that could appear unchanged in any game's results screen."*
Quoting the injected law: *"This screen carries the replay hook of the entire slice
in a paragraph, and it is the one place where the writing is doing narrative work
rather than staying out of the way."* Correction supplied: **"Time Survived" /
"Tiempo de Supervivencia"**.

This finding is the clearest demonstration in the report of why both layers exist.
"Completion time" is a **legitimate** stat for this screen — the design names it
explicitly, and the cut-feature denylist deliberately does *not* ban the bare word
"completion" precisely so this label keeps working; only *completion percentage* was
cut. The gate was right to pass it. Being permitted and being right are different
questions, and only the second one needs judgment.

**Finding 2 — `ES_TRANSLATED` on `RunComplete_SecondRun`.** The hardest finding the
reviewer was built to raise, and it raised it unprompted: *"The Spanish is
clause-for-clause structurally parallel to English… This suggests translation-first
authoring rather than origin-written Spanish."* Quoting the law: *"Spanish that
mirrors English clause for clause has failed even when it fits."* The correction
restructures rather than retranslates:

> **Solo viste una mitad. Una puerta se te vedó; rincones que tu clase no puede
> alcanzar — esperan a la otra.**

The gate had already proved this string *fits*: both languages inside the
`ProseBlock` cap, the Spanish inside its allowance. Fitting was never the question
the origin rule asks, and no arithmetic can ask it.

Both findings carry a `quote_from_source` and a concrete bilingual replacement, so
the correction is shown rather than claimed.

**The correction applied, and what happened when it was.** Both replacements were
taken from the reviewer's own `suggestion` fields and re-submitted to the gate. The
result is the most useful artifact in this report:

```
st_ui_runcomplete_asreviewed.gate.json   →  FAIL, 2 errors
  ERR_OVER_CAP     records[0].text_es  23 chars exceeds the StatLabel cap of 20
  ERR_UI_OVERFLOW  records[0].text_es  23 chars exceeds its allowance of 19 for a 13-char text_en
```

**The reviewer proposed a correction the gate refuses.** "Tiempo de Supervivencia"
is 23 characters against a cap of 20. Nothing about this is a malfunction — it is
the authority structure working exactly as designed. The semantic layer judges
voice and has no way to count; the deterministic layer counts and has no opinion
about voice. When they disagree the arithmetic wins, because it is the one that
cannot be wrong about its own question.

Resolved by keeping the reviewer's intent and re-deriving the Spanish to fit:
**"Time Survived" / "Supervivencia"** — 13 and 13. Deliberately not a literal
rendering of the English, which is what the origin rule asks for anyway.

```
st_ui_runcomplete_refined.gate.json     →  PASS, 0 errors
st_ui_runcomplete_refined.review.json   →  PASS, 0 findings   (same reviewer, second pass)
```

The loop closed: `REVISE` → apply → gate `FAIL` → resolve → gate `PASS` → reviewer
`PASS`. Four artifacts on disk, none of them narrated after the fact.

It also produced a live candidate for `RULE_SUSPECT`: a 20-character cap on stat
labels may simply be too tight for Spanish, and the first real Spanish string to
test it failed. The caps were chosen before any string existed and the budgets note
says so. This is how a human finds out — the next tuning pass has evidence rather
than an argument.

### FAIL — refused by arithmetic before anyone reads it

**The real one is above**: `st_ui_runcomplete_asreviewed.gate.json`, two errors, on
text this pipeline actually produced. It is worth more than any constructed failure
because nobody chose it — the reviewer wrote a string it believed in and the gate
refused it.

A second, **constructed** payload exercises the codes a two-screen run never
reaches. Marked as constructed plainly, because a fabricated failure presented as a
real one would be the worst thing in this report. Twenty-two findings, including:

| Code | What it caught |
|---|---|
| `ERR_CUT_FEATURE` | a widget named `bar_progress_02` — caught through its **binding**, `BossHealthPercent`, because an id can be laundered and a binding cannot |
| `ERR_REGION_LEAK` | the country named in shipped text |
| `ERR_GLYPH_LITERAL` | `[X]` hardcoded, which becomes a lie the moment a player remaps |
| `ERR_SPECIFIER_MISMATCH` | `{1}` present in English and missing in Spanish — a silent truncation at runtime |
| `ERR_UNSOURCED` | a record citing nothing |
| `ERR_DANGLING_KEY` / `ERR_ORPHAN_STRING` | the cross-reference: an empty widget, and work nobody sees |

### RETRIEVAL MISS — the level a copy pipeline is normally not honest about

The recall table in §4 *is* this level. Both misses were structural rather than
stylistic, both were diagnosed to a cause, and both fixes are measured before and
after.

### What the pipeline does not catch

Stated because claimed coverage is worth less than known gaps.

- **The Spanish half of the IP term table is unguarded.** `La Luz del Viajero`
  passes clean while its English equivalent fails twice, against a mandate in that
  same note requiring both languages to ship clean. Closing it needs the approved
  Spanish terms decided, which is naming work rather than gate work. It is recorded
  as a known gap in the note itself.
- **Nothing verifies that the Spanish has equivalent weight in origin.** The gate
  proves it *fits*; the origin rule is carried only by the writer's brief and the
  reviewer's judgment.
- **Held-out retrieval accuracy is unmeasured**, as §4 says.

---

## 7. Voice judgment

Do the outputs sound like *this* game? The three runs answer differently, and the
difference is the point.

**Pause: deliberately not, and that is correct.** The design law gives each screen
one job, and this one's is to let the player leave and come back. Copy with
personality there is copy getting in the way. The reviewer checked voice and passed
the plainness — the right answer, which would look like the wrong one to anyone who
had not read the law.

**Run-Complete: not yet, and the reviewer said so.** This is the only screen whose
job is rhetorical, and the first draft failed it in both languages at once — a
generic stat label, and Spanish built on English clause structure. Neither broke a
countable rule. The honest self-assessment is that the writer's default register is
competent and placeless, and that the law alone did not pull it far enough: the
prohibitions in the brief tell it what not to write, and nothing in the pinned
context shows it what this game's *voice* sounds like when it is working. The
retrieved chunks for that run were all structural — screen roster, visibility rule,
route description — because that is what the query asked for. **The next adjustment
is to the query, not the prompt:** a screen whose job is narrative should retrieve
tone alongside facts.

**Two concrete changes made to improve game-fit**, both traceable to evidence:

**1. The retriever now enforces a scope boundary.** Before the tiering fix, queries
about the slice returned chunks from the full GDD — a document describing three
campaigns, four endings, and systems this slice explicitly cut. Copy written from
that context would have been fluent, on-brand, and about a different game. This is
the single most important adjustment in the pipeline and it is a retrieval change,
not a prompt change.

**2. The banned-term rule now bans the capital rather than the word.** The IP guard
rejected *"The light in the corridor died long before we did."* — correct, on-tone
copy — because `Light` is a placeholder from another game's vocabulary and the match
was case-insensitive. A gate that refuses good writing teaches people to route
around it. Terms listed capitalised now match case-sensitively, and a
sentence-initial capital, where the capital is mandatory and therefore carries no
signal, is reported as a warning for a human rather than failed by a guess.

**And one adjustment the data made before any agent ran.** The Spanish overflow rule
was a flat 1.30 ratio, which rejects correct translations of short strings:
`Resume`/`Continuar`, `Retry`/`Reintentar`, `Settings`/`Configuración`. An absolute
floor of six characters was added; the two terms cross at twenty, so the floor
governs buttons and the ratio governs prose.

Then the first real run produced, as its very first record, `Resume` → `Continuar`.
The old rule would have rejected the first string the pipeline ever wrote. A defect
found by arithmetic was confirmed, unprompted, by the generator.

---

## 8. Reproducing this

```bash
# The corpus and the retrieval measurement (no model calls, no keys)
python3 agents/retriever.py --stats
python3 agents/retriever.py --eval           # tiered + filename indexed
python3 agents/retriever.py --eval --flat    # the measurement that motivated both fixes

# Retrieve, then generate → gate → review
python3 agents/retriever.py --query "<what this screen must say>" --k 4 --context
python3 agents/runner.py --pipeline --agent 13 --output st_ui_<screen>.json --input "<brief + context>"

# The gate alone, including the cross-reference against layouts
python3 agents/validators.py --kind strings --file table.json --umg screen.json

# 70 tests, including the drift guard that holds the code to the budgets note
python3 -m unittest discover -s agents
```

### Repository layout

```
agents/
  retriever.py          chunking, BM25, the labelled evaluation   ← new in #4
  ui_rules.py           the UI arithmetic; numbers cite ui-budgets.md   ← new in #4
  validators.py         the deterministic gate, now including --kind strings
  room_rules.py         geometry rules (imported by the gate)
  runner.py             orchestrator: routes agents to subscription CLIs
  13-ui-copy-writer.md  the RAG generator      ← new in #4
  14-ui-copy-reviewer.md the semantic reviewer ← new in #4
  07-ui-designer.md     the layout half, rewired to the contract
  test_*.py             70 tests, including the drift guard on the budgets note
vault/                  the design canon — the retrieval corpus, and the pinned notes
  07-ui-and-controls/   uispec.md · ui-constraints.md · ui-budgets.md   ← new in #4
GDD/GDD-course-scope.md the slice specification, also part of the corpus
production/output/      the five string tables and their ten verdicts
```

Artifacts, every one with its `.gate.json` and `.review.json` siblings — the
deterministic verdict and the semantic one persisted beside each run rather than
printed and lost:

| File | Gate | Reviewer |
|---|---|---|
| `st_ui_pause.json` | PASS | PASS |
| `st_ui_hud.json` | PASS | PASS |
| `st_ui_runcomplete.json` | PASS | **REVISE** — 2 findings |
| `st_ui_runcomplete_asreviewed.json` | **FAIL** — 2 errors | — (never reached it) |
| `st_ui_runcomplete_refined.json` | PASS | PASS (second pass) |
