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

Four constraint types, each read live at runtime from the vault note that owns
it. Nothing is restated: a style rule copied into a second place is a rule that
will eventually disagree with itself, and the one that gets obeyed is whichever
document the reader happened to open.

| # | Constraint type | Source of truth | What it fixes |
|---|---|---|---|
| 1 | **Vocabulary & IP** | `vault/00-core/terminology-guard.md` | banned working placeholders, banned region references |
| 2 | **Tone** | `vault/05-lore/architects-cosmology.md` | the narrative register |
| 3 | **Format & length** | `vault/07-ui-and-controls/ui-budgets.md` | per-widget character caps, in both languages |
| 4 | **Function** | `vault/07-ui-and-controls/ui-constraints.md` | the string still has to do its job |

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

### 4 — Function

The first three rules make text *sound* like Echoes. This one makes it *work*.
`ui-constraints.md` states the beat every string has to hit:

> **GLANCE** — it is seen without being looked for.
> **GRASP** — it lands in one pass. **Rereading is the failure.**
> **ACT** — it changes a decision. *"What does the player do differently because
> they read this?"* has to have an answer.
> **TRUST** — it tells the truth about the state of the game, every time.

The agent also loads **the job of the screen the string belongs to**, because
copy that serves a different screen's job is wrong even when well written. A
`MenuLabel` is judged against Pause's job — *"plain where plain is correct; a
pause menu with voice in it is a pause menu getting in the way"* — while a
`ClassTagline` is judged against Class Select's, which is to preview two
fantasies, agility and force.

This rule was added after the first run of this assignment shipped text that
scored a perfect 10 and could not be used. Section
"[The failure that made Rule 4](#the-failure-that-made-rule-4)" below is that
episode in full.

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

**Rules 2 and 4 get no findings at all**, because no regex reaches tone and none
reaches whether a label can be understood. That is where the judge earns its
place, and Example 2 is the proof: zero deterministic findings, and it still
caught five distinct violations.

Scores are floored, not merely weighted. Any banned placeholder, region reference
or over-cap string holds the score at 6 regardless of how good the writing is,
because those three ship broken — and the same ceiling now applies to Rule 4,
which the evaluator must argue against its own taste before awarding a 9 or 10:

> *If this is a menu label: can a player predict what pressing it does, without
> pressing it? If not, cap the score at 6 however good the voice is.*
> *If this is a class tagline: would it sit equally well under the OTHER class?*

That instruction exists because the loop failed exactly there once — see
"The failure that made Rule 4" below.

---

## Before and after, on real content for this game

Three seeds, each deliberately wrong in a different way, all run through the same
loop with no intervention. Full transcript with every score and reason:
`production/output/A7_style_demo.style.json`.

| # | Violation class | Widget | Score | Attempts |
|---|---|---|---|---|
| 1 | Vocabulary & IP | `ProseBlock` | **1 → 9** | 2 |
| 2 | Tone | `ClassTagline` | **2 → 10** | 2 |
| 3 | Format & length | `MenuLabel` | **2 → 9** | 2 |

Every "after" was then re-measured independently by the deterministic checker:
**zero findings on all three**. Two of the three settle at 9 rather than 10,
which is the rubric grading its own output honestly rather than flattering it.

### Example 1 — Vocabulary and IP · run-complete prose · 1/10 → 9/10

**Before**
> EN — The Light guided your Ghost through the Hive nest, Guardian. The Traveler watched over this Mexican valley and its pyramid.
> ES — La Light guio a tu Ghost por el nido Hive, Guardian. El Traveler vigilaba este valle mexicano y su pirámide.

Fourteen deterministic findings across the two languages: six banned placeholders
in English, six in Spanish, and a region reference in each.

**Evaluator's reason (excerpt)**
> This text violates Rule 1 catastrophically and is unshippable. Every banned placeholder is present: "Light" (→Weave), "Ghost" (→Beacon), "Hive" (→Remnants/Facets), "Traveler" (→Architects) in both languages. Both texts also contain prohibited region references: "Mexican" and "pyramid" in English, "mexicano" and "pirámide" in Spanish. Rule 1 has no exceptions; these terms must be replaced before th…

**After**
> EN — This traverse leaves passages unexplored, their depths beyond sight. The Weave holds what remains unread. Return to the Architects' halls, and doorways will open where before they were sealed
> ES — Este recorrido deja pasajes sin explorar, sus profundidades fuera de vista. La Trama guarda lo que permanece sin leer. Regresa a los salones de los Arquitectos, y las puertas se abrirán donde antes estaban cerradas

Every placeholder is replaced by its approved term rather than deleted, and the
valley keeps its identity through geology instead of being named. Note what Rule 4
added: Run-Complete's job is *to sell the second run*, so the line now ends on the
doors that will open — a replay hook, not just atmosphere.

### Example 2 — Tone · Titan class tagline · 2/10 → 10/10

This is the case with **no deterministic findings at all**. Both strings sat
comfortably under the 48-character cap and carried no banned term. A gate built
only on measurement passes this text.

**Before**
> EN — Awesome tank build, champ!
> ES — ¡Tanque increíble, campeón!

**Evaluator's reason**
> This text fails multiple rules and is off-brand at the concept level.

**Rule 2 (Tone):** The text violates nearly every tonal requirement. It is cheerful and congratulatory ("Awesome… champ!"), uses exclamation marks (prohibited), addresses the player directly as a player, employs modern casual idiom ("Awesome", "champ"), and speaks from outside the world commenting on the player's choice rather than from inside the world. The register is upbeat marketing copy, not "sci-fi melancholic, ancient architectural mystery." The Spanish "¡Tanque increíble, campeón!" mirrors these failures.

**Rule 3 (Format):** Interface text carries no terminal punctuation. Both languages end with exclamation marks, which is a direct violation.

**Rule 4 (Function):** This text could sit unchanged under the Hunter class (or under any tank character in any game ever shipped) and fails the core requirement that 

**After**
> EN — Stone against the unraveling
> ES — Piedra contra lo que se deshace

Violations no regex reaches: the exclamation marks, the congratulatory register,
"champ" addressing the player from outside the world, "tank build" speaking to
them as a gamer rather than a Weaver, "Awesome" as marketing voice. And the
replacement satisfies Rule 4 as well as Rule 2 — *stone* is force, which is the
Titan's fantasy and not the Hunter's.

### Example 3 — Format and length · pause-menu label · 2/10 → 9/10

**Before**
> EN — Abandon the current run and return to the main menu! — 52 characters
> ES — Abandonar la partida actual y volver al menú principal para empezar de nuevo! — 77 characters

A `MenuLabel` caps at 20 per language. The Spanish also broke the overflow
allowance at 77 against an English 52 — the exact failure the bilingual rule
exists to catch, since Spanish decides whether a label fits.

**After**
> EN — Exit to Menu — 12 characters
> ES — Salir a Menú — 12 characters

Plain, and a player knows what pressing it does. That is Rule 4 and the Pause
screen's own job agreeing: this is the one screen where plain is correct.

---

## The failure that made Rule 4

The first version of this agent had three rules, and it produced text that scored
a perfect 10 and could not be used.

| Widget | Accepted at 10/10 under three rules | The problem |
|---|---|---|
| `MenuLabel` | `Unweave` / `Destejer` | flawless register; a player scanning a pause menu cannot tell it means *abandon the run* |
| `ClassTagline` | `The Weaver of echoes` | sits equally well under the Hunter, so it previews neither fantasy |

The diagnosis was initially wrong. The write-up said the missing rule *"is not in
`ui-budgets.md` yet"* — but it was never missing. `ui-constraints.md` already
required GRASP and ACT, and already told the Pause screen to stay plain. **The
contract was right and the agent had not been given it.**

That distinction matters more than the fix. A style agent is only as good as the
share of the law it is handed, and a guide assembled from three of four notes
will confidently approve text the fourth forbids — while sounding entirely
correct about the three it read.

Both strings were re-judged under the four-rule guide:

- `Unweave` — **10 → 6**. *"Beautifully voiced… but prioritizes voice over
  function at the cost of clarity."*
- `The Weaver of echoes` — **10 → 5**. *"Applies equally to both classes — any
  Weaver weaves echoes — and offers no reason for a player to choose Titan."*

The scoring rubric now floors any string that fails GRASP or ACT at 6 **however
good the voice**, and the refiner is explicitly forbidden from buying register
with clarity. The re-run above is the result: `Exit to Menu` instead of
`Unweave`, and `Stone against the unraveling` instead of a line that fitted
either class.

---

## What this agent does and does not do

It makes text sound like Echoes **and** hold its job on the screen it belongs to.
It cannot tell whether the underlying design decision was right: a perfectly
worded label for a menu entry that should not exist still scores 10.

The general lesson is the one Rule 4 came from. An agent optimising against a
guide will find the cheapest thing that guide accepts, so every clause you leave
out is a clause it will happily violate — persuasively, and at full marks.
