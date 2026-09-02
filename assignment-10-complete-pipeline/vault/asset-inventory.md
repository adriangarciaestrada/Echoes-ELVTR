# Asset inventory — what gets generated, and with what

Every sprite the game needs, its size, its prompt, and the parameters it is
generated under. Written before the first credit is spent: generating and hoping
is how a roster ends up looking like fifteen different games.

`art-direction.md` owns the style decisions. This file owns the list.

## The coherence strategy: one anchor, then style transfer

The API has two generation endpoints, and the difference decides whether this
roster hangs together:

| endpoint | what it does | used for |
|---|---|---|
| `generate-image-pixflux` | text to sprite, no style reference | **the anchor only** |
| `generate-image-bitforge` | text to sprite **with `style_image`** | everything else |

So the order is fixed:

1. Generate ~6 candidates for **one** subject with `pixflux`.
2. A person picks the one that defines the house look. That sprite is the anchor.
3. Every remaining subject is generated with `bitforge`, passing the anchor as
   `style_image` at `style_strength` 55 `[TUNE]`.

The anchor is `construct_node` — a one-cell object, simple enough that the
choice is about outline, shading and palette rather than about subject matter.
It is the cheapest possible thing to get right, and everything inherits it.

Rejecting the anchor costs six generations. Rejecting the roster after
generating it blind costs forty-five.

## Global parameters

Fixed for every request, so the only variable between subjects is the subject.

| field | value | why |
|---|---|---|
| `no_background` | `true` | the board is dark; a framed sprite has no silhouette |
| `color_image` | the game's palette PNG | parsed from `theme.ts`, so it cannot drift |
| `outline` | `selective outline` | a black outline disappears against `#0b0d12` |
| `shading` | `basic shading` | anything more is mud at 16-32px |
| `detail` | `low detail` | same reason |
| `view` | `side` for relics, `high top-down` for enemies | relics are inventory objects; enemies are seen from above walking the lane |
| `coverage_percentage` | 55 | the checks refuse below 10% and above 92% |
| `text_guidance_scale` | 8.0 | `[TUNE]` |
| `seed` | recorded per candidate | a sprite someone likes can be regenerated, not re-hunted |

`negative_description` (bitforge only): *"photorealistic, 3d render, blurry,
antialiased, drop shadow, text, watermark, frame, border, white background"*.

## Base resolution: generate 1:1 with world units

The renderer draws at the display's real pixels now, and the pixel ratio is
**rounded to a whole number** (`main.ts`), so a sprite is only ever scaled by
1×, 2× or 3×. That decides the generation size on its own:

- **Never generate at 3× and downscale.** Downsampling is the one thing pixel
  art cannot survive; it is what made this question worth asking.
- **Never generate below world size and upscale in the game.** A 16px sprite
  drawn across 32 world units is six physical pixels per art pixel at dpr 3 —
  legible, but chunky in a way this game's clean look does not ask for.

So each sprite is generated at exactly the size it occupies in world units, and
the display ratio multiplies it by a whole number afterwards with
nearest-neighbour filtering. One asset, sharp on every monitor.

| family | generated | world units | dpr 1 | dpr 2 | dpr 3 |
|---|---|---|---|---|---|
| Weaver card | 350×400 | 350×400 | 1× | 2× | 3× |
| Weaver, back view | 96×112 | 192×224 | ×2 | ×4 | ×6 |
| relic icon | 32×32 | 32×32 | 32px | 64 | 96 |
| enemy | 32×32 | 32×32 | 32px | 64 | 96 |
| boss | 64×64 | 64×64 | 64px | 128 | 192 |
| Beacon | 128×64 | 128×64 | 128×64 | 256×128 | 384×192 |

All within `bitforge`'s 200px ceiling; the anchor uses `pixflux`, which allows 400.

### What this changes in the game

`art-direction.md` specified enemies at 32-48 and bosses at 96, while the
renderer draws them at **14px** and **26px** (`CELL = 36`, `centre.ts`). The
table above resolves that in the renderer's favour and then enlarges it: enemies
go 14 → 32 world units, bosses 26 → 64.

**That is a design change riding along with the art.** Enemies become visibly
bigger, and the lane stops reading as empty. It is recorded here rather than
smuggled in with a sprite import.

## The 21 subjects

Prompts are built from the names and descriptions the copy pipeline already
approved, so a relic's icon and its text describe the same object.

### Relics — 32×32, `view: side`

| id | subject | prompt body |
|---|---|---|
| `relic_bolt_needle` | Swift Fang | a slender fang-shaped dart of pale bone, needle point, bound at the base with a single dark thread |
| `relic_bolt_long` | Rending Bolt | a long barbed harpoon bolt with a serrated head, shaft wound in frayed cord |
| `relic_bolt_heavy` | Heavy Hitter | a squat blunt slug of dark stone, banded with iron, weighted at the front |
| `relic_burst_bomb` | Shock Burst | a small round charge of cracked stone with light bleeding from the fractures |
| `relic_burst_arc` | Burning Arc | a curved brazier of blackened metal holding a low teal flame |
| `relic_burst_field` | Flame Field | a wide flat emitter plate, three vents breathing pale fire |
| `relic_construct_node` | Sentry Node | a small carved stone node with one lit eye, resting on a short base |
| `relic_construct_orbit` | Orbital Guard | a dark core encircled by three thin orbiting blades |
| `relic_construct_turret` | Focus Turret | a compact turret on a squat mount with one long focusing barrel |

### Enemies — `view: high top-down`

| id | size | prompt body |
|---|---|---|
| `enemy_walker` | 32×32 | a shambling husk of frayed grey thread and broken stone, hunched forward |
| `enemy_gunner` | 32×32 | a crouched husk bracing itself, one barbed limb raised to fire |
| `enemy_bulwark` (boss) | 64×64 | a hulking armoured husk behind a slab of fused stone, immovable |
| `enemy_splitter` (boss) | 64×64 | a bloated husk seamed with bright cracks, straining to come apart |
| `enemy_disruptor` (boss) | 64×64 | a tall spindly husk trailing severed luminous threads from its arms |

### Weavers — the asset attacks come out of

**The figure is science fiction; the setting is ancient.** That contrast is the
picture, and getting it backwards is the first thing this inventory got wrong:
a prompt built from `plate`, `helm` and the house style's `dark stone and
luminous thread` returned fantasy knights three times out of three. The world's
vocabulary belongs to the world. The Weavers are described in hard-surface
terms — powered armour, panel lines, sealed visors — and the ruins around them
carry the age.

The Weaver is not scenery. Every attack except the Constructs is fired by the
figure on screen, so it stands at the point all combat geometry is measured
from: `(0, 0)`, which the code has been calling "the Beacon". The origin does
not move — it acquires a body, and the Beacon sits behind it. Every reach in the
game keeps its measured value.

Drawn from behind, **high top-down** — the same camera as the enemies, not a
softer three-quarter angle — facing away up the lane, so the player looks past
their own Weaver at what is coming. The Remnants come down the lane towards
that figure and the Beacon behind it. And because this is the figure attacks
fire from, not a portrait, it has to be shown **gripping a weapon, raised and
aimed up the lane** — a plausible source for a shot leaving a muzzle, which a
figure with empty hands is not.

Rotating the approved card into this pose was tried first and abandoned: `/rotate`
only turns the pixels it is given, and a 3/4-view portrait carries no information
about what the character's back or a weapon in its hands would look like — it
warped the scene behind the figure instead. The fix is to generate the back view
fresh, reusing the card's own armour description as a prompt body rather than its
pixels, and to trust the `view`/`direction` fields (already sent, `generate.py`)
for the camera instead of restating the angle in the prompt text — restating it
as "slightly above" is what fought the field in the first attempts.

**The cards are the exception to every size rule in this file.** They are the
one place the player stops and looks, so the figure is the subject rather than a
readable token: **350×400**, drawn 1:1, at roughly thirteen times the pixel count
of the battlefield sprite. Each class gets its **own heroic pose**, chosen to say
what that class does — the Titan plants and pushes, the Hunter reaches down the
lane, the Warden holds ground.

The width is the existing card's, so the three read as one set. The height stops
at 400 rather than the card's full 430 because `pixflux` caps there, and the
remaining 30px strip carries the class name.

**The cards keep their background.** They are illustrations rather than tokens
laid on the board, so the world behind the figure is part of what they show, and
the checks that demand a silhouette — the coverage ceiling, the opaque-border
test — do not apply to them. Everything that goes on the board is still cut out,
because a sprite without a silhouette is a rectangle.

**At rest a card is its portrait and its name. Everything else — the loom to
scale, the geometry, the blurb, the opening relic, the ultimate — appears under
the cursor.** The card's job before you point at it is to show the character;
the numbers are what you ask for, not what you wade through to reach the art.

That size forces a different endpoint, and the trade is worth naming:
`bitforge` carries `style_image` but stops at 200px, so the cards use `pixflux`
and cannot inherit the anchor that way. They use `init_image` instead — the
approved Titan card seeds the other two at low strength `[TUNE]`, enough to
carry palette and treatment without copying the pose, which has to differ.

| id | size | prompt body |
|---|---|---|
| `weaver_titan_card` | 348×400 | a soldier in heavy futuristic powered exo-armour, angular segmented tech plating with panel lines and greebles, thick asymmetric shoulder pauldrons, a sealed helmet with a flat glowing visor and no face, glowing orange-red energy strips inset into the chest plate, forearms, thighs and shins, matte black composite armour, planted wide with both fists driven down into the ground, arms flexed out away from the body |
| `weaver_hunter_card` | 348×400 | a scout in light futuristic powered armour, streamlined low-profile plating, a sealed helmet with a narrow glowing visor, a long dark technical cape, energy strips along the forearms, caught mid-stride and low with one arm extended far ahead releasing a bright filament |
| `weaver_warden_card` | 348×400 | an operator in heavy futuristic powered armour, layered slab plating and reinforced greaves, a sealed helmet with a wide glowing visor, braced on one knee behind a projected energy barrier held up on one arm, head lifted |
| `weaver_hunter_back` | 96×112 | the same scout in light futuristic powered armour, streamlined low-profile plating, back of the sealed helmet with a narrow glowing visor strip, a long dark technical cape, energy strips along the backs of the forearms, gripping a long sci-fi weapon raised and aimed up the lane, crouched low stance |
| `weaver_titan_back` | 96×112 | the same soldier in heavy futuristic powered exo-armour, angular segmented tech plating with panel lines and greebles, thick asymmetric shoulder pauldrons, back of the sealed helmet, glowing orange-red energy strips down the spine and backs of the forearms, matte black composite armour, gripping a heavy sci-fi weapon raised and aimed up the lane, braced two-handed stance |
| `weaver_warden_back` | 96×112 | the same operator in heavy futuristic powered armour, layered slab plating and reinforced greaves, back of the sealed helmet with a wide glowing visor strip, gripping a sci-fi weapon raised and aimed up the lane, braced wide stance |

### The Beacon — 128×64, `view: side`

Not masonry. An **ancient alien artefact**: geometry that does not read as human
building, older than the ruins standing around it.

    an ancient alien artefact of dark angular geometry, half-buried and tilted,
    carved channels running with luminous teal light, surfaces pitted with age,
    plainly not built by the people whose ruins surround it

### The battlefield — `battlefield`, 220×232 drawn at 2×

Carried over from Echoes. Open ground ringed by **ancient ruins**, marked by the
fighting that has already happened there: weathered pillars, collapsed stone,
scoring and craters. It is the same world the character cards stand in, which is
why their prompt describes it too — the card and the lane should read as one
place.

    open stone ground ringed by ancient ruined pillars and collapsed walls,
    cracked and scorched by battle, rubble scattered across the edges, dark
    and atmospheric, seen from above

**Not generated yet.** Characters first.

## What is NOT generated, and why

As important as the list above. Each of these was considered and refused.

- **Shot shapes** (the Burst cone, the orbiter's ring, the pierce line, the
  ultimate's disc). They are geometry derived from `range` and `spread` at
  runtime — a sprite cannot widen with a relic's tier. They stay primitives.
- **Tier colour.** It is the cell background and never the sprite
  (`art-direction.md`). A sprite that paints itself purple fights the cell it
  sits on, and the five-step ramp would need five versions of every icon.
- **Cell frames, tray, panels, bars.** UI chrome that must scale with layout.
- **Buff icons.** Eleven more subjects for text that already reads fine, and
  the arsenal groups by category rather than by icon.
- **Enemy health pips.** Three pixels of state; a sprite would be worse.

## Budget

| stage | generations | note |
|---|---|---|
| anchor | 6 | `pixflux`, one subject, human pick |
| roster | 21 × 3 = 63 | `bitforge` with the anchor as `style_image` |
| reserve | ~12 | subjects that fail the checks and need a second pass |
| **total** | **~81** | |

The two Weaver families are drawn at 2× their generated size, which is why they
are generated at 150×200 and 96×112 rather than at their on-screen size: 300×400
is past `bitforge`'s 200px ceiling, and 2× is still an integer scale.

The deterministic checks run before a person sees anything, so the reserve is
spent on subjects that measurably failed rather than on ones that looked wrong.
