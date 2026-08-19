# Echoes — a Style Guide Agent

**ELVTR "Multi-Agent AI for Game Development" — Assignment #7.**

**Echoes** is a 2.5D metroidvania vertical slice in Unreal Engine 5.8: two
asymmetric classes, a shared map that splits at a class-gated junction, and a
boss named **La Costurera** who re-stitches the knights she commands. This agent
enforces the game's written style on every piece of user-facing text before it
reaches a widget.

```bash
python3 agents/style_loop.py --demo --out A7_style_demo    # the three violation classes
python3 agents/style_loop.py --brief "A pause-menu label for the controls screen" \
                             --widget-class MenuLabel
```

It runs on a personal subscription through a headless CLI. No API keys.

---

## Pipeline connection

**This Style Guide Agent runs immediately after the UI Copy Writer (agent 13)
generates a bilingual string and before the deterministic string-table gate, so
that every line reaching `import_stringtables.py` already speaks in the
Architects' register and carries no Destiny placeholder.**

---

## The style guide is not written here — it is assembled from the game's own contracts

Three constraint types, each read live at runtime from the vault note that owns
it. Nothing is restated: a style rule copied into a second place is a rule that
will eventually disagree with itself, and the one that gets obeyed is whichever
document the reader happened to open.

| # | Constraint type | Source of truth | What it fixes |
|---|---|---|---|
| 1 | **Vocabulary & IP** | `vault/00-core/terminology-guard.md` | banned working placeholders, banned region references |
| 2 | **Tone** | `vault/05-lore/architects-cosmology.md` | the narrative register |
| 3 | **Format & length** | `vault/07-ui-and-controls/ui-budgets.md` | per-widget character caps, in both languages |

### 1 — Vocabulary and IP

Echoes was drafted with Destiny working names and must ship legally clean. Each
placeholder has exactly one approved replacement, and the table is parsed from
the guard rather than typed into the prompt:

```
Traveler / Light             ->  Architects / Weave
Ghost                        ->  Beacon
Hive / Vex / Fallen / Scorn  ->  Remnants / Facets
Witch / Wizard               ->  La Costurera
Guardians                    ->  Weavers
Engram                       ->  Architect Fragment / Data Node
```

**The ban is on the capital, not the word.** `Light` is the placeholder and is
refused; `light` is an ordinary noun and passes. The check is case-sensitive for
exactly that reason — a rule that banned the lower-case word would make the game
unable to describe its own lighting.

A second table bans naming the setting's country in either language, along with
its off-allowlist iconography. The setting is *recognised, never announced*: the
place is carried by geology, light, vegetation and plausible toponymy instead.

### 2 — Tone

Quoted from the cosmology note, not paraphrased:

> *"Sci-fi melancholic, ancient architectural mystery, cryptic yet diegetically
> grounded."*

The consequences the agent enforces: no cheerfulness, no exclamation marks, no
congratulating the player, no addressing them as a player or a gamer, no
marketing register. The text speaks from inside the world or not at all.

### 3 — Format and length

Every string is authored in **both** English and Spanish — authored, not
translated — and the cap applies to each language independently. Spanish runs
longer, so **Spanish is the language that decides whether a string fits**.

| Widget class | Cap |
|---|---|
| `Prompt` | 24 |
| `MenuLabel` | 20 |
| `ClassTagline` | 48 |
| `ProseBlock` | 240 |

---

## The loop

```
Generator  →  writes a bilingual string for a named widget class
Evaluator  →  SCORE 1-10 + REASON, rule by rule
Refiner    →  takes the REASON and rewrites to clear it
```

The loop repeats until the score reaches **9/10** or the attempt budget runs out.
No human intervenes at any point.

### Why the judge is handed evidence

This project's standing preference is *deterministic check > LLM judge with an
explicit rubric > LLM judge with a vague prompt*. A score is not a deterministic
check, so the two are composed rather than chosen between.

The countable half — banned capitals, region leaks, character counts, the
Spanish overflow allowance — is measured in Python **first**, and those findings
go into the evaluator's prompt as facts it must account for. The judge still
owns the score, but it cannot invent a vocabulary violation that is not there or
miss one that is, and its reason is anchored to something a human can check.

**Tone gets no findings at all**, because no regex reaches it. That is where the
judge earns its place, and Example 2 below is the proof: zero deterministic
findings, and it still caught five distinct violations.

Scores are floored, not merely weighted: any banned placeholder, any region
reference, or any string over its cap holds the score at 6 or below regardless of
how good the writing is, because those three ship broken.

---

## Before and after, on real content for this game

Three seeds, each deliberately wrong in a different way, all run through the same
loop with no intervention. Full transcript with every score and reason:
`production/output/A7_style_demo.style.json`.

| # | Violation class | Widget | Score | Attempts |
|---|---|---|---|---|
| 1 | Vocabulary & IP | `ProseBlock` | **2 → 10** | 2 |
| 2 | Tone | `ClassTagline` | **3 → 10** | 2 |
| 3 | Format & length | `MenuLabel` | **2 → 10** | 2 |

Every "after" was then re-measured independently by the deterministic checker:
**zero findings on all three**. The 10/10s are verified, not self-reported.

### Example 1 — Vocabulary and IP · run-complete prose · 2/10 → 10/10

**Before**
> EN — The Light guided your Ghost through the Hive nest, Guardian. The Traveler watched over this Mexican valley and its pyramid.
> ES — La Light guio a tu Ghost por el nido Hive, Guardian. El Traveler vigilaba este valle mexicano y su pirámide.

Fourteen deterministic findings across the two languages: six banned placeholders
in English, six in Spanish, and a region reference in each.

**Evaluator's reason (excerpt)**
> This text is Destiny placeholder material that has not been adapted to Echoes, violating Rule 1 repeatedly and systematically across both languages. Banned placeholders in text_en: 'Light' (should be Architects or Weave), 'Ghost' (Beacon), 'Hive' (Remnants or Facets), 'Guardian' (Weaver), 'Traveler' (Architects). Identical violations in text_es. Region reference 'Mexican' / 'mexicano' violates the core setting rule (…

**After**
> EN — The Weave drew the Weaver onward. The Architects' vigil lies silent here—stone corridors, threads of light, the echo of ages long surrendered
> ES — La Trama atrajo al Tejedor adelante. La vigilancia de los Arquitectos yace silenciosa aquí—pasillos de piedra, hilos de luz, el eco de épocas ya cedidas

Every placeholder is replaced by its approved term rather than deleted — Weave,
Weaver, Architects — and the valley keeps its identity through geology and light
instead of being named. 141 and 152 characters against a 240 cap.

### Example 2 — Tone · Titan class tagline · 3/10 → 10/10

This is the case with **no deterministic findings at all**. Both strings were
comfortably under the 48-character cap and carried no banned term. A gate built
only on measurement would have passed this text.

**Before**
> EN — Awesome tank build, champ!
> ES — ¡Tanque increíble, campeón!

**Evaluator's reason**
> Rule 2 is systematically violated. The tone is cheerful and congratulatory ("Awesome," "increíble"), belonging to a modern game's reward UI rather than Echoes' sci-fi melancholic world. Exclamation marks are banned; neither "Awesome tank build, champ!" nor "¡Tanque increíble, campeón!" should use them. The text addresses the player casually ("champ"/"campeón") and as a gamer ("tank build"), treating them as external to the world rather than speaking from inside it. "Awesome" and "increíble" are marketing register, not the diegetically grounded voice required. The entire piece reads as a modern FPS UI congratulating a loadout choice, not as text from an ancient, silent, decaying civilization.

**After**
> EN — The Weaver of echoes
> ES — La Tejedora de ecos

Five distinct violations that no regex reaches: the exclamation marks, the
congratulatory register, "champ" addressing the player from outside the world,
"tank build" speaking to them as a gamer rather than a Weaver, and "Awesome" as
marketing voice. This is the whole argument for scoring rather than matching.

### Example 3 — Format and length · pause-menu label · 2/10 → 10/10

**Before**
> EN — Abandon the current run and return to the main menu! — 52 characters
> ES — Abandonar la partida actual y volver al menú principal para empezar de nuevo! — 77 characters

A `MenuLabel` caps at 20 per language. The Spanish also broke the overflow
allowance at 77 against an English 52 — the exact failure mode the bilingual rule
exists to catch, since Spanish is the language that decides whether a label fits.

**Evaluator's reason (excerpt)**
> The string breaks three rules fatally and cannot ship.

**Rule 3 (Length):** English 52 characters vs. cap 20 (32 over); Spanish 77 characters vs. cap 20 (57 over). As stated in the guide, any string over its cap is a hard-ship blocker. MenuLabel is a constrained widget and this text is nearly 4× the width allowed.

**Rule 3 (Punctuation):** "Interface text carries no terminal …

**After**
> EN — Unweave — 7 characters
> ES — Destejer — 8 characters

---

## What the loop got right, and one thing worth arguing with

The refiner did the hard half of its brief: it replaced placeholders with their
approved terms instead of deleting them, and it re-thought the Spanish as Spanish
rather than trimming it down to fit.

But Example 3's result deserves scrutiny rather than applause. `Unweave` /
`Destejer` scores a clean 10 — on register, on length, on vocabulary — and it is
**less clear than the string it replaced**. A player scanning a pause menu knows
what "Exit Run" does; "Unweave" is beautiful and ambiguous.

Example 2 shows the same pattern from another angle. `The Weaver of echoes` is
perfectly in register — and it is a **class tagline that does not distinguish the
class**. It would sit as comfortably under the Hunter as under the Titan, which
is precisely what a tagline on a class-select screen exists not to do.

That is a real property of this kind of loop, not a bug in this run: **an agent
optimising hard against a style score will trade function for register**, because
the guide it was given measures voice and says nothing about whether a menu label
can be understood at a glance or a tagline tells two classes apart. The rules
that would catch both — a label names its action, a tagline names what is unique
to its class — are not in `ui-budgets.md` yet. They should be, and they are the
natural next constraints to add.

Stated plainly: this agent makes text sound like Echoes. It does not make text
usable, and it should not be trusted to notice the difference.
