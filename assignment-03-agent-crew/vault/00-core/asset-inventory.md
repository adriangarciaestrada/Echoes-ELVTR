# Detailed Asset Inventory & Sourcing Specification — Echoes (Vertical Slice)

> **Research & Sourcing Document for Asset Scout (`agents/11-asset-scout.md`)**  
> This document contains the full inventory, volume metrics, art direction constraints, and exhaustive technical specifications for each of the **27 asset requests** (34 entry specifications) required for the *Echoes* 2.5D Sci-Fi Metroidvania vertical slice.

---

## 1. Executive Inventory Summary

### Total Asset Requests: **27 Asset IDs**

| Category | P0 Entries (Required) | P1 Entries (Stretch) | Total Specifications | Total Unit / Instance Count |
| :--- | :---: | :---: | :---: | :---: |
| **Player Characters** | 1 (Hunter) | 1 (Titan) | 2 | 2 |
| **Weapons** | 2 (Hand Cannon, Grapple Knife) | 1 (Auto Rifle) | 3 | 3 |
| **Enemies** | 3 (Crawler, Ledge Gunner, Shieldbearer) | 2 (Walking Bomb, Blink Tank) | 5 | 5 |
| **Bosses** | 2 (La Costurera, Revived Knights) | 0 | 2 | 3 (1 Witch + 2 Knights) |
| **Environment (Modular)** | 2 (Modular Kit, Boss Arena) | 0 | 2 | 2 Kits / Sets |
| **Interactive & Lore Props** | 4 (Anchor, Door, Boss Door, Beacon) | 2 (Bash Wall, Lore Nodes) | 6 | 8+ |
| **Visual Effects (VFX)** | 5 (Weave, Revive, Combat, Ability, Boss) | 2 (Blink, Beacon VFX) | 7 | 7 Packs / Systems |
| **Audio (Music / SFX)** | 3 (Music, Combat SFX, Movement SFX) | 1 (UI/Boss SFX) | 4 | 4 Packs |
| **UI & Materials** | 1 (Sci-fi Font) | 2 (HUD Kit, Master Material) | 3 | 3 Sets |
| **TOTALS** | **23 P0 Entries** | **10 P1 Entries** | **33 Configs / 27 IDs** | **37+ Individual Assets** |

---

## 2. Demand Timeline / Release Phases (R1 - R5)

- **Phase R1 (21–27 Jul):** Greybox & Movement (No external assets).
- **Phase R2 (28 Jul – 3 Aug):** Player Character Models (`char-hunter`, `char-titan`).
- **Phase R3 (4–10 Aug):** PEAK ASSET DEMAND (Enemies, Weapons, Environment Kit, Combat VFX, Props).
- **Phase R4 (11–17 Aug):** Main Boss (`boss-la-costurera`), `boss-revived-knights` & Boss Chamber.
- **Phase R5 (18–24 Aug):** Audio (Music/SFX) & UI Polish.

---

## 3. Global Selection Rules & Constraints for Asset Scout

> **2.5D Side-Scroller Perspective (Metroid Dread Style):** Assets are always viewed in profile (X/Z plane) at a camera distance of ~900 units. **Side-view silhouette legibility is the single most important selection criterion.**

1. **Art Direction:** Space fantasy. Clean hard-surface armor combined with fabric accents (hoods/capes); mystic technology rendered as geometry and light (not unshaped particle soup).
2. **IP Safety (Legally Distinct):** Destiny-adjacent tone but 100% legally clean. No recognizable names, logos, or 1:1 designs from existing IP. Subtle homage is fine; direct copies are rejected.
3. **License:** Must permit non-commercial course use. Prefer licenses that also allow later commercial (Steam) release (CC0, CC-BY, Fab Standard License, Unreal Engine Sponsored Content, etc.).
4. **Technical Standards:**
   - **Characters / Bosses:** $\le$ 50,000 tris, game-ready rig, PBR texture maps (Albedo, Normal, Roughness/Metallic).
   - **Props / Minor Enemies:** $\le$ 10,000 – 15,000 tris.
   - **Humanoid Rig:** UE5 skeleton compatible (Manny/Quinn) or Mixamo auto-riggable.
   - **Audio:** Royalty-free, WAV (44.1kHz/16-bit) or OGG, clean seamless loops.

---

## 4. Exhaustive Technical Specifications per Asset (27 IDs)

### 4.1. Player Characters

#### 1. `char-hunter` — Hunter (Agile Class)
- **Category:** Player Character | **Priority:** P0 | **Phase:** R2 (28 Jul – 3 Aug) | **Quantity:** 1
- **Visual Description:** Lean, high-mobility silhouette. Wears an optional tattered hood/cloak and sleek sci-fi light armor. Reads instantly as "the fast, agile gunslinger" from the side.
- **Technical Specs:** $\le 50k$ tris. Rigged humanoid, UE5-skeleton compatible or Mixamo-riggable. PBR 2K/4K textures. Required sockets: `weapon_r` (hand cannon right hand), `grapple_socket` (wrist/waist for tether).
- **Search Keywords:** `sci-fi hunter character rigged`, `hooded agile ranger UE5`, `space fantasy rogue character game ready`, `cyberpunk assassin rigged`
- **Acceptance Criteria:** Crisp side-readable silhouette distinct from Titan; clean A/T-pose; functional cloth physics on cape/hood if present.
- **IP Safety:** Silhouette evokes a hooded space gunslinger; must not copy any specific character design from Destiny or Star Wars.

#### 2. `char-titan` — Titan (Heavyweight Class)
- **Category:** Player Character | **Priority:** P1 | **Phase:** R2 (28 Jul – 3 Aug) | **Quantity:** 1
- **Visual Description:** Bulky, heavy hard-surface powered armor, broad shoulders, grounded stance. Silhouette reads as "the tank" in profile — wide, heavy, industrial.
- **Technical Specs:** $\le 50k$ tris. Rigged humanoid, UE5-skeleton compatible or Mixamo-riggable. PBR textures. Sockets: `weapon_r` (auto rifle), `shield_attach` (left forearm for energy shield).
- **Search Keywords:** `sci-fi heavy armored soldier rigged`, `space fantasy juggernaut character UE5`, `bulky powered armor character game ready`, `futuristic mech warrior rigged`
- **Acceptance Criteria:** Strong mass contrast vs Hunter; wide footprint; tested with charge-bash animations.
- **IP Safety:** Standard heavy powered armor archetype; keep plate shapes distinct.

---

### 4.2. Weapons

#### 3. `weapon-hand-cannon` — Hand Cannon (Hunter Primary)
- **Category:** Weapon | **Priority:** P0 | **Phase:** R3 (4–10 Aug) | **Quantity:** 1
- **Visual Description:** Semi-automatic sci-fi heavy revolver-pistol. Hard-surface, chunky, high-precision feel. Reads from the side as a single crisp silhouette in the Hunter's hand.
- **Technical Specs:** $\le 8k$ tris. Separate mesh with grip pivot. Sockets: `MuzzleFlashSocket`. PBR 2K textures.
- **Search Keywords:** `sci-fi hand cannon`, `futuristic revolver pistol`, `space western revolver 3d model`, `hard surface sidearm game ready`
- **Acceptance Criteria:** Side-readable profile at 900 units camera distance; detached mesh.
- **IP Safety:** Avoid replicating iconic named weapons like *Fatebringer* or *Thorn*.

#### 4. `weapon-auto-rifle` — Auto Rifle (Titan Primary)
- **Category:** Weapon | **Priority:** P1 | **Phase:** R3 (4–10 Aug) | **Quantity:** 1
- **Visual Description:** Automatic sustained-fire sci-fi rifle. Heavier and longer than the hand cannon; suppression weapon. Hard-surface, industrial.
- **Technical Specs:** $\le 10k$ tris. Separate mesh. Sockets: `MuzzleFlashSocket`, `EjectSocket`. PBR textures.
- **Search Keywords:** `sci-fi assault rifle`, `futuristic auto rifle`, `hard surface rifle game ready`, `heavy pulse rifle 3d`
- **Acceptance Criteria:** Reads cleanly in Titan's two-handed grip.

#### 5. `weapon-grapple-knife` — Grapple Chain Knife (Hunter Traversal)
- **Category:** Weapon / Traversal Prop | **Priority:** P0 | **Phase:** R3 (4–10 Aug) | **Quantity:** 1
- **Visual Description:** A throwing knife tethered by a chain or energy cord, used as a grappling traversal tool that anchors to ceiling/wall points.
- **Technical Specs:** Blade mesh ($\le 3k$ tris) + tileable/stretchable chain segment or cable for cable component attachment in UE5.
- **Search Keywords:** `grappling hook chain`, `kunai chain weapon`, `grapple knife 3d prop`, `sci-fi tether blade`
- **Acceptance Criteria:** Detachable blade mesh to project anchor point visually.

---

### 4.3. Regular Enemies

#### 6. `enemy-crawler` — Crawler (Melee Swarm)
- **Category:** Enemy | **Priority:** P0 | **Phase:** R3 (4–10 Aug) | **Quantity:** 1 Mesh / Multiple Instances
- **Visual Description:** Small, fast pursuer that follows floors, walls, and ceilings. Insectoid or skittering-robotic. Low HP swarm unit providing room friction.
- **Technical Specs:** Rigged for fast locomotion. $\le 15k$ tris. Animations: Idle, Run, Attack, Death.
- **Search Keywords:** `sci-fi crawler drone`, `robotic spider enemy rigged`, `small alien swarm creature`, `wall crawler enemy 3d`
- **Acceptance Criteria:** Fluid run animation; easily aligns to sloped geometry.

#### 7. `enemy-ledge-gunner` — Ledge Gunner (Elevated Shooter)
- **Category:** Enemy | **Priority:** P0 | **Phase:** R3 (4–10 Aug) | **Quantity:** 1
- **Visual Description:** Stationary or platform-bound ranged shooter fixed to ledges and alcoves. Fires line-of-sight energy projectiles at intervals. Turret-like or gunner silhouette.
- **Technical Specs:** $\le 15k$ tris. Articulated mesh with aim/fire animation and `MuzzleSocket`.
- **Search Keywords:** `sci-fi turret enemy`, `alien ranged gunner rigged`, `energy sentry robot`, `wall mounted gun enemy`
- **Acceptance Criteria:** Clear telegraph wind-up animation; distinct muzzle point in 2.5D profile.

#### 8. `enemy-shieldbearer` — Shieldbearer (Chokepoint Wall)
- **Category:** Enemy | **Priority:** P0 | **Phase:** R3 (4–10 Aug) | **Quantity:** 1
- **Visual Description:** Heavy humanoid carrying a full-height frontal energy/physical shield plus knockback melee. A moving wall the player solves by going over (Hunter) or through (Titan).
- **Technical Specs:** Heavy humanoid rig + separate shield mesh ($\le 20k$ tris total) to support energy VFX attachment.
- **Search Keywords:** `sci-fi shield bearer enemy`, `energy shield soldier rigged`, `riot shield alien 3d`, `phalanx shield unit`
- **Acceptance Criteria:** Wide frontal silhouette dominated by shield; shield can fully obscure enemy body in side view.

#### 9. `enemy-walking-bomb` — Walking Bomb (Proximity Explosion)
- **Category:** Enemy | **Priority:** P1 | **Phase:** R3 (4–10 Aug) | **Quantity:** 1
- **Visual Description:** Slow, volatile ground unit that rushes when the player is near and detonates on contact or death. Needs an unstable/overcharged emissive state.
- **Technical Specs:** $\le 15k$ tris. Simple rig + exposed emissive material parameter for flashing telegraph.
- **Search Keywords:** `sci-fi suicide bomber enemy`, `explosive drone rigged`, `overloading robot enemy`, `kamikaze alien unit`
- **Acceptance Criteria:** Adjustable emissive pulse via material parameters.

#### 10. `enemy-blink-tank` — Blink Tank (Teleport Heavy)
- **Category:** Enemy | **Priority:** P1 | **Phase:** R3 (4–10 Aug) | **Quantity:** 1
- **Visual Description:** High-HP heavy that takes initial damage then teleports behind the player to strike. Slow, imposing bruiser silhouette.
- **Technical Specs:** $\le 25k$ tris. Bruiser rig + heavy melee swing and vanish/reappear animations.
- **Search Keywords:** `sci-fi heavy brute enemy`, `teleporting alien warrior rigged`, `armored melee bruiser`, `phase-shift enemy`
- **Acceptance Criteria:** Melee strike animation with clear visual weight.

---

### 4.4. Bosses

#### 11. `boss-la-costurera` — La Costurera (Main Boss — Witch)
- **Category:** Boss | **Priority:** P0 | **Phase:** R4 (11–17 Aug) | **Quantity:** 1
- **Visual Description:** Alien witch fighting at range with energy volleys and beams while guiding the revive weave of her knights. Elegant/svelte duelist with a glaive and thread motif. Tall, imposing caster silhouette.
- **Technical Specs:** $\le 60k$ tris. Full rig with flowing robes/fabric. PBR textures with intense emissive maps. Sockets for projectile cast origin and thread attachment (`weave_hand_l`, `weave_hand_r`).
- **Search Keywords:** `sci-fi alien witch boss`, `energy caster boss rigged`, `elegant duelist glaive character`, `space sorceress boss 3d`
- **Acceptance Criteria:** Majestically menacing silhouette; casting, channel, and floating locomotion animations.
- **IP Safety:** Inspired by space witch archetypes (e.g. Destiny Hive Wizard) but original ceremonial design, not dirty/organic.

#### 12. `boss-revived-knights` — Revived Knights (Boss Vanguard)
- **Category:** Boss (Vanguard) | **Priority:** P0 | **Phase:** R4 (11–17 Aug) | **Quantity:** 2 Instances (1 Shared Mesh)
- **Visual Description:** Two monumental humanoid knights in ancient sci-fi armor with greatswords, providing melee pressure. When downed, they enter a petrified state while La Costurera's threads visibly re-stitch them.
- **Technical Specs:** $\le 40k$ tris. Single optimized rig reusable at two scale factors. Melee sweep, downed, and revive-idle animations.
- **Search Keywords:** `sci-fi knight greatsword rigged`, `armored space paladin`, `monumental warrior enemy`, `heavy melee knight game ready`
- **Acceptance Criteria:** Single mesh scalable to 2 sizes; heavy combat stance; compatible with revive-weave VFX.

---

### 4.5. Environment & Arenas

#### 13. `env-modular-kit` — Architect Ruins Modular Kit
- **Category:** Environment | **Priority:** P0 | **Phase:** R3 (4–10 Aug) | **Quantity:** 1 Kit (~30–50 pieces)
- **Visual Description:** Ancient, colossal, decaying structures of stone and dark metal alloys built by a long-gone civilization (The Architects). Corridors, walls, floors, ceilings, ledges, pillars, and arches tiling cleanly on a 2.5D plane.
- **Technical Specs:** UE5 Nanite geometry. Grid snapping on X and Z axes (100u / 400u increments). Shared PBR materials / Trim Sheets for low draw calls.
- **Search Keywords:** `modular sci-fi ruins kit`, `ancient alien temple modular`, `decaying space structure environment`, `sci-fi corridor modular UE5`
- **Acceptance Criteria:** Zero visible seams when snapped on side plane; cohesive cosmic ruin art style.

#### 14. `env-boss-arena` — Boss Chamber / Arena
- **Category:** Environment | **Priority:** P0 | **Phase:** R4 (11–17 Aug) | **Quantity:** 1 Arena Mesh / Scene
- **Visual Description:** Large ceremonial/ritual chamber for the La Costurera fight. Open floor space for knight melee and witch repositioning; dramatic, ancient, sealed feeling.
- **Technical Specs:** Nanite geometry. Matches `env-modular-kit`. At least 3,000 units horizontal floor space.
- **Search Keywords:** `sci-fi boss arena`, `ancient ritual chamber environment`, `alien temple hall UE5`, `sci-fi throne room`
- **Acceptance Criteria:** Unobstructed profile camera view; clear room bounds.

---

### 4.6. Interactive & Lore Props

#### 15. `prop-grapple-anchor` — Grapple Anchor Point
- **Category:** Interactive Prop | **Priority:** P0 | **Phase:** R3 | **Quantity:** Multiple instances
- **Visual Description:** Ceiling/wall target device that glows steadily, signalling to the Hunter "grapple here".
- **Technical Specs:** $\le 3k$ tris. High-contrast emissive material.
- **Search Keywords:** `sci-fi grapple point`, `wall anchor prop glowing`, `hook target device 3d`

#### 16. `prop-bash-wall` — Destructible Wall (Titan Bash)
- **Category:** Interactive Prop | **Priority:** P1 | **Phase:** R3 | **Quantity:** 2 Instances
- **Visual Description:** Cracked, reinforced ruin wall that Titan breaks with Charge Bash. Needs intact state and fractured/debris state.
- **Technical Specs:** $\le 8k$ tris. Chaos Physics ready in UE5.
- **Search Keywords:** `destructible wall sci-fi`, `cracked breakable wall prop`, `chunk fracture wall UE5`

#### 17. `prop-keycard-door` — Keycard Door + Pickup
- **Category:** Interactive Prop | **Priority:** P0 | **Phase:** R3 | **Quantity:** 2 Doors + 2 Pickups
- **Visual Description:** Sliding sci-fi door with access terminal + floating holographic keycard pickup prop.
- **Technical Specs:** Door mesh with open/close animation or slide bones. Pickup with spin movement.
- **Search Keywords:** `sci-fi door animated`, `keycard access door`, `futuristic sliding door UE5`, `keycard pickup prop`

#### 18. `prop-boss-door` — Boss Door
- **Category:** Interactive Prop | **Priority:** P0 | **Phase:** R4 | **Quantity:** 1 Major Door
- **Visual Description:** Large, imposing sealed door preceding the boss chamber. Ceremonial, ancient, clearly a point of no return.
- **Technical Specs:** Large scale mesh with opening animation sequence.
- **Search Keywords:** `sci-fi vault door large`, `ancient sealed gate`, `boss door prop UE5`

#### 19. `prop-beacon` — Beacon (Checkpoint / Respawn Anchor)
- **Category:** Interactive Prop | **Priority:** P0 | **Phase:** R3 | **Quantity:** Multiple instances
- **Visual Description:** Architect shrine/pillar device that emits warm, safe light. Fully restores health and anchors respawn point.
- **Technical Specs:** $\le 10k$ tris. Emissive material with idle pulse and activation burst state.
- **Search Keywords:** `sci-fi checkpoint shrine`, `glowing save point device`, `energy pillar prop emissive`

#### 20. `prop-lore-nodes` — Lore Props (Murals, Terminals, Fragments)
- **Category:** Lore Prop | **Priority:** P1 | **Phase:** R3 | **Quantity:** 3 Variants
- **Visual Description:** Carved stone murals, sci-fi data terminals with screens, and small collectible data fragment nodes.
- **Technical Specs:** $\le 5k$ tris each. Emissive terminal screens.
- **Search Keywords:** `sci-fi wall console terminal`, `ancient carved relief wall`, `hologram data node collectible`

---

### 4.7. Visual Effects — VFX (Niagara / Materials)

#### 21. `vfx-weave` — The Weave / Luminous Threads
- **Category:** VFX | **Priority:** P0 | **Phase:** R4 | **Quantity:** 1 Master Package
- **Visual Description:** Signature energy effect: luminous threads and geometric light ribbons (NOT unshaped smoke).
- **Technical Specs:** Niagara particle system. Exposed color parameters.
- **Search Keywords:** `niagara energy threads`, `magic light strands VFX`, `geometric energy ribbons UE5`, `arcane thread effect`

#### 22. `vfx-revive-weave` — Knight Revive Weave
- **Category:** VFX | **Priority:** P0 | **Phase:** R4 | **Quantity:** 1 System
- **Visual Description:** Thread effect that visibly re-stitches a downed knight's body over 8–12 seconds, serving as the fight's timer telegraph.
- **Technical Specs:** Progress parameter ($0.0 \to 1.0$) driven via Blueprint.
- **Search Keywords:** `reconstruction VFX niagara`, `body reassemble energy effect`, `weaving light heal effect`

#### 23. `vfx-combat-set` — Combat VFX Set
- **Category:** VFX | **Priority:** P0 | **Phase:** R3 | **Quantity:** 1 Pack
- **Visual Description:** Muzzle flashes, energy projectile traces, impact hits for hand cannon/auto rifle, and Walking Bomb explosion.
- **Technical Specs:** Niagara systems optimized for low latency.
- **Search Keywords:** `sci-fi weapon VFX pack niagara`, `energy projectile muzzle impact`, `explosion VFX UE5 stylized`

#### 24. `vfx-ability-set` — Ability & Traversal VFX
- **Category:** VFX | **Priority:** P0 | **Phase:** R3 | **Quantity:** 1 Pack
- **Visual Description:** Grapple chain trail, Titan charge-bash impact, Hunter dodge i-frame flash, energy shield, and ground pulse.
- **Technical Specs:** Attachable to sockets and character materials.
- **Search Keywords:** `sci-fi ability VFX pack`, `energy shield niagara`, `dash trail effect`, `ground pulse AoE VFX`

#### 25. `vfx-blink` — Blink / Teleport VFX
- **Category:** VFX | **Priority:** P1 | **Phase:** R3 | **Quantity:** 1 System
- **Visual Description:** Short phase-shift flash for Blink Tank and La Costurera teleportation.
- **Search Keywords:** `teleport VFX niagara`, `phase shift effect`, `blink dash energy UE5`

#### 26. `vfx-boss-attacks` — Boss Attack VFX
- **Category:** VFX | **Priority:** P0 | **Phase:** R4 | **Quantity:** 1 Pack
- **Visual Description:** Predictive energy volley patterns, floor danger telegraphs, and area-denial energy beams.
- **Search Keywords:** `sci-fi boss beam attack VFX`, `energy volley projectile pattern`, `area denial beam niagara`

#### 27. `vfx-beacon` — Checkpoint Activation VFX
- **Category:** VFX | **Priority:** P1 | **Phase:** R3 | **Quantity:** 1 System
- **Visual Description:** Idle warm glow and activation energy burst for the Beacon device.
- **Search Keywords:** `glowing checkpoint VFX`, `energy pillar idle niagara`, `save point activation effect`

---

### 4.8. Audio (Music & SFX)

#### 28. `audio-music` — Soundtrack (Exploration, Combat, Boss)
- **Category:** Audio | **Priority:** P0 | **Phase:** R5 (18–24 Aug) | **Quantity:** 3 Tracks
- **Audio Description:** Melancholic, vast sci-fi ambient bed for exploration; tension percussive layer for combat; epic orchestral/synth boss theme for La Costurera.
- **Technical Specs:** Royalty-free commercial license. WAV 24-bit / 44.1kHz. Seamless loop points.
- **Search Keywords:** `melancholic sci-fi ambient music`, `atmospheric exploration game music`, `epic boss battle theme royalty free`

#### 29. `audio-sfx-combat` — Combat & Weapon SFX
- **Category:** Audio | **Priority:** P0 | **Phase:** R5 | **Quantity:** 1 Pack (~20–40 files)
- **Audio Description:** Crisp heavy hand cannon shots, auto rifle bursts, impacts, shield hits, explosions, and enemy hurt/death sounds.
- **Search Keywords:** `sci-fi weapon SFX pack`, `energy gun sound effects`, `explosion impact SFX royalty free`

#### 30. `audio-sfx-movement` — Locomotion & Ability SFX
- **Category:** Audio | **Priority:** P0 | **Phase:** R5 | **Quantity:** 1 Pack (~15–30 files)
- **Audio Description:** Stone/metal footsteps, double jump whooshes, grapple chain whir, charge bash impact, and dodge swishes.
- **Search Keywords:** `character movement SFX pack`, `jump dash footstep sounds`, `grapple hook sound effect`

#### 31. `audio-sfx-ui-boss` — UI, Boss & Ambience SFX
- **Category:** Audio | **Priority:** P1 | **Phase:** R5 | **Quantity:** 1 Pack (~15–25 files)
- **Audio Description:** Clean UI clicks, checkpoint activation stingers, boss vocal cues, and ambient room hums.
- **Search Keywords:** `sci-fi UI SFX pack`, `magic cast sound effects`, `dark ambience loop royalty free`

---

### 4.9. UI & Unifying Materials

#### 32. `ui-hud-kit` — HUD Art Kit
- **Category:** UI | **Priority:** P1 | **Phase:** R5 | **Quantity:** 1 Kit
- **Visual Description:** Minimalist Dread-style HUD glyphs: health pips, Titan shield meter frame, interact glyphs, and keycard icon.
- **Technical Specs:** PNG vector art / 4K textures with transparency.
- **Search Keywords:** `minimalist sci-fi UI kit`, `game HUD icon pack`, `clean UI glyphs interact prompts`

#### 33. `ui-font` — Technical UI Font (Latin Extended / ES Support)
- **Category:** UI | **Priority:** P0 | **Phase:** R5 | **Quantity:** 1 Font Family
- **Visual Description:** Legible futuristic sci-fi typeface. **Mandatory full support for Spanish diacritics (á, é, í, ó, ú, ñ, ¿, ¡).**
- **Technical Specs:** TTF / OTF with open license permitting game embedding (SIL Open Font License / Google Fonts).
- **Search Keywords:** `sci-fi UI font latin extended`, `technical game font free commercial`, `clean futuristic typeface spanish accents`

#### 34. `mat-hardsurface` — Hard-Surface Master Material & Trim Sheets
- **Category:** Material | **Priority:** P1 | **Phase:** R3 | **Quantity:** 1 Master Material Set
- **Visual Description:** Master material and trim sheet set to unify marketplace assets from different creators under the project's faction color language.
- **Technical Specs:** Parameterized master material (tint, roughness offset, metallic multiplier, normal intensity, Nanite support).
- **Search Keywords:** `hard surface sci-fi material pack`, `trim sheet sci-fi UE5`, `metal stone PBR texture set`
