# Production prompts — flat vector re-skin

Prompts for the manual Gemini (web interface) generation of the full asset
inventory in the chosen style (`style-samples.md` owns the decision; the
rendering clause below opens every prompt verbatim). Recorded here because
the original pixel-art run never recorded its prompts — provenance sidecars
name the source image but not the words that produced it.

Workflow per asset: generate several candidates in the Gemini web
interface → pick one → save it under `References/` with the exact filename
`import_gemini.py`'s `SOURCES` table expects (e.g.
`Hunter-card-chosen.jpeg`) → run
`python3 import_gemini.py --only <spec_id>`.

## The setting vocabulary

Environments draw from a shared vocabulary, never from a shared verbatim
clause: an identical setting sentence pasted into every prompt produced
three near-identical backgrounds, so each asset gets its own scene composed
from the same materials. The vocabulary
(`from-echoes/terminology-guard.md` is the law — the setting is recognised,
never announced, carried by geology, light and vegetation, with loaded
iconography off-allowlist):

- **Geology:** dark volcanic stone; broad, low stepped terraces; massive
  precisely fitted blocks; weathered geometric carvings worn almost smooth.
- **Vegetation:** agave-like succulents, prickly-pear cacti, dry golden
  grasses — growing from cracks and edges.
- **Light:** the main differentiator between scenes — cold pre-dawn mist,
  harsh high-altitude midday, dusk with the luminous threads glowing.
- **Negatives, always:** no columns, no arches, no Greco-Roman
  architecture — the generator's default for "ancient ruins" is classical,
  which is how the first-generation cards ended up with amphitheatres and
  announced the wrong place entirely.

## UI chrome (menu screens)

Course correction after the first drawn-chrome prototype: code keeps
layout, states and interaction, but every visual surface (background,
frames, plaques) is generated — the drawn-only version read as bare. The
design resolution is a fixed 1280×720 (`theme.ts`), so frames are generated
at fixed aspect ratios and imported at exact sizes like the cards; nothing
ever stretches. Glyph ornament is always "abstract angular carved glyphs,
no real writing system" — legible-as-decoration, attributable to no one
(`from-echoes/terminology-guard.md`).

### `ui_background` (1280×720)

```
Minimal flat vector illustration, geometric simplified shapes, flat colour
fills, uniform line weight, subtle paper grain. A dark, quiet background
for a video game menu screen: a wall of ancient fitted volcanic stone
blocks seen straight on, sparse abstract angular carved glyphs worn almost
smooth (no real writing system), a few thin luminous pale-teal threads
running along the seams between blocks like veins of light. Very dark,
very low contrast, no focal point, no characters — foreground interface
elements must stay readable on top of it. Muted desaturated palette of
deep blue-black with pale teal highlights. Landscape orientation, 16:9.
No columns, no arches, no Greco-Roman architecture. No text, no watermark,
no border.
```

### `ui_card_frame` (350×430)

The centre window is requested plain and dark; tooling punches it to
transparency so the portrait sits inside the frame.

```
Minimal flat vector illustration, geometric simplified shapes, flat colour
fills, uniform line weight. An ornate rectangular FRAME for a video game
character card, in carved dark volcanic stone: thick border decorated with
abstract angular carved glyphs (no real writing system), diagonally cut
corners, a thin luminous pale-teal thread inlaid around the inner edge of
the border, one small amber gem set at the top centre. The centre of the
frame is a completely plain, solid, very dark empty rectangle — the
character portrait will be placed there later. Portrait orientation,
border width about one tenth of the image width. Muted desaturated palette
of deep blue-black with pale teal highlights and a single warm amber
accent. No columns, no arches, no Greco-Roman architecture. No text, no
watermark.
```

### `ui_button` (240×92)

One idle plaque; the hover state is added in code (amber outline and a
brightness tint), so one asset serves every state.

```
Minimal flat vector illustration, geometric simplified shapes, flat colour
fills, uniform line weight. A wide rectangular BUTTON plaque for a video
game menu, carved from dark volcanic stone: chamfered corners, a border of
abstract angular carved glyphs (no real writing system), a thin luminous
pale-teal thread along the bottom edge, plain dark flat centre where a
text label will be drawn later. Wide landscape orientation, about 5:2.
Muted desaturated palette of deep blue-black with pale teal highlights.
No text, no watermark, no Greco-Roman ornament.
```

## Game-screen chrome (side panels + market)

Generated-first (owner's direction): every visible surface comes from a
generated asset; code draws only what an asset cannot be — live bars,
tints, hover states composited from the base asset. Aspect ratios below
match their exact destinations; that match is what made the offer plaque
(2.49:1 vs a 2.39:1 slot) drop in cleanly.

### `ui_panel_frame_tall` (320×720 side panels, 4:9)

```
Minimal flat vector illustration, geometric simplified shapes, flat colour
fills, uniform line weight. A very tall, narrow rectangular FRAME for a
video game side panel, in carved dark volcanic stone: a THIN border, about
one twentieth of the image width, with small abstract angular carved
glyphs (no real writing system), diagonally cut corners, a thin luminous
pale-teal thread inlaid along the inner edge. The centre is a completely
plain, solid, very dark empty rectangle for interface content. Tall
portrait orientation, aspect ratio 4 wide by 9 tall. Muted desaturated
palette of deep blue-black with pale teal highlights. No columns, no
arches, no Greco-Roman architecture. No text, no watermark.
```

### `ui_banner` (panel headers ~320×44 and the centre HUD bar, ~7:1)

```
Minimal flat vector illustration, geometric simplified shapes, flat colour
fills, uniform line weight. A long, thin horizontal stone LINTEL banner
for a video game panel header, carved dark volcanic stone with a few small
abstract angular glyphs near both ends (no real writing system), chamfered
corners, a thin luminous pale-teal thread along the bottom edge, plain
flat centre where a title will be drawn later. Very wide landscape
orientation, about 7 wide by 1 tall. Muted desaturated palette of deep
blue-black with pale teal highlights. No text, no watermark, no
Greco-Roman ornament.
```

### `ui_button_small` (market row controls — take, banish, reroll, ~3:1)

```
Minimal flat vector illustration, geometric simplified shapes, flat colour
fills, uniform line weight. A SMALL rectangular button plaque for a video
game, carved dark volcanic stone, chamfered corners, a simple clean bevel
with a thin pale-teal inner line, plain dark flat centre for a short text
label, minimal ornament so it stays readable at a small size. Landscape
orientation, about 3 wide by 1 tall. Muted desaturated palette of deep
blue-black with pale teal highlights. No text, no watermark, no
Greco-Roman ornament.
```

### `ui_plaque_buff` (buff choice cards 580×120, ~5:1)

```
Minimal flat vector illustration, geometric simplified shapes, flat colour
fills, uniform line weight. A very wide, low stone PLAQUE for a video game
choice card, carved dark volcanic stone: a thin border with small abstract
angular carved glyphs (no real writing system), chamfered corners, a thin
luminous pale-teal thread inlaid along the inner edge, and along the left
edge a slightly raised smooth vertical strip in plain light grey stone
(the game colour-tints it). Plain flat centre for text. Very wide
landscape orientation, about 5 wide by 1 tall. Muted desaturated palette
of deep blue-black with pale teal highlights. No text, no watermark, no
Greco-Roman ornament.
```

The offer cards (244×102) need no new asset: the wide runic plaque already
generated (2.49:1) is their match. Hover states for all of these are
composited from the base asset with the orange-contour recipe in
`ui.ts`/`imageButton` — never generated separately, so idle and hover can
never drift apart in size again.

## Combat screen (phase D)

Design decisions baked into these prompts: enemies keep the game's
existing hue coding (walker violet, gunner amber, bosses crimson) so
gameplay reading survives the re-skin; Remnants render as faceted
crystalline creatures — an echo of their lore name ("Facets") that suits
flat vector; every token must survive the 32px shrink test. Shots, bars
and the pause chip stay code-drawn.

### `battlefield` (top-down lane, ~1:1.06)

```
Minimal flat vector illustration, geometric simplified shapes, flat
colour fills, uniform line weight. A TOP-DOWN battlefield ground for a
video game, seen from directly above: a wide lane of ancient fitted
volcanic stone slabs running vertically, worn by passage, sparse abstract
angular carved glyphs worn almost smooth (no real writing system), a few
thin luminous pale-teal threads along the seams, cracked slab edges, dry
grass tufts at the outer margins. Very dark and low contrast so game
pieces stay readable on top; no focal point, no characters. Nearly
square, slightly taller than wide. Muted desaturated palette of deep
blue-black with pale teal highlights. No columns, no arches, no
Greco-Roman architecture. No text, no watermark.
```

### `ui_ult_frame` (the ultimate's slab, 212×62, ~3.5:1)

```
Minimal flat vector illustration, geometric simplified shapes, flat
colour fills, uniform line weight. A wide ornate FRAME for a video
game's ultimate-ability button, carved dark volcanic stone with small
abstract angular glyphs (no real writing system), chamfered corners, a
thin luminous pale-teal thread inlay around the inner edge, one small
amber gem at each end. The centre is a completely plain, solid, very
dark empty rectangle — the game fills it with a charge meter. Wide
landscape orientation, about 3.5 wide by 1 tall. Muted desaturated
palette of deep blue-black with pale teal highlights and warm amber
accents. No text, no watermark, no Greco-Roman ornament.
```

### `beacon` (128×64, side view)

```
Minimal flat vector illustration, geometric simplified shapes, flat
colour fills, uniform line weight. The Beacon: a single low, wide,
ancient monolithic slab of dark volcanic stone, cracked with age, seen
from the side — luminous pale-teal threads glow through its cracks and
one bright thread-seam runs its length, with a small warm amber core at
the centre. Centred on a plain solid dark backdrop, strong readable
silhouette. Wide landscape orientation, about 2 wide by 1 tall. Muted
desaturated palette of deep blue-black with pale teal highlights. No
columns, no arches, no text, no watermark.
```

### Remnants — shared token clause

Every enemy prompt opens with the render clause and closes with:

> Top-down view seen from directly above, a single creature token centred
> on a plain solid dark backdrop, strong readable silhouette, simple bold
> shapes that stay readable when shrunk to a tiny 32-pixel game token.
> Muted desaturated palette of deep blue-black. No text, no watermark.

### `enemy_walker` (32×32)

```
Minimal flat vector illustration, geometric simplified shapes, flat
colour fills, uniform line weight. A Remnant walker: a jagged
crystalline shard-creature crawling forward on angular splinter limbs,
violet-purple facets over a dark core. Top-down view seen from directly
above, a single creature token centred on a plain solid dark backdrop,
strong readable silhouette, simple bold shapes that stay readable when
shrunk to a tiny 32-pixel game token. Muted desaturated palette of deep
blue-black. No text, no watermark.
```

### `enemy_gunner` (32×32)

```
Minimal flat vector illustration, geometric simplified shapes, flat
colour fills, uniform line weight. A Remnant gunner: a squat crystalline
shard-creature anchored on a tripod of splinters, one long faceted
barrel-spike aiming upward in the image, amber-orange facets over a dark
core. Top-down view seen from directly above, a single creature token
centred on a plain solid dark backdrop, strong readable silhouette,
simple bold shapes that stay readable when shrunk to a tiny 32-pixel
game token. Muted desaturated palette of deep blue-black. No text, no
watermark.
```

### `enemy_bulwark` (boss, 64×64)

Silhouette family: ONE solid wide mass. Rendered like the walker/gunner
tokens — the white-background "no shadow" round flattened everything
into stickers; the depth lives in per-facet tones, so it is asked for
explicitly and the backdrop returns to dark.

```
Minimal flat vector illustration, geometric simplified shapes, flat
colour fills, uniform line weight, each crystal facet its own flat tone
with subtle lighter edge-highlights giving low-poly depth. A colossal
armoured tortoise-like BEAST seen from directly above: one broad,
UNBROKEN dome-shell of thick overlapping crimson-red crystal plates,
clearly WIDER than it is tall, advancing like a living wall; only four
short thick feet peek from under the shell's sides and a blunt armoured
snout from under its front edge, facing DOWN the image. Crimson-red
facets over deep blue-black. A single creature token centred on a
plain, solid, very dark navy backdrop, in the same rendering style as
the other Remnant tokens. Strong readable silhouette that stays
readable when shrunk to a small game token. No text, no watermark.
```

### `enemy_splitter` (boss, 64×64)

Silhouette family: a CLUSTER visibly about to come apart. Mechanical
consistency: on death it spawns three WALKERS (battle.ts), so its three
lobes ARE walkers — described with the walker prompt's own words,
violet included, held in a crimson boss-matrix.

```
Minimal flat vector illustration, geometric simplified shapes, flat
colour fills, uniform line weight, each crystal facet its own flat tone
with subtle lighter edge-highlights giving low-poly depth. A Remnant
brood BEAST seen from directly above: THREE identical smaller
creatures — each a jagged crystalline shard-spider with violet-purple
facets over a dark core and angular splinter limbs — fused into one
lumpy wide body by a cradle of crimson-red crystal plates, brightly
glowing crimson fracture seams between the three, a beast visibly about
to split apart into its three spiders, facing DOWN the image. A single
creature token centred on a plain, solid, very dark navy backdrop, in
the same rendering style as the other Remnant tokens. Strong readable
silhouette that stays readable when shrunk to a small game token. No
text, no watermark.
```

### `enemy_disruptor` (boss, 64×64)

Silhouette family: RADIAL. Thick limbs only — thin threads and
filaments render as noodles in flat vector and stay banned.

```
Minimal flat vector illustration, geometric simplified shapes, flat
colour fills, uniform line weight, each crystal facet its own flat tone
with subtle lighter edge-highlights giving low-poly depth. A Remnant
unraveller BEAST seen from directly above: a bell-shaped crystalline
body crowned with crimson shard-plates around a dark slowly-whirling
core, with FOUR THICK, angular, segmented crystal arms spread radially
like a cross, each ending in a two-pronged hook reaching outward, the
front pair reaching DOWN the image. NO thin threads, NO filaments, NO
tentacle hairs — bold segmented limbs only. Crimson-red facets over
deep blue-black. A single creature token centred on a plain, solid,
very dark navy backdrop, in the same rendering style as the other
Remnant tokens. Strong readable silhouette that stays readable when
shrunk to a small game token. No text, no watermark.
```

### `weaver_*_back` (96×112, optional re-render)

The battle backs are the previous style's downscaled concept art; once
the battlefield is vector they will clash. Same character clauses as the
cards, viewed from behind and slightly above, facing away up the image,
full figure, on a plain solid dark backdrop for cutting out — e.g. for
the Titan:

```
Minimal flat vector illustration, geometric simplified shapes, flat
colour fills, uniform line weight. A massive, heavyweight titan in bulky
matte-black science-fiction powered armour with hard-surface mechanical
panelling and oversized shoulder plates, thin ember-orange accent lines
across the back and limbs, seen FROM BEHIND and slightly above, facing
away up the image, standing full figure in a wide planted stance. NOT
medieval, NOT a fantasy knight. Centred on a plain solid dark backdrop,
strong readable silhouette. Portrait orientation. Muted desaturated
palette of deep blue-black with pale teal highlights. No text, no
watermark.
```

(Hunter: sleek silver-white armour, pointed hood, crimson cape, lean
crouched-ready stance. Warden: polished silver-white armour, black dome
helmet, long black split cape from the waist, upright guarded stance.)

## The offer card, redesigned as one piece

Why this is one asset and not a card plus two buttons: the standalone
button plaque is a **widget-scale** asset — it carries its own stone,
bevel, glyph border and glow margin, which costs 34px of a 102px card to
deliver a 22px control, and reads as stone inside stone. And neither
layout gave the relic's colour a home: the category arrived as a stripe
laid over the composition rather than a part of it.

So the card is generated WITH its two action slots and TWO tinting
sockets built in, and the game draws only text and tints:

- **Category socket** (Bolt / Burst / Construct): a crystal set into the
  stone at the top-left. Tinted `#e08a5a`, `#d8556b`, `#6ea8d8`.
- **Tier**: stays in the footprint cells, which is the vault's law
  (`art-direction.md`: tier colour is the CELL BACKGROUND, never a sprite
  recolour) — so the card provides a recessed grid area for them.
- **Two action slots**: recessed panels carved into the card's own bottom
  edge, sharing its material. No separate plaque, nothing nested.

### `ui_offer_card` (244×102, ~2.4:1)

```
Minimal flat vector illustration, geometric simplified shapes, flat
colour fills, uniform line weight, each stone facet its own flat tone
with subtle lighter edge-highlights giving low-poly depth. A wide, short
horizontal CARD for a video game item offer, carved from dark volcanic
stone, seen straight on. Its composition, left to right and top to
bottom: a small faceted CRYSTAL GEM set into the stone at the top-left
corner, plain light grey so it can be colour-tinted later; to its right
a wide plain flat area for the item's name; below the gem a square
RECESSED GRID PANEL about one third of the card wide, sunken and empty,
its floor plain dark, where small coloured tiles will be drawn later; to
the right of that panel a plain flat area for two short lines of
numbers; and along the bottom edge TWO equal RECESSED RECTANGULAR SLOTS
side by side, carved into the card's own stone, each plain and empty
inside for a text label, separated by a narrow stone divider. Thin
luminous pale-teal thread inlaid around the card's outer rim only.
Sparse abstract angular carved glyphs (no real writing system) on the
narrow stone between areas, never inside them. Every plain area must be
FLAT and UNDECORATED so text stays readable. Muted desaturated palette
of deep blue-black with pale teal highlights. Wide landscape
orientation, about 2.4 wide by 1 tall. No text, no watermark, no
Greco-Roman ornament.
```

### `ui_gem_bolt` / `ui_gem_burst` / `ui_gem_construct` — one image, three gems

The card ships its gem in plain grey so it can carry a colour. Painting a
flat disc over it destroys the faceting that made it read as set stone,
so the coloured gems are generated instead — all three in ONE image, in a
row, so they cannot drift in shape or lighting from each other or from
the socket they drop into. Tooling cuts them apart and scales each to the
socket measured on the card (`Z.gem`).

Hex codes are the game's own category colours (`theme.ts`
`CATEGORY_MARK`), so the art matches what every other category mark in
the UI already uses.

```
Minimal flat vector illustration, geometric simplified shapes, flat
colour fills, uniform line weight, each facet its own flat tone with
subtle lighter edge-highlights giving low-poly depth. THREE faceted
hexagonal crystal GEMS in a row on a plain solid pure white background,
evenly spaced and clearly separated, all three identical in shape, size,
cut and lighting — the same six-sided gem drawn three times, lit from the
top-left so the upper-left facets are pale and the lower-right facets are
deep. They differ ONLY in colour: the first is warm orange (#e08a5a),
the second is crimson rose-red (#d8556b), the third is steel blue
(#6ea8d8). Each gem is a bare crystal with NO metal setting, NO socket,
NO frame and NO shadow around it. Wide landscape orientation. No text, no
watermark.
```

### `ui_offer_card_hover` — do not generate

The hover state is composited from the card above by the same
distance-transform recipe as the buttons (`ui.ts`), so the two can never
drift in size or alignment.

## Weaver cards (`weaver_*_card`, 348×400)

The three characters keep the identity of the approved pixel-art cards —
same figure, same colours, same pose language — only the rendering and the
setting change.

### `weaver_hunter_card` → `References/Hunter-card-chosen.jpeg`

```
Minimal flat vector illustration, geometric simplified shapes, bold
silhouette, flat colour fills, uniform line weight, subtle paper grain. A
lean, agile hunter in sleek silver-white science-fiction powered armour
with hard-surface mechanical panelling, a pointed angular hood over a
featureless dark visor, and a flowing deep-crimson cape as the single warm
accent. Full figure crouched in a low, dynamic lunge as if about to
sprint. NOT medieval, NOT a fantasy knight. Setting: a long, straight
elevated causeway of dark volcanic stone crossing a dry lakebed under
thin, cold pre-dawn mist, broken slabs and dry golden grasses along its
edges, low terraced ruins far on the horizon. No columns, no arches, no
Greco-Roman architecture. Muted desaturated palette of deep blue-black
with pale teal highlights, dark ancient stone and luminous glowing
threads. Portrait orientation. No text, no watermark, no border.
```

### `weaver_titan_card` → `References/Titan-card-chosen.jpeg`

```
Minimal flat vector illustration, geometric simplified shapes, bold
silhouette, flat colour fills, uniform line weight, subtle paper grain. A
massive, heavyweight titan in bulky matte-black science-fiction powered
armour with hard-surface mechanical panelling and oversized shoulder
plates, a glowing ember-orange visor and thin ember-orange accent lines
across the chest and limbs as the single warm accent. Full figure standing
in a wide, planted stance with clenched fists. NOT medieval, NOT a fantasy
knight. Setting: a sunken square courtyard of dark volcanic stone under
harsh high-altitude midday light casting short, hard shadows, colossal
cracked blocks half-buried in rubble, weathered geometric carvings worn
almost smooth on the retaining walls, sparse prickly-pear cacti growing
from the cracks. No columns, no arches, no Greco-Roman architecture. Muted
desaturated palette of deep blue-black with pale teal highlights, dark
ancient stone and luminous glowing threads. Portrait orientation. No text,
no watermark, no border.
```

### `weaver_warden_card` → `References/Warden-card-chosen.jpeg`

```
Minimal flat vector illustration, geometric simplified shapes, bold
silhouette, flat colour fills, uniform line weight, subtle paper grain. A
calm sentinel warden in polished silver-white science-fiction powered
armour with hard-surface mechanical panelling, a smooth glossy black dome
helmet, a long black split cape flowing from the waist, small luminous
pale-teal lights on the chest plate and a small amber emblem as the single
warm accent. Full figure standing upright with both open palms raised in a
protective warding gesture. NOT medieval, NOT a fantasy knight. Setting:
a quiet terraced hillside of dark volcanic stone at dusk, broad low steps
descending to a still, dark pool that reflects faint pale-teal threads of
glowing light, agave-like succulents along the stone edges. No columns,
no arches, no Greco-Roman architecture. Muted desaturated
palette of deep blue-black with pale teal highlights, dark ancient stone
and luminous glowing threads. Portrait orientation. No text, no watermark,
no border.
```
