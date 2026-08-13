# HUD & Screen Specifications — Echoes (GDD V2)

## Minimalist Dread HUD Philosophy
- **Health:** Segmented health pips (4–6 hits to die).
- **Meters:** Energy meter for Titan Shield ONLY. Hunter has zero meters (binary verbs).
- **Contextual Prompts:** Minimalist interact prompts (`[X]`), keycard status icon post-Boss 1.
- **Teaching prompts are NOT HUD** (GDD §4.4). The interact glyph floats
  **world-space** over lore nodes and checkpoints; traversal-key prompts sit on the
  grapple point or the cracked wall itself, run for the **first uses and then
  retire** `[TUNE: prompt retirement rule]`; and tutorial prompts are **world-space
  signage, in-fiction where possible**. The full kit is introduced up front rather
  than dumped unexplained, but it is introduced **in the level**, not on an overlay.

  They are still authored copy and still live in `ST_UI` — a world-space widget
  pulls its text from a String Table like any other. What changes is the rung of the
  diegesis ladder they occupy (`ui-constraints.md`): spatial or diegetic, never a
  screen overlay. Teaching that has to retire is teaching the world is expected to
  take over.
- **Excluded HUD Elements:** NO boss health bar (visual phases indicate damage), NO minimap (wayfinding via visibility rule), NO ammo counters, NO damage numbers.

## Cut Features — Denylist

Systems the slice does not have. **No widget id, type, binding or string-table key
may reference one, and no shipped string may name one.** Their absence is the
design: copy that names a cut feature promises a system that does not exist, and a
widget that displays one contradicts a decision made on the record.

**Tokens are written in prose form**, lowercase, with the spaces a player would
read. Prose is matched on word boundaries, tolerating a plural suffix; identifiers
are matched as substrings of the same token with its separators removed, so
`boss health` catches a widget called `bar_boss_health`. Writing them the other way
round does not work: an identifier-shaped token never matches the sentence.

Tokens must be specific enough not to catch legitimate copy. "completion
percentage" is cut; **"completion time" is a Run-Complete stat** and must keep
working, which is why no row says merely "completion".

| Cut Feature | Match Tokens | Cut in |
|---|---|---|
| Boss health bar | boss bar, boss health, barra de vida | §4.4 |
| Minimap or map screen | minimap, map screen, world map, minimapa | §4.4 |
| Ammo counter | ammo count, ammo counter, munición | §4.4 |
| Damage numbers | damage number, número de daño | §4.4 |
| Difficulty settings | difficulty, dificultad | §3 non-goals |
| Completion percentage | completion percentage, percent complete, porcentaje | §4.4 |
| Save slots beyond checkpoints | save slot, save game, partida guardada | §3 non-goals |

## Screen Roster
- **Main HUD (`HUD_Main`):** the in-run HUD, defined by the philosophy above (pips,
  Titan energy meter, contextual prompts — and nothing from the excluded list).
- **Class Select Screen:** Preview Hunter (grapple agility) vs Titan (shield bash force).
- **Pause Menu:** Minimalist settings, accessibility toggles, exit run.
- **Run-Complete Screen:** Displays completion time, stats, and names what this class never saw (sells the 2nd run for opposite class).
