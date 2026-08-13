# UI Budgets — Echoes

The counts every string must respect. What the words are *for* is
`ui-constraints.md`; the format they travel in is `uispec.md`. This note holds
only numbers, and it is the single place they live: `ui_rules.py` reads its
figures from here and cites this file beside each constant.

**Read this warning before designing against these figures.** Unlike
`../04-world/movement-reach.md`, whose every number is measured in play, most of
the numbers below are **industry ranges plus judgment**. The Basis column says
which is which, and nothing here claims to be measured that was not. The two
kinds must not be confused: an industry range is a starting point that survives
until this project's own data contradicts it, and a judgment cut is an argument
that someone should be able to win against.

Every figure marked `[TUNE]` is expected to move once real strings exist.

## Spanish overflow

The origin rule is in `../05-lore/bilingual-string-tables.md`: `text_en` and
`text_es` are authored together, never translated afterwards. This section only
bounds the result so it fits the widget.

| Quantity | Value | Basis |
|---|---|---|
| Spanish expansion over English, game UI | 15–30% | industry range, several localization sources; Romance languages cluster at 20–30% |
| Ratio cap | **1.30** | GDD V2 decision; sits at the top of that range |
| Absolute floor | **+6 characters** `[TUNE]` | judgment — see the failure below |

**The rule:**

```
len(text_es) <= max(len(text_en) * 1.30, len(text_en) + 6)
```

**Why the floor exists.** A percentage cap punishes short strings, and short
strings are exactly what a menu is made of. The ratio alone rejects correct
translations:

| English | Spanish | Ratio cap | Ratio alone | With floor |
|---|---|---|---|---|
| Resume (6) | Continuar (9) | 7.8 | **rejected** | 12 → passes |
| Retry (5) | Reintentar (10) | 6.5 | **rejected** | 11 → passes |
| Settings (8) | Configuración (13) | 10.4 | **rejected** | 14 → passes |
| Exit (4) | Salir (5) | 5.2 | passes by 0.2 | 10 → passes |

The two terms cross at 20 characters (`1.30x = x + 6`). **Below 20 characters the
floor governs; above it the ratio governs** — which is the correct shape, because
long strings have slack a four-letter button does not.

The floor is not a licence to overflow: the absolute caps in the next section
apply to **both** languages regardless of ratio, and they are what actually
protects the widget.

## Per-widget-class caps

Characters, applied to `text_en` **and** `text_es` independently. These are the
figures that keep a string inside its box; the ratio rule above only keeps the
two languages comparable.

The `widget_class` column is the literal field value from `uispec.md` that selects
each cap. It is written here so the figures can be checked against the code that
reads them: `test_ui_rules.py` parses this table and fails if `ui_rules.py`
disagrees with any row.

| Widget class | `widget_class` | Cap | Basis |
|---|---|---|---|
| Contextual prompt | `Prompt` | **24** `[TUNE]` | judgment — one verb, optional object, no clause |
| Menu label (button, list row) | `MenuLabel` | **20** `[TUNE]` | judgment — list scanning; this is where the +6 floor does its work |
| Option value (toggle state, locale name) | `OptionValue` | **16** `[TUNE]` | judgment |
| Option description (one line, never wraps) | `OptionDescription` | **80** `[TUNE]` | judgment |
| Class name | `ClassName` | **16** `[TUNE]` | judgment |
| Class tagline | `ClassTagline` | **48** `[TUNE]` | judgment — one line under the name |
| Run-Complete stat label | `StatLabel` | **20** `[TUNE]` | judgment, consistent with menu labels |
| Run-Complete prose block | `ProseBlock` | **240** `[TUNE]` | judgment — the only prose budget in the game |
| In-run HUD text | — | **0** | design, not judgment — see below |

**In-run HUD text is zero.** `hud-and-screens.md` puts pips, the Titan energy
meter, contextual prompts and the keycard state in the HUD, and of those only the
prompt carries words — and a prompt is transient, tied to a nearby interactable,
and budgeted on its own row above. Nothing persistent in the HUD is text. This is
the arithmetic consequence of the ~0.5 s glance band: at that budget the player
recognises a shape, and reading has not happened yet.

## The glance bands are intent, not derivation

`ui-constraints.md` prices attention in seconds: ~0.5 s for an in-run HUD
element, ≤1 s for a prompt, ≤2 s for a menu label, unbounded on Run-Complete.

**The caps above are not derived from those seconds.** They come from widget
geometry and from the localization floor. Presenting a reading-speed calculation
that connects them would be false precision — on-screen glance reading under
gameplay load has no reliable constant to divide by.

The honest version: the seconds state the *intent*, the characters *implement* an
estimate of it, and one experiment would connect them. **The experiment:** show
each screen for its band's duration, then ask what the player read. A cap is too
generous if the string was not finished, and too tight if the player had time to
spare and the string had to drop information the design wanted. Until that runs,
every cap above stays `[TUNE]`.

## Format-specifier parity

A specifier is a token the runtime substitutes: `{0}`, `%s`, or an action token
(below). Localization breaks silently when the two languages disagree about them
— a missing specifier truncates, an extra one substitutes garbage or crashes.

**The rule:** the multiset of specifiers in `text_en` equals the multiset in
`text_es`. Order may differ — Spanish word order legitimately reorders them —
count and identity may not.

Purely arithmetic, and cheap. There is no reason for a model to ever be asked
about it.

## Button naming, and a conflict to settle

`control-scheme.md` is gamepad-first with full keyboard fallback and no mouse
aiming, and GDD §4.5 puts **input remap** in the pause menu.

Those two facts make a hardcoded button letter a lie: remap the interact binding
and every string naming the old button is wrong. The rule that follows is that a
prompt carries an **action token** — `<Interact>`, `<Dodge>` — which the runtime
resolves to whatever glyph is currently bound, and never a literal letter.
Deterministically checkable: a prompt string containing a bare glyph literal
fails; it must contain a token.

> ⚠️ **Unresolved.** `hud-and-screens.md` specifies "minimalist interact prompts
> (`[X]`)", which is a hardcoded glyph, and contradicts input remap being in
> scope. This is a design decision, not a typo, so it is flagged rather than
> silently changed: either prompts move to action tokens, or remap drops out of
> scope. The TRUST beat in `ui-constraints.md` says a prompt must tell the truth
> about the state of the game, which argues for tokens.

## Safe area

| Quantity | Value | Basis |
|---|---|---|
| Title-safe region | inner **90%** of the frame | long-standing console/TV convention `[VERIFY]` |
| Action-safe region | inner **95%** | same `[VERIFY]` |

All text anchors inside title-safe. `[VERIFY]` means: confirm against UE's own
safe-zone settings and the packaged build on a TV before treating these as
settled — the convention is stable, its exact expression in UE 5.7.4 is not yet
checked in this project.

## Set-level counts

A table of strings fails as a set even when every string passes alone.
`ui-constraints.md` explains why the sign is inverted from the room batch rules
(rooms fail by being too similar, strings by being inconsistent). The countable
part:

| Rule | Value | Basis |
|---|---|---|
| Distinct keys per screen | ≤ **14** `[TUNE]` | judgment — a cap that catches menu bloat before layout does |
| Two keys with identical text | **0 allowed** | either a redundant key or a lost distinction |
| Approved-term spelling variants across the set | **0 allowed** | `../00-core/terminology-guard.md` is the authority |
| Grammatical mood per prompt set | **1** | judgment — mixed moods read as mixed authorship |
| Keys referenced by a widget with no string | **0** | dangling reference: an empty widget ships |
| Strings with no widget referencing them | **0** | orphan work nobody sees |

The last two are the cross-reference between the layout specs and the string
table, and they are the integration checkpoint for this pipeline: content that
fails them must not reach the engine.

## What the gate enforces

**Arithmetic, in `ui_rules.py`** — the ratio-plus-floor rule; every per-class
cap, both languages; specifier parity; the action-token rule; placeholder
detection (`Lorem`, `TODO`, `TBD`); banned terms from
`../00-core/terminology-guard.md`; the excluded-HUD and cut-feature denylists;
every set-level count above.

**Judgment, and not checkable here** — whether the string earns its place at all,
whether the Spanish reads as origin rather than translation, and whether the
voice is the game's. Those are the reviewer's, and `ui-constraints.md` is what it
cites.

## Related

- `ui-constraints.md` — what the words are for; the glance bands as intent.
- `uispec.md` — the format, the key grammar, what the gate checks.
- `hud-and-screens.md` — the screen roster and the excluded elements.
- `control-scheme.md` — gamepad-first input.
- `../05-lore/bilingual-string-tables.md` — the EN/ES origin rule and the seam.
- `../04-world/movement-reach.md` — the model this note follows, and the standard
  of evidence it does not yet meet.
