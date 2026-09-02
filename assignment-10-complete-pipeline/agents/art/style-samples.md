# Style samples — choosing the post-pixel-art direction

Purpose: decide, with side-by-side evidence, which rendering style replaces
pixel art before the full re-skin (all 22 sprites plus UI chrome). One test
run per candidate style, all rendering the SAME subjects, so the comparison
is apples-to-apples.

Status: sampling stage. `loom-vault/art-direction.md` still says "pixel art"
and stays law until a style is chosen here; the winner amends that note.
The itch.io AI-asset disclosure obligation is unchanged by the generator or
style.

## Test subjects (three per style)

Every style renders these three. Each probes a different failure mode:

| Subject | Probes | Target size |
|---|---|---|
| **A. Titan Weaver card** | the hero shot — does the style carry mood? Has an approved pixel-art version (`approved/weaver_titan_card.png`) to compare against | 348×400 (portrait) |
| **B. Sentry Node relic icon** | the hard test — does it still read as a token at 32×32 on a dark board? | 32×32 |
| **C. UI panel + button** | does the style extend to chrome (panels, frames, buttons), or only to illustrations? | n/a (mock) |

A style that wins A but fails B cannot be the game's style — most of the 22
assets live on the board at 32–96px, not at card size.

## Prompts (ready to paste)

Every prompt is self-contained: the world direction (deep blue-black
palette, pale teal highlights, one warm ember accent, dark stone and
luminous threads, sci-fi figure against ancient ruins) is baked into each
one, so only the rendering style varies between them. Generate 2 candidates
per prompt.

### Style 1 — Painted illustration

Card (A):
```
Painterly digital illustration, soft cinematic lighting, visible brushwork,
atmospheric depth. Full figure in a dynamic heroic pose, science-fiction
powered armour with hard-surface mechanical panelling, NOT medieval, NOT a
fantasy knight, standing in an ancient ruined stone arena with collapsed
walls and battle-scarred pillars. Muted desaturated palette of deep
blue-black with pale teal highlights and a single warm ember-orange accent,
dark ancient stone and luminous glowing threads. Portrait orientation. No
text, no watermark, no border.
```

Icon (B):
```
Painterly digital illustration of a single sentry turret emblem, centred on
a plain dark backdrop, strong readable silhouette, simple bold shapes that
stay readable when shrunk to a tiny 32-pixel game token. Muted desaturated
palette of deep blue-black with pale teal highlights and a single warm
ember-orange accent. Square image. No text, no watermark, no border.
```

UI (C):
```
Video game user interface style sample, painterly digital illustration
style: one rectangular panel, one card frame, and two buttons (one idle,
one highlighted), carved dark stone edges with a thin inlay of luminous
pale-teal thread, dark background. Muted desaturated palette of deep
blue-black with pale teal highlights and a single warm ember-orange accent.
Square image. No text, no watermark.
```

### Style 2 — Cel-shaded / comic

Card (A):
```
Cel-shaded comic illustration, bold clean linework, flat shading with
hard-edged shadows, strong rim light, high contrast. Full figure in a
dynamic heroic pose, science-fiction powered armour with hard-surface
mechanical panelling, NOT medieval, NOT a fantasy knight, standing in an
ancient ruined stone arena with collapsed walls and battle-scarred pillars.
Muted desaturated palette of deep blue-black with pale teal highlights and
a single warm ember-orange accent, dark ancient stone and luminous glowing
threads. Portrait orientation. No text, no watermark, no border.
```

Icon (B):
```
Cel-shaded comic illustration of a single sentry turret emblem, bold clean
linework, flat shading with hard-edged shadows, centred on a plain dark
backdrop, strong readable silhouette, simple bold shapes that stay readable
when shrunk to a tiny 32-pixel game token. Muted desaturated palette of
deep blue-black with pale teal highlights and a single warm ember-orange
accent. Square image. No text, no watermark, no border.
```

UI (C):
```
Video game user interface style sample, cel-shaded comic style with bold
clean linework and flat hard-edged shading: one rectangular panel, one card
frame, and two buttons (one idle, one highlighted), carved dark stone edges
with a thin inlay of luminous pale-teal thread, dark background. Muted
desaturated palette of deep blue-black with pale teal highlights and a
single warm ember-orange accent. Square image. No text, no watermark.
```

### Style 3 — Clean flat vector

Card (A):
```
Minimal flat vector illustration, geometric simplified shapes, bold
silhouette, flat colour fills, uniform line weight, subtle paper grain.
Full figure in a dynamic heroic pose, science-fiction powered armour with
hard-surface mechanical panelling, NOT medieval, NOT a fantasy knight,
standing in an ancient ruined stone arena with collapsed walls and
battle-scarred pillars. Muted desaturated palette of deep blue-black with
pale teal highlights and a single warm ember-orange accent, dark ancient
stone and luminous glowing threads. Portrait orientation. No text, no
watermark, no border.
```

Icon (B):
```
Minimal flat vector illustration of a single sentry turret emblem,
geometric simplified shapes, flat colour fills, uniform line weight,
centred on a plain dark backdrop, strong readable silhouette, simple bold
shapes that stay readable when shrunk to a tiny 32-pixel game token. Muted
desaturated palette of deep blue-black with pale teal highlights and a
single warm ember-orange accent. Square image. No text, no watermark, no
border.
```

UI (C):
```
Video game user interface style sample, minimal flat vector style with
geometric shapes and flat colour fills: one rectangular panel, one card
frame, and two buttons (one idle, one highlighted), carved dark stone edges
with a thin inlay of luminous pale-teal thread, dark background. Muted
desaturated palette of deep blue-black with pale teal highlights and a
single warm ember-orange accent. Square image. No text, no watermark.
```

### Style 4 — Control: current look, native resolution

The approved sprites are downscaled painted concept art, not true pixel art
(see the header of `import_gemini.py`). The cheapest option is to keep that
exact look but stop downscaling it into pixelation.

Card (A):
```
Detailed digital concept illustration, crisp hard-surface rendering,
cinematic lighting, no pixelation, no pixel-art grid. Full figure in a
dynamic heroic pose, science-fiction powered armour with hard-surface
mechanical panelling, NOT medieval, NOT a fantasy knight, standing in an
ancient ruined stone arena with collapsed walls and battle-scarred pillars.
Muted desaturated palette of deep blue-black with pale teal highlights and
a single warm ember-orange accent, dark ancient stone and luminous glowing
threads. Portrait orientation. No text, no watermark, no border.
```

Icon (B):
```
Detailed digital concept illustration of a single sentry turret emblem,
crisp hard-surface rendering, no pixelation, centred on a plain dark
backdrop, strong readable silhouette, simple bold shapes that stay readable
when shrunk to a tiny 32-pixel game token. Muted desaturated palette of
deep blue-black with pale teal highlights and a single warm ember-orange
accent. Square image. No text, no watermark, no border.
```

UI (C):
```
Video game user interface style sample, detailed digital concept art style
with crisp hard-surface rendering: one rectangular panel, one card frame,
and two buttons (one idle, one highlighted), carved dark stone edges with a
thin inlay of luminous pale-teal thread, dark background. Muted desaturated
palette of deep blue-black with pale teal highlights and a single warm
ember-orange accent. Square image. No text, no watermark.
```

## Procedure

1. In the Gemini web interface, generate 2 candidates per subject per style
   (24 images). Portrait framing for cards; square for icons and UI.
2. Save as `References/style-samples/<style>-<subject>-<n>.jpeg`
   (e.g. `painted-card-1.jpeg`, `vector-icon-2.jpeg`).
3. Downscale each icon candidate to 32×32 and each card to 348×400 (the
   `fit()` in `import_gemini.py` does this) and view them at game size on a
   dark background — judge the small version, not the 2000px original.
4. Pick the winning style; record the decision and the winning rendering
   clause below; amend `loom-vault/art-direction.md`; then regenerate the
   full inventory (`art-specs.json`, 22 assets) plus UI chrome in that
   style.

## Decision

**Style 3 — clean flat vector** (2026-08-31). All three test subjects
(card, icon, UI) read well in this style. Winning rendering clause,
verbatim, to open every production prompt:

> Minimal flat vector illustration, geometric simplified shapes, bold
> silhouette, flat colour fills, uniform line weight, subtle paper grain.

`loom-vault/art-direction.md` amended accordingly. Production prompts for
the full inventory accumulate in `gemini-prompts.md` as assets are
generated.
