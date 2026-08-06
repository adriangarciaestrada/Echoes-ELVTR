# Game Design Document — Vertical Slice (7-Week Build)

**Project:** *Echoes* (working title for the slice, chosen Jul 17 — short and spoiler-safe; the full-vision game's final title may differ, see placeholder register §1.3)
**Engine:** Unreal Engine 5 (Blueprints-first, Linux/Nobara)
**Perspective:** 2.5D side-scroller (3D models on a lateral plane, *Metroid Dread* style)
**Deliverable:** Playable build, August 25, 2026
**Parent document:** Full-vision GDD (`GDD.md`) — this document is a deliberate vertical slice of it.

> **Pitch.** A short 2.5D sci-fi metroidvania that runs *Metroid Dread*'s loop with a Destiny-style class kit.
> **One map, two games:** a Hunter and a Titan traverse the same world through different verbs, class-exclusive branches — and one boss that hunts each of them differently.
> Nothing is impossible for either class — asymmetry budgets *difficulty*, never *possibility*.
> That balance promise is the hard problem of the project, and it is validated by an adversarial crew of AI agents that generates rooms and lore and playtests every build headless.
> Built in seven weeks by one human directing a virtual studio of AI agents — the production thesis, made playable.

> **Scope rule of this document:** everything here is either buildable in 7 part-time weeks or explicitly marked as a cut line. Anything not listed is out of scope for the slice (it lives in the full GDD).

---

## 1. Concept (the slice)

A short 2.5D sci-fi metroidvania slice — **one shared map, two playable classes, one adaptive boss** — designed to prove the full project's core differentiator at minimum cost:

> **"One map, two games."** The same space, traversed and fought differently depending on who you are.

The player picks one of two classes at the start — and starts **with the class kit already open** (traversal key included; ~50–70% of the full-vision kit), following the slice-design rule that a vertical slice shows the game at its most fun: no mid-run power grind — a tester sees multiple ways to move and deal damage from minute one (decided Jul 17). **Segment A** (game start → junction, tutorial included) is a **shared path** where asymmetry lives in combat texture and optional kit-gated pockets; at the **junction**, each class's gate answers only its own traversal key, splitting **Segment B** into **class-exclusive branches** that converge shortly before the boss. Both classes fight the same boss — **La Costurera** — which adapts its pressure to the class it faces (the asymmetric matchup lives *inside* one fight, §7). A complete run takes ~15–25 minutes; playing both classes is the intended full experience.

**The AI angle (production thesis):** the content that makes asymmetry affordable — route variations, encounters, environmental lore, and above all the **balance validation** of asymmetric routes and boss fights — is produced and tested by a multi-agent dev crew, not by hand.

### 1.1 Audience, platforms & positioning

**Immediate audience:** the external reviewers and playtesters who receive the build. Deliverable consequence: the build must run on *their* hardware, not just the dev machine — see the Windows packaging note below — plus the demo video (§9).

**Market audience (positioning exercise):** PC/Steam metroidvania players. Comparables: *Metroid Dread* (loop and feel reference), *Hollow Knight* (tone of exploration), *Prince of Persia: The Lost Crown* (modern 2.5D execution). Store-page hook = the pitch's line 2: **"one map, two games."** The 15–25 min run with class-swap replay is a natural fit for handheld/short-session play.

**Platforms:**
- **Linux (native) — first-class:** the dev platform (Nobara) produces native Linux builds directly; already de-risked in week 0. A rarity worth stating on any store page.
- **Windows — required for distribution:** the highest-probability platform for anyone receiving the build. UE5 does **not** support packaging Windows builds from a Linux host. Mitigation: the dev machine dual-boots Windows — install UE5 on the Windows side and package there. **Owner: the developer** (their own dual-boot machine). **First Windows package + non-dev-hardware verification: week 5** (never for the first time in ship week; date confirmed Jul 17 against the rebalanced calendar, §9 — both the Linux and the (patched) engine side are already confirmed stable, so week 5 is packaging risk only, not engine risk); the project lives in version control, so switching sides is a reboot, not a migration.
- **Steam Deck — target-compatible by design:** gamepad-first controls (§4.3), no mouse, short sessions, native Linux build. Not a certification goal for the slice; a positioning statement.

**Input floor:** full gamepad support from week 0 (§4.3) — which is also what makes the Deck claim honest.

### 1.2 Art direction

**Target feeling: familiar to a Destiny player, legally distinct.** The space magic and the world as a whole — characters, bosses, enemies, backgrounds, props — should *feel* like they could belong in Destiny without being official: clean hard-surface armor with fabric accents, mystical technology (space magic rendered as geometry and light, not particle soup), faction-coded color language, monumental sci-fi ruins over readable silhouettes. Homages and easter eggs are **deliberate and legally safe** — managed through the style guard's approved-homage allowlist (#6); nothing crosses Destiny's protected names, marks, or trade dress.

**Enforcement reality:** with no original 3D art and no commissioned artist (§3, §9.1 — marketplace/free assets only), the direction lives entirely at the *selection and grading* level — asset choice, palette, lighting, and VFX language — encoded in the style bible (§9.1). The Asset Scout (§8) sources candidates against that register and the style guard (#6) grades them; a hard-surface master material set unifies mixed-source assets into one look.

**Regional identity (decided): a what-if Golden Age that prospered in Mexico.** The slice's region reads as Mexico to a player who knows the country — and never says so. The identity is carried by *hints, not banners*: geology and light (cenotes and karst chambers, §9.3's underground lake; warm high-altitude sunsets), vegetation reclaiming ruins, architectural traces and half-erased signage fragments in Spanish, toponymy that sounds plausible rather than labeled. **Explicitly avoided:** the loaded pre-Hispanic iconography package that announced "Mexican games" default to (pyramids, calendar motifs, feathered-serpent dressing) — the setting is a *future* Mexico remembered through its ruins, not a postcard of its past. Style-guard rule (#6): the country is never named in any shipped text, and any pre-Hispanic visual reference must be on the approved-hint allowlist (default: none). Two systems get quiet resonance from this: the EN/ES day-1 parity (§8.1) stops being mere localization — Spanish is the place's own language — and the environmental lore (#4) can let bilingual fragments *be* the strongest hint of where we are.

### 1.3 Placeholder register (Destiny-derived terms)

Working terms borrowed from Destiny while proper names are decided. They may live in internal docs, but **none may ship** — the style guard (#6) blocks them in build text. The full registry with risk tiers lives in the parent GDD (§9.2). Currently in this document: *Hunter, Titan, hand cannon, auto rifle, Lift, "Light", Golden Age* (the *Warden* and *Echo* designs and their names moved to the parent GDD's roster when the slice consolidated to a single boss — decided Jul 17). The working title (*Echoes*, decided Jul 17) names nothing that needs concealing — the earlier title (*Echoes of the Architects*) is retired along with the concern that motivated this note. The slice boss's name is settled and original: **La Costurera** (ships in Spanish in both locales, §7; no collision).

---

## 2. Core loop (*Metroid Dread* grammar, Destiny kit)

The slice does **not** invent a loop. It inherits *Metroid Dread*'s: movement-first traversal, verb-gated routing (gates answer class verbs rather than mid-run pickups — the slice front-loads the kit, §1), and tension alternating between exploration and skill-check gates. Dread's **acquire → use immediately → the world reopens** beat is deliberately deferred to the full game; the slice's version of it is identity, not acquisition — the junction opens *for who you are* (§5). Destiny provides the kit (gunplay, class verbs) and the fictional register: an **original cosmology written to be Destiny-plausible** — a story that could live in that universe without being official — with deliberate, legally-safe homages managed by the style guard's approved-homage allowlist (#6). The differentiator is that **two classes run the same loop differently**; the development challenge — and the production thesis — is **balance**: every gate passable by both classes, with asymmetric difficulty texture.

Deliberate cuts from Dread's loop (scope, not oversight): no parry/counter (the kits' defensive verbs — Hunter's i-frame dodge, Titan's shield — take its place), no stalker/EMMI zones, no open map puzzle (two segments, guided).

Bands are QA-crew assertions (#8) measured on headless runs, not aspirations. All numbers `[TUNE]`.

### 2.1 Room loop (~30 seconds): FLOW → READ → FRICTION → MARK

- **Flow** — movement is the constant reward (Dread's signature): rooms are built to be traversed fluidly with class verbs; what gets punished is *sloppy* movement, never *slow* decision-making.
- **Read** — the room's primary question is navigational: *where does my class go here?* (ledges and grapple points for Hunter, Lift shafts and cracked walls for Titan). Enemies and lore nodes register on the same read.
- **Friction** — encounters (≤1 combo, §6) interrupt flow and tax sloppy movement; combat is friction along the route, not the destination of the room.
- **Mark** — the beat closes by marking progress: the exit, a lore node (#4), a checkpoint — or mentally noting a **legibly impossible gate** for later (§2.2).

**Driver:** movement mastery + navigation legibility. **Band:** combat rooms 20–45 s; pure traversal rooms ≤20 s `[TUNE]`.

### 2.2 Segment loop (~5 minutes): explore → note gates → pressure → gate → reopen

1. **Branch recognition** (the junction): the branch is not chosen — only the gate that answers the class's traversal key opens. An identity statement, not a menu (Segment A is shared; §5).
2. **Exploration under rising pressure** — 3–6 rooms that introduce one archetype or combo, then remix it (§6 vocabulary).
3. **Noted gates (visibility rule, binds the Level Designer agent):** the junction shows **both** branch gates — the player's own opens to their key; the other stays sealed and legibly class-locked (run 2's question, planted). Segment A's optional pockets show rewards only the other class can claim; the convergence shows the other branch's exit door.
4. **Checkpoint** before the gate (rules: §2.4).
5. **Gate** — the boss arena (§7).

On death: respawn at the last checkpoint. Runs are short by design, so the retry currency is **knowledge** (boss patterns, combo answers, room reads), never grind.

**Driver:** tension alternation (exploration ↔ skill check) + gate curiosity. **Band:** segment traversal 3–6 min; boss fight 2–4 min per winning attempt `[TUNE]`.

### 2.3 Session loop (one run, 15–25 min): the other class is the "new power"

Dread's macro-loop is *area → boss → new power → world reopens*. The slice projects that arc across runs instead of compressing it into one: Segment A teaches the full kit under light friction → the exclusive branch exercises it at full stretch → La Costurera masters it against an adapting opponent (GOAP). Across runs, the arc lands **on the class system**: the second class is the "new power" — the same map reopens under a different verb set, which is "one map, two games" stated in Dread's own grammar. The run-complete screen has a single job: name what this class never saw (the other route, the other difficulty texture).

**Balance contract (the development challenge):** nothing in either loop may be class-impossible. Asymmetry budgets *difficulty*, never *possibility* — enforced by the QA crew's win-rate/TTK bands (§7).

**Driver:** "one map, two games" — playing both classes is the full experience; the session loop's exit is the other class's entry. **Band:** full run 15–25 min at the QA bots' "competent" profile; first human clears may exceed it `[TUNE]`.

### 2.4 Death & checkpoints

- **Placement (binds the Level Designer agent):** one checkpoint at the tutorial exit, one at the junction, one at the **branch convergence**, and one at the boss door. No stretch of any route may exceed 4 rooms without one `[TUNE]`. Checkpoint positions ship inside the room-spec JSON and are validated deterministically: every gate is preceded by an adjacent checkpoint, and every checkpoint is both reachable and exitable for the active class (no checkpoint stranded past a point of no return).
- **On death:** respawn at the last activated checkpoint. No penalty beyond position — collected lore nodes, the traversal unlock, and noted-gate world state persist; regular enemies between checkpoint and death respawn (friction stays alive); bosses reset fully.
- **Boss retry:** the boss-door checkpoint makes retry instant — die, door, again. Worst-case loss anywhere in the slice is ~2–3 minutes of traversal `[TUNE]`, which is what keeps the retry currency knowledge, never grind (§2.2).
- **Health economy:** touching a checkpoint heals to full (Dread convention). Regular enemies have a small chance to drop health `[TUNE]` — a deliberately Titan-serving rule: a class that *trades* needs recovery for trading to be a strategy instead of a countdown; the QA crew's asymmetry bands assume these drops exist. No ammo economy: both primaries fire freely (deliberate non-goal).
- **Skin:** checkpoints are lore-skinned as **resonance beacons** — meditation spots where the connection to nature / the universal field runs strong (decided Jul 15: **no Architect iconography or mention anywhere the player can see** — the player never learns the Architects exist; naturalist reading per full GDD §9.1) — but mechanically plain, subject to the #6 style pass. Narrative direction `[IN EXPANSION — full GDD lore, not yet detailed]`: meditating at a beacon recharges the player's vital energy ("Light" — placeholder, §1.3) — flavor only in the slice, no gameplay effect. The full GDD's diegetic respawn economy remains out of slice scope (§3).

---

## 3. What is IN / OUT (vs. full GDD)

| | IN (slice) | OUT (full vision only) |
|---|---|---|
| Classes | Hunter (P0), Titan (P0) | Warlock; supers; heavy weapons |
| World | 2 level segments + 1 boss arena + tutorial area | Aging timeline, three campaigns, shared-map persistence |
| Bosses | 1 — *La Costurera*, a GOAP-driven squad fight (witch + two knights; scripted fallback) | ~8-boss roster (incl. the Warden and the Echo), Architect hierarchy, escalation spine |
| Narrative | Environmental lore only (RAG-generated, layered) | Cosmology reveals, 4 endings, diegetic respawn economy |
| Progression | Fixed kits **open from the start** (traversal keys included; ~50–70% of the full-vision kit) — the second class *is* the progression | Unlock arcs, jump upgrades (triple jump, higher Lift, Glide→Blink), additional ability unlocks, expansions, weapon evolution |
| Meta | Class select screen; run-complete screen per class | Campaign order chronology, true final boss |

**Explicit non-goals:** no save system beyond checkpoints (run state survives death, not app exit), no difficulty settings, limited menu *polish* (a minimal functional options/pause menu — input remap, toggles, locale switch (§4.5, §8.1) — **is** in scope; the two hero flow screens — class select (§8.2) and run-complete — use marketplace UI art and typography only (no bespoke commissioned art — art scope is marketplace/free, §9.1); menu art beyond those two screens is still out — decided Jul 20, art track retired Jul 23), no original 3D art (marketplace/free assets + retargeted animations), no audio beyond stock SFX/music, no authored cutscenes (cinematic feel comes from existing systems — §9.3).

---

## 4. Classes (simplified slice kits)

Kits are cut to the minimum set that still makes each class *feel* like itself (fantasy filter from the full GDD).

### 4.1 Hunter — P0 (must ship)
| Slot | Tool | Verb |
|---|---|---|
| Jump | Double jump | Precise vertical staccato |
| Defense | Dodge with i-frames | Evasion |
| Primary | Hand cannon | Precise ranged damage |
| Traversal key (from start) | Chain knife | Grapple point traversal + light melee `[TUNE: melee damage absent from §7.1 bands until tuned]` |
| Grenade (decided Jul 17) | Sticky grenade | Adheres to a target, delayed single-target burst on cooldown — precision damage from range |

**Branch identity (Segment B):** grapple chains, high ledges, precision platforming. **Boss identity:** wins by not getting hit.

### 4.2 Titan — P0 (committed)
| Slot | Tool | Verb |
|---|---|---|
| Jump | Lift (sustained vertical push) | Reach high walls, slow float |
| Defense | Energy shield (brief) | Absorb instead of evade |
| Primary | Auto rifle | Sustained hitscan damage |
| Traversal key (from start) | Charge bash | Break cracked walls — horizontal key |
| Grenade (decided Jul 17) | Area grenade | Generates a sustained area-damage zone for a few seconds on cooldown — matches the sticky's offensive weight with area presence instead of single-target burst (redesigned Jul 17: no longer a knockback tool) |

**Branch identity (Segment B):** Lift wall climbs, bash-through walls. **Boss identity:** wins by trading and tanking windows.

**Hard rule (inherited):** each class must complete the slice using only its own kit. Asymmetry decides *which route*, never *whether you can get there*.

### 4.3 Controls & game feel (shared)

**Device policy: gamepad-first** (genre convention — the slice is designed around a controller), keyboard as a full fallback, **no mouse aiming**. Implemented with **Enhanced Input** (Input Actions + Mapping Contexts), so device support is configuration, not code; both devices work from the week-0 grey-box onward.

| Action | Gamepad (Xbox layout) | Keyboard | Class overload |
|---|---|---|---|
| Move / aim direction | Left stick | A / D (+ W / S aim) | — |
| Jump | South (A) | Space | Hunter: tap ×2 = double jump · Titan: hold = Lift |
| Defensive verb | East (B) | Left Shift | Hunter: dodge (i-frames) · Titan: shield (hold) |
| Fire primary | RT | J | Hunter: hand cannon (semi-auto) · Titan: auto rifle (hold) |
| Precision aim (hold) | LT | K (hold) | Locks position, 360° stick aim `[TUNE]` |
| Traversal key | West (X) | L | Hunter: chain knife (auto-targets nearest grapple point in the facing cone) · Titan: charge bash (directional) |
| Grenade | RB | I | Hunter: sticky (adheres to a target, delayed burst) · Titan: area (sustained damage zone) — both on a flat time-based cooldown, independent of fight state `[TUNE: cooldown length]` |
| Interact (lore, checkpoints) | North (Y) | E | — |
| Pause | Start | Esc | — |

**One motor vocabulary, two dialects:** the same button always means the same *category* of verb (jump, defend, fire, key) — switching class changes what the verb *does*, never *where it lives*. This is the control-layer expression of "one map, two games", and it is what makes the second run feel familiar in the hands while playing differently on screen.

**Game feel defaults (all `[TUNE]`, validated in the week-0 grey-box):**
- **Coyote time 120 ms** — a jump input remains valid briefly after walking off a ledge.
- **Input buffer 150 ms** — inputs pressed slightly early (jump before landing, dodge before a recovery ends) queue and fire on the first valid frame.
- **Variable jump height** — releasing jump early shortens the arc (minimum ~40% of full height).
- **Dodge:** ~400 ms total, i-frames in the ~250 ms core; cancelable into fire once i-frames end; fire is always cancelable into dodge (**defense has priority** — no animation ever traps the player).
- **Instant turnaround** — facing flips with no blocking animation; near-full air control.
- **No landing lag** on normal falls.

**Pipeline note:** all feel parameters live in a **DataTable** (the same agent→engine seam, §8): tuning is data, not recompilation, and the QA crew can sweep feel-parameter variants in headless runs.

### 4.4 HUD (minimal)

**Philosophy:** Dread-minimal — the screen belongs to the world; UI exists only where the body can't feel state. Implemented in UMG; all strings in string tables from day 1 (EN/ES localization seam).

**On screen, always:**
- **Player health** as segmented pips (top-left) — matches the hits-to-die model (§7.1: 4–6 hits) better than a continuous bar; a hit = a pip, instantly readable `[TUNE: pip count]`.
- **Titan only — shield meter:** a thin recharge bar under the pips (its one metered verb). Hunter has no meter: double jump and dodge are binary, the body feels them — no UI.

**Contextual only:**
- **Interact glyph** (Y/E) floating world-space over lore nodes and checkpoints.
- **Traversal-key prompts:** contextual button prompts on grapple points / cracked walls run during the first uses, then retire `[TUNE: prompt retirement rule]`.
- **Tutorial prompts** (§5, tutorial area) are world-space signage, not HUD overlays — they live in the level, in-fiction where possible.

**Deliberately absent:**
- **No boss health bar** (Dread/Hollow Knight convention): bosses telegraph damage through **phase states** (armor cracks, glow shifts, pattern escalation, §7). Reversible decision — if human playtests read boss fights as "am I even hurting it?", a minimal bar returns `[TUNE]`. The "fair vs. unfair" playtest that would trigger this now lands in **week 4** (§9, moved up from week 5 — decided Jul 17), so there's real calendar margin to build a bar if needed, instead of discovering the problem the same week as content freeze.
- **No minimap / map screen — explicit cut:** the slice is two guided paths where the junction, the visibility rule, and camera framings (§5.1) carry the wayfinding; a metroidvania map system (fog, icons, room reveal) is high-cost UI for a 15–25 min run. The map belongs to the full GDD, where the world is big enough to get lost in.
- No ammo counter (no ammo economy, §2.4), no score, no quest log, no damage numbers.

**Damage feedback (player):** hit-flash + i-frame blink; screen effects reserved for the last pip (low-health state) `[TUNE]`.

### 4.5 Accessibility (minimum bar)

- **Full input remapping** — free by construction: Enhanced Input mappings are data (§4.3), so a remap screen reads/writes the same asset.
- **Hold-vs-toggle option** for every sustained input (Titan Lift and shield, LT precision aim).
- **No color-only signals:** every telegraph and gate state reads through shape, animation, or audio as well as color — the style guard (#6) flags color-only signals as defects.
- **Effects toggle:** screen shake and low-health screen effects (§4.4) can be disabled.
- All text is on-screen text (no voice-over to subtitle); minimum text size verified at 1080p couch distance `[TUNE]`.

---

## 5. World structure

```
[Start] ──(Segment A: shared path — tutorial → corridors)──> [Junction: own gate answers your key; the other stays sealed]
   ──(Segment B: class-exclusive branch)──> [Convergence checkpoint] ──> [Boss arena: La Costurera] ──> [Run complete]
```

- **Segment A (start → junction): one shared route for both classes.** Opens with the **tutorial area** (the full kit taught in safe rooms, then tested under light friction — the kit is open from minute one (§1), so the tutorial teaches more verbs than a drip-feed slice would; contextual prompts (§4.4) and pocket design carry the residual teaching), then Metroid-style corridors and areas. Asymmetry here is *texture, not routing*: encounter combos that press each class differently (§6) plus **optional kit-gated pockets** — a ledge only the Hunter's grapple anchor reaches, a chamber only the Titan's charge bash opens — visible to both, claimable by one (lore/health caches, 2–3 total `[TUNE]`). Neither class out-jumps the other (Lift matches the double jump), so exclusivity comes from where anchors and cracked walls are placed, never from raw reach.
- **The junction (the identity beat):** Segment A ends in the junction chamber, where both class branch gates sit visible. The player's own gate **reads their traversal key and opens**; the other stays sealed and legibly class-locked — run 2's question, planted (visibility rule, §2.2).
- **Segment B (junction → boss): class-exclusive branches.** Each branch is built around its class's full kit (Hunter: grapple chains, precision platforming; Titan: bash walls, Lift climbs) and seasoned with its punisher archetypes (§6). Branches **converge shortly before the boss** at the convergence checkpoint — where the *other* branch's exit door is visible **and obviously sealed to the wrong class** (reads the class key just like the junction gates, §2.2 — decided Jul 17: locked, not just closed, so the tease can't become a softlock): the replay seed planted at the moment of maximum curiosity, safely.
- **Backtrack budget (binds the Level Designer agent):** the slice has **no mandatory backtracks**. Any backtrack added later must obey the Dread rule: it comes with a new verb or collapses behind a shortcut. Re-traversal is power fantasy, never repetition.
- Segments are assembled from **agent-generated room specs** (JSON → UE5 DataTables): a Level Designer agent proposes room layouts and encounter placements per route; a human pass curates and assembles them in-engine.
- Target size: Segment A = 5–7 rooms + tutorial area + junction; Segment B = 3–5 rooms per branch + convergence `[TUNE]`. Dense over large.

### 5.1 Camera (2.5D)

**Base rig:** side-on perspective camera (not orthographic — parallax depth is what sells 2.5D) at a fixed lateral distance `[TUNE: ~900 units, FOV ~35°]`, implemented as a single CameraRig Blueprint (*Project Lux* as reference architecture, week 0). **No manual camera control** — no right-stick look, no zoom input (Dread convention: the camera is the designer's voice, not the player's).

**Follow behavior (all `[TUNE]`):**
- **Horizontal lookahead:** the camera leads the facing direction by ~15% of screen width — the player sees where they are going, not where they have been.
- **Vertical dead zone:** ~25% of screen height; jumps inside it do not move the camera (no jitter), sustained ascent/descent (Lift climbs, shaft drops) catches up elastically.
- **Never snap:** all camera motion is interpolated; door transitions blend (below), never hard-cut.

**Room framing (pipeline-integrated):** every room-spec JSON carries its **camera bounds**; the camera is clamped to them so the frame never shows out-of-room void. Door transitions blend over 0.3–0.5 s. Deterministic validation: a room's camera bounds must contain its full walkable extent (no room can let the player walk out of frame); the QA crew asserts "player in frame" across headless runs.

**Authored framings (the camera serves the visibility rule, §2.2):**
- **Junction chamber:** slight pull-back so **both branch gates share the frame** — one answering the player's key, the other legibly class-locked; the rule pays off only if the player cannot miss it.
- **Convergence checkpoint:** framing includes the other branch's exit door, staged to read as obviously locked — the incentive, never a temptation to wander into a kit-mismatched room.
- **Boss arena:** fixed wide shot (the full arena — including the revive weave, §7 — readable at all times; no follow-cam surprises mid-pattern).
- **Precision aim (LT):** optional slight zoom-out while held `[TUNE: cut if it fights readability]`.

---

## 6. Regular enemies (the encounter palette)

**Selection principle:** the palette is chosen to fit the level grammar of the slice — *Metroid Dread*-style dense, interconnected rooms: corridors with chokepoints, vertical shafts, platform ledges, and **short default sightlines**. Every palette enemy must work in that grammar by default. Archetypes that demand bespoke room shapes (long sniper lanes, wide open arenas, persistent area denial) are excluded from the slice rather than allowed to constrain the Level Designer agent.

**Design rule:** memorable encounters are **combos, not archetypes**. The archetypes below are a fixed palette with combination rules; the Encounter Designer agent composes encounters from this palette and never invents new enemy types. All names are mechanical placeholders (style-guard rule applies).

| # | Archetype | Weight (TTK tier, §7.1) | Skill check it enforces | Matchup texture | Priority |
|---|---|---|---|---|---|
| 1 | **Crawler** — cheap melee chaser that follows surfaces (floor, walls, ceiling); short telegraphed pounce `[TUNE]` | Fodder (≤1.5 s) | Spacing and rhythm in tight spaces; dodging *through* a lunge | Neutral; exists to combo with everything; native to Dread-style verticality | P0 |
| 2 | **Ledge Gunner** — holds an elevated platform, fires angled bursts with clear windows | Standard (2–4 s) | Using platforms and elevation as cover; exchange windows | Neutral; the **TTK calibration enemy** — all damage bands tune against it first | P0 |
| 3 | **Shieldbearer** — frontal block + knockback bash, holds a chokepoint | Standard (2–4 s once solved) | Positioning; solving an obstacle with your kit | Hunter hops it (double jump). Titan pre-unlock goes over **slow** (Lift, trading a hit); post-unlock breaks *through* (bash) — the same obstacle gets easier as you grow. "One map, two games" in a single enemy | P0 |
| 4 | **Walking Bomb** — slow shambler, proximity detonation; chokepoints amplify it | Fodder (≤1.5 s) | Range discipline in corridors | Punishes Titan (slow, close-range kit); trivial for Hunter | P1 |
| 5 | **Blink Tank** — teleports across the room, sustained tracking fire | Heavy (5–8 s) | Sustained evasion under pressure | Punishes Hunter (dense rooms shrink dodge space; tracking fire outlasts i-frames); Titan trades through it with shield windows | P1 |

The **weight tiers are the enemy vocabulary's scale**: Fodder → Standard → Heavy → Elite → Boss. There is no miniboss or Elite tier in the slice. The boss echoes the palette **by lesson, not by body** (§7): La Costurera's knights scale the Crawler's spacing lesson into sustained melee pressure, and her ranged volleys scale the Ledge Gunner's cover lesson — foreshadowing through minions, the Dread way. The dual-kill window itself has no pre-boss minion rehearsal in the slice (see below).

- **The P1 pair is a mirrored set** (Walking Bomb punishes Titan, Blink Tank punishes Hunter): it ships together or not at all — half of it would skew one class's difficulty curve.
- **Splitter — cut from the slice** (decided Jul 17): the duplicates-when-left-alive archetype that would have rehearsed the boss's dual-kill window. Not vital — the fight teaches its own mechanic without a pre-boss dress rehearsal — and it returns in the full GDD's larger roster, where dense-room floor-space is less of a hard constraint on its exponential duplication.
- **Foreshadowing stretch (pre-prioritized; never ship-blocking):** two boss-lesson trainers may enter *in this build order* only if the schedule allows after the Aug 4 decision: (1) **Ledge Gunner arc-fire variant** — lobbed shots when the target holds cover, rehearsing La Costurera's ranged volleys; (2) **Tracer Drone** — a Titan-branch laser lane rehearsing her beam patterns (sphere + beam, Crawler-cost). (The Wavecaster trainer retired with the Warden — it returns with him in the full GDD.) The boss remains fully beatable and the §7.1 bands remain valid **without any of them** — they are learning-curve polish, cut freely and silently.

**Canonical combos (the Encounter Designer's starting vocabulary):**
1. Crawler + Ledge Gunner — crawlers deny the floor while the gunner holds the high ground.
2. Walking Bomb + Ledge Gunner — the gunner holds you at the range where bombs close in.
3. Shieldbearer pushing toward Crawlers — knockback turns positioning into the threat.

*(P1-pair combos enter the vocabulary only after the Aug 4 cut decision.)*

**Encounter Designer contract (crew #3):** input = this palette + combo list + per-room budget (max 2 archetypes **and 2–5 total enemies per combat room, 0–1 in traversal rooms** `[TUNE]` — Dread-observational density; combat is friction, not a horde), ≥1 canonical combo per route, P0-only until the Aug 4 cut decision; output = encounter placements inside room-spec JSON. Deterministic placement checks at the JSON validation step: enemy counts within budget, every Shieldbearer placement leaves an over-*or*-through solution for the active class (no softlock by chokepoint), and beacon/vista checkpoint rooms carry **zero enemies** (natural spaces are safe ground — §9.3, full GDD §9.1). **Branch-sealing check (decided Jul 20, closes the reachability-validator gap):** the Level-crew Reviewer must prove not only that each class's own gates are reachable, but that the *other* class's sealed branch is **provably unreachable** by this class's traversal tool — no grapple anchor lets a Hunter latch past the Titan gate, no bash launch-arc lets a Titan overshoot into the Hunter branch. A reachability proof is not an un-reachability proof; both are required, or the "visibly sealed" junction gate is decorative and a wrong-branch softlock slips through. The QA crew (#8) reports TTK per archetype against the Ledge Gunner baseline.

**Out of slice scope (full GDD only):** Rail Sniper (demands bespoke long-lane rooms that fight the dense-room grammar) and area-denial controller (oppressive in small rooms; punishes the same class as the Walking Bomb, mirrors nothing).

**Production note:** humanoid archetypes share one base rig with material/scale swaps and at most one custom projectile each; the Crawler is a simple non-humanoid mesh on spline movement; the Blink Tank is the base rig + teleport VFX. No unique skeletons.

---

## 7. The boss (the showcase of asymmetry)

One boss, built as a **squad** (decided Jul 17; the Warden and the Echo move to the full GDD's roster): **La Costurera** — an alien witch who commands two revived knights. Design lineage: Dûl Incaru, *The Shattered Throne* (analysis in `research/destiny-boss-analysis.md`). The name is settled, original, and ships **in Spanish in both locales** — the regional identity (§1.2) moved to the front of the stage; subject to the #6 style pass like everything else.

- **Composition & the rule of the fight:** La Costurera (a tall sleek caster at **1.5–2× player height**, fighting from mid-air anchors with ranged volleys and beams) is **invulnerable while either knight stands**. Her two knights (base rig scaled **2–2.5×** + greatswords, heavy animation set) carry the melee pressure on the plane.
- **The dual-kill window (core mechanic):** when the *first* knight falls, La Costurera begins **re-stitching him** — a visible channel of luminous threads weaving the body back together. **The timer is diegetic:** the weave's progress *is* the clock (no HUD element; audio cue rises with it — and per §4.5, never color-only). The player must drop the second knight fast enough to leave time to hurt her before the weave completes. While both knights are down she is **grounded, channeling, and vulnerable** — the punish window the whole slice teaches toward. **Weave-completion rules (decided Jul 20):** knights die quickly by design and revive at **full health** — the skill is *synchronizing* the two deaths so both are down at once, never out-DPSing them; the window lasts until the first-felled knight's weave finishes, at which point he returns at full HP and the witch regains invulnerability (tighter synchronization = longer window). **Witch damage persists and accumulates across windows** — only the player's death resets it (the fight resets, the run does not), so damage is monotonic and the kill always converges: no infinite stalemate, no revive cap needed. Witch damage counts *only* inside a window (a hit landing while she is invulnerable does nothing to her). This is what makes Clearability = 100% (§7.1) true by construction rather than by tuning luck. **The class grenades (§4) are designed into this fight:** Hunter's sticky is his intended burst answer for the second knight and the punish window; Titan's sustained-zone grenade is his intended relief valve against the knights' melee pressure — tune one and you tune the other (deliberate coupling, decided Jul 17). **Grenade rules (decided Jul 17):** both grenades run on a flat time-based cooldown, independent of fight state — a knight's death does not reset it. **Pre-staging is allowed and intentional**: a Hunter who reads the fight well enough to land the sticky on the second knight before the first one even falls is banking a skilled read, not exploiting a bug — the reward for experienced play, not a defect to patch. **Guarantee:** killing the boss never requires the grenade — normal primary-weapon TTK is always sufficient by itself; the grenade only makes a good read pay off faster.
- **Fixed difficulty, QA-tuned (revised Jul 20 — cuts the Jul 17 anti-frustration valve):** the re-stitch weave's duration and the grenade cooldowns that answer it are constant across every cycle and every attempt — the fight never gets easier because a player failed it before. Two independent stress-test boards flagged the same failure mode in the cut valve from opposite angles: an escalation counter that survives (even partially) across attempts is also a counter a player can farm by dying on purpose, and a design whose only clearability guarantee is "you'll eventually get a window" rewards surviving, not improving — which quietly contradicts §2.2's own retry-currency law ("knowledge, never grind"). Clearability (§7.1 band 1) is guaranteed the honest way instead: the QA crew tunes these fixed constants against headless data, iterating before ship until every tested bot profile reliably clears within the stated attempt band — a tuning target, not a runtime safety net.
- **Full reset on death, no exceptions (closes the ambiguity both stress-test boards flagged):** dying at any point in the fight — mid-weave, mid-window, with one knight down, anything — resets La Costurera and both knights to their starting state (§2.4's "bosses reset fully" rule, made explicit here for this fight specifically: no revive progress, no stagger, no partial credit survives a death). There is nothing to gain by dying on purpose.
- **Three minds, one director (GOAP, crew #5):** the witch and each knight run their own GOAP brain over a **shared perception blackboard** (player class, distance, verb habits: dodge direction, shield uptime, air time). La Costurera acts as *director*, reweighting her knights' goals (`pincer` · `pressure` · `peel` · `guard the weave`) while running her own (`zone` · `deny` · `snipe` · `re-stitch`). The production poetry is deliberate: a multi-agent dev crew ships a boss that is itself a small multi-agent system.
- **Memorizable core, adaptive spice (decided Jul 23 — the genre-fit guardrail):** a metroidvania earns its boss fun from *learnable patterns*, so the GOAP runs **on top of** a fixed repertoire, never instead of one — it invents no new moves. **Layer 1 (the substance):** a set of telegraphed patterns — the volley, the area-denial beam, the re-stitch channel — the player memorizes like any *Dread* or *Hollow Knight* boss. **Layer 2 (GOAP, the spice):** it only decides *which* Layer-1 pattern to run, *where* to aim it, and the class-emphasis (class adaptation, below) — never the existence of an unlearnable move. The adaptation is **rule-based and consistent, not random**: the same read yields the same *telegraphed* answer — a readable tell (a weapon flash, a stance shift) a beat before the counter lands (decided Jul 17) — so the player learns her *rules* (a deeper mastery) instead of fighting noise, and beating her is a **read-and-adjust** skill check, never a mind-reading gotcha that invalidates a died-for lesson. Her memory is **bounded** — it biases her Layer-2 choices toward your revealed habit and then relaxes, so she never permanently out-solves the player, but it is never a coin-flip. The floor stays pure memorization: the scripted fallback (§9.1 cut-line 2, per-class fixed patterns) is Layer 1 alone, and ships if Layer 2 ever hurts the feel.
- **Class adaptation (the asymmetric matchup lives inside one fight):** pressure escalates by *pattern*, never by raw numbers. **Vs. Hunter**, the witch's goals sharpen — predictive shots covering the read dodge direction, area denial compressing safe ground (the anti-Hunter axis: §6's Blink Tank lesson at boss scale). **Vs. Titan**, the knights' coordination sharpens — pincer positioning and staggered swings the shield cannot cover at once (the anti-Titan axis: §6's Walking Bomb lesson at boss scale).
- **Phase reading without a health bar (§4.4):** armor cracks on the knights, fraying threads and behavioral escalation on the witch as her health drops.
- **Balance target:** both classes winnable **at parity** — win rates within ±10 points at the same bot profile `[TUNE]` — with **distinct death signatures** (§7.1: *what* kills you differs by class). Hard moments demand more skill, never more math (hard ≠ unfair, inherited rule).
- **Balance method:** win rates, TTK, and cause-of-death mix measured by the **adversarial QA crew** (headless simulated runs + structured reports), not by feel alone. Human playtests reserved for the "fair vs. unfair" perception check.
- **Stretch (never ship-blocking; only if the schedule allows after Aug 4):** a knights-only mid-map encounter — La Costurera watches from the background plane and re-stitches them as she withdraws — teaching the revive mechanic diegetically and planting her as the one who hunts you. Cut freely and silently.

### 7.1 Balance bands (QA-crew assertions)

Balance has two axes with different reference sources. **Vertical difficulty** (player vs. world) is anchored to *Metroid Dread* — observable from play, so the anchors are starting values, not gospel. **Horizontal balance** (class vs. class) has no Dread analog (one Samus, no matchups): those bands are this project's own design contract. All numbers `[TUNE]`, measured at the QA bots' "competent" profile unless noted.

**Methodology rule:** relative assertions (class A vs. class B against the *same* bot profile) are the trustworthy ones — bots differ from humans, but the delta between classes survives that gap. Absolute human difficulty is checked only in human playtests (fair-vs-unfair, above).

**Vertical anchors (from Dread, observational):**

| Metric | Band `[TUNE]` |
|---|---|
| Fodder TTK (Crawler, Walking Bomb) | ≤ 1.5 s |
| Standard TTK (Ledge Gunner — the calibration enemy; Shieldbearer once solved) | 2–4 s |
| Heavy TTK (Blink Tank) | 5–8 s |
| Player hits-to-die vs. regular enemies | 4–6 |
| Boss winning-attempt length | 2–4 min (§2.2) |
| Attempts to first boss clear (competent profile) | 3–6 |

**Horizontal bands (the asymmetry contract):**

1. **Clearability = 100%** — every class clears every room, branch, and boss at every bot profile; softlocks = 0. For the boss specifically (§7), this is met by tuning the fight's fixed constants against QA-crew data before ship, never by a runtime mechanic that loosens the fight after repeated failure. Hard assertion, build-blocking (§10).
2. **Boss parity with distinct death signatures:** class win rates against La Costurera within **±10 points** of each other AND inside an **absolute band of 15–35% per attempt at the competent profile** (decided Jul 20 — derived from the "3–6 attempts to first clear" anchor above so the two numbers stay consistent; the ±10 parity alone never pinned an absolute difficulty, which the stress-test board flagged) `[TUNE]`; the asymmetry is asserted on the **cause-of-death mix** instead — knight-kills dominate Titan deaths, witch-kills dominate Hunter deaths, and the two mixes must differ by ≥20 points `[TUNE]`. The same boss provably kills each class differently: asymmetric texture, symmetric difficulty.
3. **Regular-enemy TTK delta ≤ ±15%** between classes against the Ledge Gunner baseline — the palette must not silently tax one kit.
4. **Branch traversal time within ±20%** of each other (Segment B) — neither class pays a time tax for its identity.
5. **Damage-intake shape, not equality:** Titan is allowed more hits taken but must land in a similar effective-health-loss band per segment once shield absorbs and health drops (§2.4) are counted — trading is its plan, not its punishment. Hunter's intake should concentrate in boss fights.

---

## 8. The agent dev crew (crew → game system map)

Every crew unit produces a working piece of this game (the numbered IDs are the roster's stable references, used throughout this document):

| Crew | Discipline | What it builds for this game |
|---|---|---|
| #1–2 GDD authoring | Scoping | This document and its parent vision GDD |
| #3 Level crew (3+ agents) | Multi-agent orchestration (CrewAI) | Level Designer + Encounter Designer + Reviewer agents emitting room-spec JSON (Encounter Designer consumes the §6 palette) |
| #4 Lore pipeline (RAG, 3+ content types) | Content consistency | Room ambient descriptions, bestiary entries, item/upgrade flavor text — consistent with the full GDD's buried backstory, engine-ready |
| #5 GOAP boss brain | Autonomous agency | **La Costurera's squad brains** (three GOAP minds on a shared blackboard — witch as director + two knights; perception, competing goals, bounded non-random memory over a fixed, telegraphed pattern repertoire — §7's memorizable-core/adaptive-spice guardrail) |
| #6 Style & IP guard | Human touch / consistency | Validates all generated content against the style bible (§1.2 register), **flags placeholder leakage** (no Destiny-derived name may survive into the build — register in §1.3), and distinguishes accidental leakage from **deliberate homages on the approved-homage allowlist** |
| #7 Narrative engine (optional) | Multi-agent narrative | Layered lore reveal ordering across the two class runs |
| #8 Adversarial QA crew (**committed** — §2, §7.1 and §10 depend on it) | Chaos testing | **Balance harness:** headless runs, softlock detection, per-class boss win-rate reports |
| #9 Pipeline documentation | Production pipeline | Mermaid-diagrammed end-to-end pipeline: prompt → JSON → DataTables → UE5 |
| #10 Ship | Integration | The playable build |

**Agent→engine seam (decided):** two gated paths. **Content** (rooms, encounters, lore, feel parameters) — agents output validated JSON; a Python import step converts to CSV/DataTable format; UE5 consumes DataTables; no agent hand-edits content into engine files. **Gameplay logic** — the Coder agent implements config-driven Blueprints (tunables in DataTables, no hardcoded literals), and nothing it writes is accepted until its paired review and focused tests pass (the builder/judge law). Both paths keep every agent output a proposal until a human ratifies it.

**Crew charter (decided):** agents exist to **accelerate, never to decide**. Every creative decision — what ships, what it looks like, how it reads, how it feels — is made or approved by the human director; agents propose, generate variants, validate, and measure. This was already the shape of every pipeline above (room specs pass human curation before assembly; every sourced asset is human-approved before it enters the build); it is now the explicit rule for the whole roster. The crew is **not capped to the numbered roster**: an agent joins if it saves real calendar hours (§9) or improves a definition-of-done criterion (§10) — and every agent's output remains a *proposal* until a human accepts it.

**Builder/judge law (decided Jul 20):** nothing an agent generates ships unaudited. Every generator is paired with a checker — the Level Designer with the Room Reviewer, the Lore Scribe with the Style & IP Guard, the Coder with review + focused tests, and the whole build with the adversarial QA crew (#8). A generate-then-judge loop always ends on the judge, never the generator; an unjudged artifact can never be the pipeline's final state.

**Implementation (this crew is built, not just specified — Jul 23).** The orchestrator, the **12 agent specs**, and the deterministic gate live in `agents/`: `runner.py` (routes each agent to its subscription CLI — no per-token API keys — and runs the generate→validate→judge pipeline, including a 3-agent room-production chain), `validators.py` (the deterministic hard gate for room/encounter/text specs), `NN-*.md` (the specs), and `README.md` (the end-to-end Mermaid architecture diagram — the #9 pipeline-documentation deliverable). The asset needs list is `production/asset-manifest.json`. The submitted slice GDD (`GDD/deliverables/`) is the polished, player-facing cut of this document.

**Extended roster (decided — beyond the numbered map):**

| Agent | Role | Plugs into |
|---|---|---|
| **Asset Scout** (built) | Browses marketplaces (Fab / Sketchfab / freesound) against the `production/asset-manifest.json` needs list; checks licence + IP-safety; returns a ranked candidate shortlist (JSON) for human approval. Runs on the web-capable lane | §9.1 asset plan; §1.3 IP safety; licence log audited by #6; weeks 1–5 |
| **Player Psychologist** | Interprets QA-crew metrics (win rates, death patterns, TTK) as predicted player perception; drafts the hypotheses the human "fair vs. unfair" playtests confirm or refute | #8 reports; §7.1 bands |
| **Narrative Critic** | Quality reviewer for the lore pipeline — pacing, interest, cosmology coherence, EN/ES tone parity (complements #6, which covers compliance) | #4 pipeline; §8.1 |
| **Controls & Game-Feel Designer** (built) | Owns player controls: the verb→button scheme (§4.3) and the `DT_PlayerFeel` parameters (jump arcs, i-frame windows, coyote time, cancel priority), emitted as a DataTable the QA crew sweeps headless; never controls the player at runtime (§9.2 zero-runtime policy untouched). Promoted from the earlier "Feel-Tuning Agent" — "movement is the reward" (§2.3) is a core pillar, so feel gets an owner, not an implicit slot | §4.3 DataTables; #8 harness |
| **Adversarial Design Critic** (built) | Red-teams design specs *before* build — unwinnable/trivial states, cheese strategies, contradictions — as a Markdown risk report, each finding rated critical or deferred. Takes the player-facing roster slot the earlier "pipeline documenter" idea never earned (pipeline docs are a deliverable, #9, not an autonomous agent) | §7 boss; §2 loop; §10 definition of done |
| **Production Watchdog** | Weekly pass over the production calendar, repo activity, and cut lines; emits early risk alerts (e.g. cut-line #1 at risk) | §9 plan and cut lines |
| **UI Designer** (adopted Jul 20) | Emits functional UMG layout specs — widget hierarchy, screen flow, string-table and accessibility bindings — for the HUD and the class-select, run-complete, and pause/options screens, through the same JSON→engine seam as the level crew; all screens use marketplace/default styling and typography — no bespoke commissioned art (§9.1). Fills a real gap: UI was previously unowned in the roster | §4.4 HUD; §4.5 accessibility; §8.1 localization; §8.2 class-select beat; §9.1 asset plan |
| **Coder** (adopted Jul 20) | Implements one approved mechanic at a time as **config-driven Blueprints** — every tunable read from a DataTable, hardcoded values are a rejection condition — and ships a focused test with each change. Output is accepted only after the paired review (Room Reviewer / Style Guard as applicable) and its tests pass; proposes, never self-approves. Closes a gap: the roster was design/review-heavy with no agent that actually implements engine logic (a role present in most cohort GDDs) | §4.3 feel DataTable; §8 agent→engine seam; the builder/judge law (crew charter) |

**Bench (adopt only if cycles allow; not before week 3):** sound curator (likely just an Asset Scout query set), a schema guard for the JSON→DataTable seam (today covered by `validators.py` and the level-crew Reviewer), an explicit orchestrator (worth its overhead only past ~12 active agents), and localization QA (starts as a Narrative Critic concern).

**Evaluated and discarded:** a systems-designer agent (the system is this document, closed after the gap analysis — an agent here would re-litigate settled decisions) and a business-analyst agent (positioning is §1.1; at most a one-shot for store copy in week 6, not a crew member).

### 8.1 Localization (EN/ES, pipeline-integrated)

Full **English/Spanish parity from day 1** — localization as a pipeline property, not a post-production pass. It is also a deliberate showcase: it proves the agent→engine seam generalizes beyond level content.

- **Three text sources, one seam:** (1) hand-authored UI/system strings live in **string tables** from the first widget (§4.4); (2) agent-generated lore (#4) is **bilingual at the source** — every content record carries `text_en` and `text_es` fields in the same JSON, so there is no separate translation pass and the style guard (#6) audits both languages; (3) store/meta text is manual.
- **Deterministic validation:** no hardcoded literals (localization-gather audit each build), placeholder integrity (`{tokens}` intact in both languages), and **UI overflow checks** — Spanish runs ~20–30% longer than English; the weekly QA pass sweeps widgets at both locales.
- Locale switch exposed in the pause menu; default follows OS language, falls back to EN.

### 8.2 Narrative envelope (in scope — decided)

The slice is wrapped in a **four-beat narrative envelope**, delivered entirely through
existing systems — string tables (§4.4), bilingual lore records (§8.1), set dressing —
with **no new tech and no Sequencer cutscenes** (§3 non-goals):

1. **Opening cards.** 2–3 full-screen text cards on New Game: mood and setting, not
   story — enough atmosphere (§1.2 register) to make the first door feel like a
   threshold. No cosmology, no promised reveal (language calibrated Jul 17 to match
   what the slice's scope can actually deliver — §3 forbids cosmology reveals, so the
   cards no longer claim to). Always skippable.
2. **Class select as lore.** The class choice is framed as an in-world decision, not a
   menu — simple framing text, no invented ritual or vow (simplified Jul 17; the
   earlier "two oaths, one gate" language promised specific content — an oath, an
   authority, a cost — that was never written); the same screen carries the
   class-identity beat that §4.4's contextual prompts then reinforce in play.
3. **Environmental arrival.** The tutorial opens on the aftermath of the descent told
   by the room itself — set dressing plus one ambient lore record. No cutscene; the
   player has control from the first frame.
4. **Closing bookend.** After La Costurera falls, a return to the opening cards' visual
   language — the same mood-only register as beat 1, not a revelation. The text names
   what *this run* accomplished, not what secretly changed, and plants the other
   class's run as the hook (the replay seed, §2 — reinforced by the sealed-but-visible
   convergence door, §5).

All four beats are **content, not code**: they ride the lore pipeline (#4), are audited
by the style guard (#6) in both languages, and degrade gracefully — cards ship
hand-written if the pipeline slips. The envelope is never ship-blocking.

---

## 9. Production plan and cut lines

| Week | Build goal |
|---|---|
| 0 (now–Jul 13) | UE5 already installed on Nobara ✓. Clone & study *Project Lux* (2.5D controls/camera); grey-box room with a capsule that jumps, dodges, shoots using the §4.3 defaults; **verify gamepad input on Nobara** (SDL); **package a Linux build of the empty project** (de-risk shipping early) |
| 1 (Jul 14–19) | GDD v1 freeze; Hunter movement feel pass; pick base skeleton & prove the Mixamo→UE5 retarget path (§9.1) |
| 2 (Jul 20–26) | Level crew v1 → first agent-generated rooms in engine; hand cannon combat vs. dummy; **asset sourcing pass** (Asset Scout → shortlists for approval, §9.1) |
| 3 (Jul 27–Aug 2) | DataTable import automation; knight scripted base patterns; GOAP design for La Costurera's squad |
| 4 (Aug 3–9) | **La Costurera GOAP implementation** (moved up from week 5 — decided Jul 17: removing the traversal-unlock arc when the kit went open-from-start freed this week's capacity); Segment B branches; style guard live; **early "fair vs. unfair" human playtest** (scripted patterns as placeholder if the squad brain isn't fully live yet) |
| 5 (Aug 10–16) | Cross-class balance tuning (grenade cooldowns, cause-of-death bands, boss-bar go/no-go from week 4's playtest); **first Windows package + verification** (dual-boot, developer-owned — both engine sides already confirmed stable, so this is packaging risk only, not first-time engine risk) (+ narrative layer if on track) |
| 6 (Aug 17–23) | Content freeze Aug 20; pipeline doc (#9); bug-fix only |
| Aug 25 | Ship playable build + demo video |

### 9.1 Asset plan

**One track: marketplace / free assets only** (decided Jul 23 — the earlier two-track plan, with a commissioned 2D artist plus an AI-to-3D experiment for the player classes, is retired: no commissioned artist and no original 3D art). The build depends only on sourced assets curated toward the §1.2 register. The full needs list lives in `production/asset-manifest.json`; the **Asset Scout** agent (§8) browses marketplaces against it, checks licence and IP-safety, and returns candidate shortlists for human approval — every asset's licence is logged at import (style guard #6 can audit the log).

| Category | Need | Source (marketplace / free) | Needed by |
|---|---|---|---|
| Player classes ×2 | Humanoid, full locomotion + verb set | **Paragon** characters (free, AAA quality, UE license) or Fab humanoid equivalents | Wk 1–2 |
| Regular enemies ×6 archetypes | 1 humanoid base rig + material/scale swaps (§6); Crawler = simple non-humanoid mesh + spline | Fab humanoid pack or Paragon minion-class model | Wk 2–3 |
| Boss squad ×3 | All humanoid (§7): 2 knights = base rig scaled 2–2.5× + greatswords, heavy anim set; La Costurera = tall sleek caster 1.5–2× + staff, thread VFX (Niagara) | Fab knight/warrior + witch/caster models (marketplace-abundant); Mixamo two-handed/casting sets + video mocap for signatures (re-stitch channel, knight pincer) | Wk 3–4 |
| Animations | Locomotion, jump/double-jump, dodge, shield, fire, bash, grapple, deaths | **Mixamo** library retargeted to one base skeleton (IK Retargeter); gaps filled with video mocap (Rokoko Video / DeepMotion — record the move, apply to skeleton) | Wk 1 pipeline proof |
| Environment | Modular sci-fi corridor/room tileset; junction + convergence set pieces | Fab modular sci-fi pack + **Quixel Megascans** surfaces | Wk 2 |
| VFX | Muzzle, impacts, teleport (Blink Tank), shield, detonation, gate-open, the Weave / re-stitch | Fab Niagara packs | Wk 3–4 |
| Audio | SFX set + 2–3 music loops | Stock (Fab audio, Sonniss GDC bundles, Kenney) | Wk 5 |
| UI | Pips, glyphs, prompts (§4.4); class-select + run-complete imagery | UMG built by the UI Designer agent; icon pack + font from Fab / Google Fonts; typography where no fitting art exists | Wk 3 |
| Style bible (#6) | Canonical art reference for the style guard agent | Curated from the chosen Fab/Paragon set **toward the §1.2 register** | Wk 2–4 |

**Selection bar:** the camera distance (§5.1, ~900 units) sets the real quality bar — silhouette and palette over mesh detail. Every asset's licence must permit course (non-commercial) use; licences that also allow later commercial release are preferred. Because there is no bespoke art, cohesion is bought at the *selection and grading* level (§1.2): a hard-surface master material set unifies mixed-source assets into one look.

**Pre-agreed cut lines (in order of sacrifice):** Titan is **no longer a cut line** — with a single shared boss, both classes are load-bearing for the slice's own thesis ("one map, one boss, two kits feel different"); cutting Titan would cut the reason the slice exists. If the schedule slips, the sacrifice order below applies instead.
1. **Level crew (#3) → hand-authored rooms** (Jul 26 — added Jul 17: this was the one load-bearing system with no dated fallback): if the 3-agent CrewAI pipeline hasn't produced one validated, engine-importable room by end of week 2, the remaining committed rooms are hand-authored directly into the same room-spec JSON schema — the deterministic Reviewer-agent checks (§2.4, §5.1, §6) still run against hand-authored specs, so the validation safety net survives even though the generative front-end didn't. The crew keeps iterating in parallel without blocking main development; it can still ship later rooms if it stabilizes.
2. **La Costurera's GOAP → scripted fallback** (Aug 13): if the squad GOAP isn't stable, all three entities ship with per-class scripted pattern sets (70/30: 70% shared base, 30% per-class modifiers — the witch's modifiers keyed vs. Hunter, the knights' vs. Titan, §7); the GOAP work still ships as a crew #5 tech demo in a test arena.
3. **Class branches in Segment B**: collapse to a single shared route; asymmetry then lives in Segment A's kit-gated pockets, the encounter texture, and the boss matchups. The junction keeps **one shared gate that opens with either class's key** — the reopen beat survives; only exclusivity is sacrificed.
4. **Narrative layer (#7)**: optional crew unit; drops without touching the build.

**Degrade paths for production commitments (added Jul 17):** the numbered cut lines above are game-facing; these two are pipeline-facing and previously had no fallback at all. If the Aug 20 freeze is at risk: **localization** degrades from a full weekly EN/ES QA sweep (§8.1) to spot-checks only — English always ships complete, and any Spanish content already generated is never retired (it's cheap because it's bilingual at the source, not a separate translation pass). **The optional bench** (§8) sheds in this order: Production Watchdog → Narrative Critic → Player Psychologist. The **Asset Scout** and the **Controls & Game-Feel Designer** are committed (built), not shed candidates — the first sources every asset, the second owns a core pillar.

**Top risks:** (1) UE5 learning curve — the engine choice is **committed** (UE5 is a project priority, already installed); mitigation is depth, not fallback: *Project Lux* as reference architecture, Blueprints over C++, native UE tools where they exist (Behavior Trees for the knights' scripted base patterns, Enhanced Input, DataTables), and packaging a build in week 0 so shipping is never a first-time event; (2) asymmetric balance cost — mitigated by the QA agent harness; (3) content sprawl — mitigated by agent generation + Aug 20 content freeze; (4) **Windows packaging from a Linux dev environment** (UE5 cannot cross-package Linux→Windows) — mitigated by the dual-boot Windows partition: UE5 installed there, first Windows package no later than week 5 (§1.1); (5) **Linux-as-dev-environment friction** (UE 5.8 was unusable on this machine and cost a night — see production notes) — bounded by a pre-committed tripwire: *if an engine/OS issue blocks development for more than 4 cumulative hours during weeks 1–2, development moves to the Windows side of the dual boot without renegotiation; Linux remains a first-class build target either way.* Status Jul 17: tripwire never triggered — 5.7.4 (the working engine) and a patched 5.8 build both confirmed stable in testing; this risk is now theoretical, kept for the record.

### 9.2 Token budget

**Runtime policy first, because it dominates everything:** the shipped game makes **zero LLM calls**. La Costurera's squad brains are classical GOAP (no per-frame inference), and all agent-generated content is build-time data. Consequence: no API key in the build, no marginal cost per player, no latency risk in gameplay.

All spend is therefore **development-time**, per pipeline. Estimates below are starting guesses to be **replaced by measured spend** — every crew run logs actual usage (model, input/output tokens, cache hits), and the measured table supersedes this one from week 2 onward.

| Pipeline | Est. volume (production total) | Model tier | Est. cost |
|---|---|---|---|
| Level crew (#3): rooms proposed → reviewed → revised | ~150 crew cycles × 10–40k tok (3 agents/cycle; input context dominates — recalibrated Jul 17 against measured agent runs of 70–140k tok each) | Mid (Sonnet-class) | $15–30 |
| Lore RAG (#4): ~80 records × 2 languages | ~0.5–1M tok + embeddings | Mid; embeddings negligible | $5–10 |
| Style guard (#6): per-record checks + build sweeps | ~400 checks × 1–2k tok | Small (Haiku-class) | $1–3 |
| GOAP boss (#5) | Design-time iteration only, ~0.2–0.5M tok; **runtime = 0** | Mid | $3–8 |
| QA crew (#8): run-report synthesis | ~60 reports × 2–5k tok (headless runs cost zero LLM tokens) | Small/mid | $2–5 |
| Narrative layer (#7, optional) | ~0.3M tok | Mid | $3–6 |
| **Production total (est.)** | **~5–10M tokens** | — | **~$30–60** |

**Cost levers (in order):** prompt caching on stable prefixes (crew system prompts + style bible — cached reads ≈ 10% price); **Batches API at −50%** for all offline generation (lore, bulk room drafts); small-model routing for checks; **local drafts** via Ollama/ROCm for bulk first passes with API models reserved for quality passes and final content `[TUNE: local quality bar]`. Evals mirror production models and parameters — measuring with a different tier than the pipeline uses reports a different system's cost and quality.

### 9.3 Cinematic moments (stretch, week 5; never ship-blocking)

**Principle:** no authored cutscenes — ever, in this build (§3). Cinematic *feel* is assembled from systems that already exist: the camera rig (§5.1), the boss intro cards (marketplace art / typography, §9.1), and trigger+text+VFX lore beats in existing slots. 90% of the feeling at 5% of the cost — and the direct payoff is the **demo video** (§9, Aug 25): two or three of these moments are the difference between footage that reads as a prototype and footage that reads as a game.

Build order (window: week 5, before the Aug 20 content freeze; each item cuts independently and silently):
1. **Boss intro:** on arena entry, ~1.5 s camera hold on La Costurera flanked by her knights + intro card (marketplace art / typography, §9.1) before control returns.
2. **The junction gate answering:** a 2–3 s camera pan to the player's branch gate as it reads the class key and unseals — the identity beat (§2.2) landing on screen, not just in theory.
3. **Pocket lore micro-events:** in the existing kit-gated pockets (§5), claiming the cache triggers a small staged beat — a mural lights up, a visual echo `[TUNE: 1 per segment]`. Trigger + text + VFX only; nothing animated beyond what Niagara gives.
4. **Cenote beacon (vista checkpoint #1):** one checkpoint room (§2.4 system, unchanged) staged as a hero room. Underground level of a ruined technological installation, time- and war-worn; the far wall is broken open onto a large rock chamber holding an underground lake — a cenote — lit dimly by shafts of light through ceiling cracks. Interacting with the beacon is framed as **meditation**: the camera blends to an authored framing of the vista (§5.1 authored-framing mechanism; any input cancels — no cutscene) while the checkpoint does its §2.4 work. The vista is pure backdrop: the 2.5D plane constraint means the player can never walk toward it, so it is kitbashed depth set-dressing (cave meshes, a simple water plane, light shafts, fog) — never playable space.
5. **Overlook beacon (vista checkpoint #2):** the *highest* checkpoint on the map. Same staging grammar: broken far wall, authored meditation framing — opening onto a sunset over the surrounding ruins of what was once a technology hub, now silhouettes in layered parallax (the parallax depth §5.1's perspective camera exists to sell). One ambient lore record each (#4, bilingual) gives the two rooms their voice.

**Vista-room build rule:** both beacons exist from day one as ordinary grey-box checkpoint rooms with a hole in the far wall (cost ≈ zero); the vista dressing is the stretch. Beacon/vista rooms carry **zero enemies** — natural spaces are safe ground (full GDD §9.1), encoded as a deterministic Encounter Designer check (§6). Beauty pass only inside this §9.3 window, marketplace assets only (§3), and these two rooms are the designated "hero rooms" of the demo video.

**Hard boundary (anti-sprawl):** no Sequencer cutscenes, no acting characters, no synced dialogue, no camera work that requires new animation (the meditation framing works as a pure camera hold; a retargeted marketplace sit/kneel idle may be added but is never required). If a proposed moment needs any of those, it belongs to the full GDD.

---

## 10. Definition of done (Aug 25)

- A playable build where **both classes** complete: Start → Segment A → their own Segment B branch → La Costurera → run-complete screen.
- All shipped content passed through the agent pipeline (level specs, lore text, style guard) with the pipeline documented end-to-end.
- Boss balance validated by QA-agent reports (win-rate per class within agreed band, zero known softlocks).
- No placeholder IP names present in the build.
- Builds delivered for **Windows and Linux**; the Windows build verified on non-dev hardware before ship week (§1.1).
