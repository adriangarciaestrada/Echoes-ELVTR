# UISpec — the UI contract

The single definition of what a screen and a string are. The UI Designer writes
the layout, the Copy Writer writes the strings, the deterministic gate enforces
both, and the importer builds from them. When this changes, those change together;
nothing here is restated elsewhere — including in an agent's prompt.

What the words are *for* is `ui-constraints.md`; the counts they must respect are
`ui-budgets.md`.

## Two artifacts, one seam

A screen is produced twice, by two agents that never see each other's output:

- **`UMGSpec`** — where things sit. Widgets, anchors, positions, sizes. Carries
  **no text**, only *references* to text.
- **`StringTable`** — what things say. Bilingual records addressed by key.

The seam between them is the key. A widget names a key; a record defines it. That
separation is what makes hardcoded strings impossible by construction, and it is
what gives the pipeline an integration checkpoint: the two artifacts either agree
about the set of keys or the content does not ship.

## Coordinates and units

- **Screen space is `x` (right) and `y` (down)**, in the layout's design
  resolution. World space is `x`/`z` (`../04-world/roomspec.md`). The two never
  mix, and no UI field ever carries a `z`.
- `position` is the widget's own origin as interpreted by its `anchor`; `size` is
  `w` × `h`. Both are numbers, and `w`/`h` are strictly positive.
- All text anchors inside the title-safe region (`ui-budgets.md`).

## Keys

`ST_<Table>.<Key>` — matched by the gate as `^ST_\w+\.\w+$`.

- `ST_UI` for interface copy, `ST_Lore` for discovered lore. A key never crosses
  tables.
- `<Key>` is `Screen_Thing` (`Pause_Resume`, `ClassSelect_HunterTagline`) —
  screen prefix first, so the table sorts into the screens that use it.
- **A key is permanent.** Renaming one is a migration across both artifacts and
  the engine's assets, so keys are chosen to survive their first draft.
- A string used on more than one screen is **one key referenced twice**, never two
  keys with the same text (`ui-budgets.md` allows zero duplicates).

## Fields — `UMGSpec`

| Field | Shape | Notes |
|---|---|---|
| `screen_id` | enum | `HUD_Main` · `Screen_ClassSelect` · `Screen_RunComplete` · `Screen_Pause` |
| `widgets` | `[{...}]` | non-empty |
| `widgets[].id` | string | unique within the screen |
| `widgets[].type` | string | UMG widget type, e.g. `TextBlock`, `ProgressBar`, `Image` |
| `widgets[].anchor` | string | how `position` is interpreted |
| `widgets[].position` | `{x, y}` | numbers |
| `widgets[].size` | `{w, h}` | numbers, both > 0. Must fit its key's `widget_class` cap **in the longer language** |
| `widgets[].binding` | string | optional data binding, e.g. the pips' health source. Never a text source |
| `widgets[].string_table_key` | string | **required on any widget whose `type` contains "text"**; forbidden elsewhere |

`binding` and `string_table_key` are the two ways a widget gets content and they
never overlap: a binding carries live state, a key carries authored words. Both are
read by the excluded-element check, so neither may name a boss bar, a minimap, an
ammo count or a damage number.

## Fields — `StringTable`

Shaped like `DT_PlayerFeel`'s `{table, rows}` (agent 12), with a name that fits
strings.

| Field | Shape | Notes |
|---|---|---|
| `table` | enum | `ST_UI` · `ST_Lore` |
| `records` | `[{...}]` | non-empty |
| `records[].key` | string | the full `ST_<Table>.<Key>`, unique in the set |
| `records[].screens` | `[enum]` | every screen that references it; non-empty |
| `records[].widget_class` | enum | `Prompt` · `MenuLabel` · `OptionValue` · `OptionDescription` · `ClassName` · `ClassTagline` · `StatLabel` · `ProseBlock` |
| `records[].text_en` | string | non-empty |
| `records[].text_es` | string | non-empty, authored in origin — never translated after |
| `records[].source_chunks` | `[string]` | `path#heading` of every retrieved chunk this record was written from; non-empty |

## `string_table_key` is the seam, `widget_class` is what makes it checkable

Two fields carry the contract.

**`string_table_key`** is the only path text takes into the game. A text widget
without one is a hardcoded string, which `bilingual-string-tables.md` forbids
outright — so the gate rejects it rather than letting the importer decide.

**`widget_class`** is what selects a budget. Every cap in `ui-budgets.md` is
keyed on it: a `Prompt` and a `ProseBlock` are both strings and are not remotely
the same object. Without this field the gate can compute nothing, because it would
have no way to know which limit applies. It is declared by the writer rather than
inferred from the widget, so that a record can be checked on its own — before any
layout exists to compare it against.

## What is never a field

- **Character counts.** Parsed from the text. A declared length cannot disagree
  with the string it describes.
- **Specifier lists.** Parsed from both languages and compared
  (`ui-budgets.md`). Same reason.
- **Anything computed from the widget.** As with `camera_bounds` in
  `roomspec.md`: a value derived from the geometry is not authored beside it.

## Example — a fragment of `Screen_Pause`

Both artifacts, agreeing about three keys.

```json
{
  "screen_id": "Screen_Pause",
  "widgets": [
    { "id": "row_resume", "type": "TextBlock", "anchor": "CenterTop",
      "position": { "x": 0, "y": 0 },   "size": { "w": 420, "h": 56 },
      "string_table_key": "ST_UI.Pause_Resume" },
    { "id": "row_locale", "type": "TextBlock", "anchor": "CenterTop",
      "position": { "x": 0, "y": 72 },  "size": { "w": 420, "h": 56 },
      "string_table_key": "ST_UI.Pause_Language" },
    { "id": "row_exit",   "type": "TextBlock", "anchor": "CenterTop",
      "position": { "x": 0, "y": 144 }, "size": { "w": 420, "h": 56 },
      "string_table_key": "ST_UI.Pause_ExitRun" }
  ]
}
```

```json
{
  "table": "ST_UI",
  "records": [
    { "key": "ST_UI.Pause_Resume",   "screens": ["Screen_Pause"],
      "widget_class": "MenuLabel",
      "text_en": "Resume",   "text_es": "Continuar",
      "source_chunks": ["vault/07-ui-and-controls/hud-and-screens.md#Screen Roster"] },
    { "key": "ST_UI.Pause_Language", "screens": ["Screen_Pause"],
      "widget_class": "MenuLabel",
      "text_en": "Language", "text_es": "Idioma",
      "source_chunks": ["vault/05-lore/bilingual-string-tables.md#Origin Rule"] },
    { "key": "ST_UI.Pause_ExitRun",  "screens": ["Screen_Pause"],
      "widget_class": "MenuLabel",
      "text_en": "Exit Run", "text_es": "Abandonar",
      "source_chunks": ["vault/00-core/game-pillars.md#Deliverable & Win/Loss Conditions"] }
  ]
}
```

`Resume` → `Continuar` is the case the ratio rule alone rejects and the absolute
floor admits (`ui-budgets.md`). It is used as the example on purpose: the most
ordinary string in the game is the one that breaks a percentage cap.

A `Prompt` record looks the same and carries an action token in both languages —
`"<Interact> Open"` / `"<Interact> Abrir"` — which **assumes the action-token
resolution of the open `[X]` conflict flagged in `ui-budgets.md`**. If that
resolves the other way, this contract changes with it.

## What the gate checks

**Structural** — `screen_id` in the enum; widgets non-empty; widget ids unique;
`type` and `anchor` non-empty; numeric `position`; `size` positive; keys matching
`^ST_\w+\.\w+$`; a `string_table_key` on every text widget and on no other;
records non-empty; keys unique; `screens` and `widget_class` in their enums;
`source_chunks` non-empty.

**Budgets** — the per-`widget_class` character caps against both languages, and
the Spanish overflow rule with its absolute floor. All from `ui-budgets.md`, which
`ui_rules.py` reads rather than restates.

**Localization** — format-specifier parity between the two languages; action
tokens instead of bare glyph literals; placeholder text rejected.

**Content law** — banned terms from `../00-core/terminology-guard.md`; the
excluded-HUD patterns (`bossbar`, `bosshealth`, `minimap`, `ammocount`,
`damagenumber`), matched today against widget `id`/`type`/`binding`/`key` and
extended by this contract to `text_en` and `text_es`; the cut-feature denylist
(difficulty, map, completion percentage) which the excluded list does not yet
cover; the region rule — the country never named in either language.

**Cross-reference, measured across both artifacts rather than per file** — every
key a widget references is defined, and every record is referenced by at least one
widget. Dangling keys ship empty widgets; orphan records are work nobody sees.
Neither is visible while checking one artifact alone, which is why this family
exists.

**Set-level** — duplicate text, approved-term spelling variants, one grammatical
mood per prompt set, and the per-screen key cap. The counts are in
`ui-budgets.md`.

## Deliberately absent

Font, size, colour and style markup; rich text with inline icons; per-platform
string variants; audio or voice-over keys; plural and gender inflection
machinery; more than two locales; and any per-widget art direction.

Each would cost importer, gate and reviewer work, and none is needed to show that
this game's words are authored rather than typed into a Blueprint. Typography and
colour arrive from the marketplace UI kit in the art pass (`../00-core/asset-inventory.md`),
which is a stage the copy pipeline cannot see — so a review finding asking for
contrast, hierarchy or a heavier weight is a finding nobody here can act on.

## Related

- `ui-constraints.md` — what the words are for; the diegesis ladder; the ranked failures.
- `ui-budgets.md` — every number, and which are measured versus judged.
- `hud-and-screens.md` — the screen roster and the excluded elements.
- `../05-lore/bilingual-string-tables.md` — the EN/ES origin rule and the engine seam.
- `../04-world/roomspec.md` — the contract this one is modelled on.
