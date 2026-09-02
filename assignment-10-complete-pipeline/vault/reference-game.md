# Reference Game — Salvation Breakers / FIGHT! ARK RANGER! (NIKKE)

The mechanical reference for the web pivot. Source of truth: firsthand play
(Adrián played both events), corrected against a full-loop video
(https://www.youtube.com/watch?v=B61X5fvZ2tQ). Web articles got the combat
layer wrong — they described move-and-dodge controls that do not exist. Both
the 2025 collab original and the 2026 reskin play identically.

## The two halves

The game alternates two phases, and the inventory phase carries most of the
fun (Adrián's estimate: combat is less than half).

```
BATTLE (auto)  →  MARKET + PACKING (manual)  →  BATTLE  →  …
```

## Battle phase

- The character is **stationary**, defending a barricade at the bottom.
  Enemies stream top → bottom toward it.
- Aiming is **automatic** — the character rotates toward targets.
- **Exactly one manual input:** the character's super/ultimate, on cooldown.
  Each playable character has a different super; all do damage to several
  enemies at once.
- Weapons fire **on individual cooldowns** — no ammo. The core stat balance:
  fast fire / low damage vs slow fire / high damage.
- Higher tier = more damage **and** faster cooldown.
- Kills award **EXP** and **money**.
- **EXP bar → upgrades, strictly alternating:** first fill grants a buff,
  second grants grid expansion slots, third a buff again, and so on.
- Waves scale in enemy **count and speed**. Every **5th wave** brings a big
  boss onto the field.

## Weapon archetypes

| Archetype | Examples | Role |
|---|---|---|
| AoE | grenade, flamethrower | crowds |
| Long range | laser beam, sniper rifle | reach the top of the lane |
| Mid range | handgun, shotgun | the bread and butter |

## Inventory phase (the attaché case)

- The case is a **grid that starts small** and grows only through the
  EXP-alternation expansion slots.
- Weapons occupy **polyomino shapes** (built from squares, all different), so
  fitting them is the puzzle.
- **Rotation is a key feature** — rotating a weapon changes what fits.
- **Merge:** drag one weapon onto the *same weapon at the same tier* → single
  weapon one tier up. Tier is shown by background colour
  (Green → Blue → Purple → Yellow).
- **Market at the end of every round:** 3 random weapons offered; take any
  into the case or leave them. **Refresh** re-rolls the offer — the first few
  refreshes are free, then they cost money.

## The decision texture (what makes it fun)

1. **Packing:** do I take a weapon I can't fit yet, or skip it?
2. **Merge timing:** merging frees cells but sacrifices a body that was
   firing; two mid-tier weapons out-shoot nothing while merged badly.
3. **Refresh gambling:** spend kill-money hunting a merge partner, or bank it.
4. **Buff vs expansion rhythm** is imposed, not chosen — the game alternates
   for you, so planning happens around a known schedule.
5. **Archetype spread:** all mid-range dies to crowds; all AoE dies to
   fast single targets.

## Scale of the reference (NOT ours)

30+ waves, 20–30 minute runs, wave-100 possible for experts. Our slice: same
loop at roughly a tenth of the content. `[TUNE]`


---

# Pinned by screenshots (wave-100 endgame run, `FightArkRangerScreenshots/`)

15 captures: battle, three inventory states, result, stats, and four trait
lists. Numbers below are read off the screens, not remembered.

## Weapon roster and the real category split

Twelve weapons in **three categories** (the trait text names the members):

| Category | Members | Buffed by |
|---|---|---|
| **Normal attacks** | Ark Submachine Gun, Ark Shotgun, Ark Machine Gun, Ark Pistol | normal damage %, normal reload % |
| **Area attacks** | Ark Launcher, Ark Fire, Ark Grenade, Ark Photon Cannon | area damage %, area reload % |
| **Summons** | Supporter: Boomerang / Missile / Dual Pistols / Blade | summon damage %, summon reload % |

(The play-memory split of AoE / long / mid range was close but the game's own
taxonomy is normal / area / summon — traits target exactly these three sets,
which is why the taxonomy matters: **the buff system is the category system**.)

## Traits — the EXP-bar buffs, observed values

Stacking percentages across a run, e.g.: area damage +44 → +96 → +123 → +158%;
area reload −34 → −53 → −58 → −78%; all-main-weapon damage +12/+22%; all-main
reload −4/−12/−16/−24%; normal damage +7/+39%; normal reload −3/−13%; summon
damage +24%; initial attack range +22/25/27/37%; knockback +0.5/+1 m; blaze
zone +0.75/1.5/2.25 s; debuff duration +0.75/1.25/2.25 s; DoT duration +0.5 s.
Pure data — a table of (target set, stat, magnitude). This is DataTable
content, which is the point.

## The case, observed

- **Grid numbers (firsthand): starts at 15 cells; each expansion adds 6
  cells, and the player chooses which cells unlock; full board is 9×9 (81).**
  That is ~11 expansions across a full run. Endgame boards look irregular
  because the outline is player-chosen, not because the grid is.
- Footprints seen: 1×1 (grenade), 1×2 / 2×1 (pistol, capsule), 2×2 (toolbox
  item), L-shapes (launcher), Z/S-shapes, a plus/cross (Supporter: Blade),
  1×3 tall. Real polyomino variety.
- Tier is the **cell background colour** behind the item. Backgrounds observed:
  plain/base, blue, purple, yellow (endgame boards are mostly yellow — max
  tier). Matches the remembered Green→Blue→Purple→Yellow ladder with base
  grey/green as the entry tier.
- Non-weapon 1×1 items exist (green gems; a red 2×2 tool kit) — pickups or
  utility items that also cost case space.

## Battle screen layout (one phone-portrait column)

Top: wave counter, level + EXP bar, gold, score, **speed toggle (1×/6×)**,
pause. Middle: the lane — enemies descend, damage numbers with CRIT!/EXTRA
popups. Bottom: the **barricade with its own HP bar (heart icon, %)**, the
character behind it, the **ultimate button** bottom-right, and the whole
arsenal laid out as an icon strip under the HP bar.

## The economy, from three result screens

Wave-100 runs: 4,306 kills; gold earned ≈ 926k–1,030k; **gold spent ≈
903k–990k** — ~95% of all gold goes into market refreshes. The refresh gamble
IS the economy. Score ~707k; a daily target-score chest (1,000 points) pays
out regardless of depth reached.

## QoL worth copying

- 6× speed toggle (also makes a 2–3 min demo video of an autobattler feasible)
- Restart / Return + Stats / Inventory / Traits from the result screen
- Per-weapon damage-dealt bars at the end — instant "what carried the run"


---

# Reverse-engineered design choices (from r/NikkeMobile strategy posts)

Strategy threads are involuntary design docs: what players optimise around is
what the designers made matter. Each observation below is paired with the
design rule it implies for our game.

## The merge is deliberately lossy — and that IS the game

> "I would add the 2 base grenades together, but not combine the new two blues
> since **they do more damage separate than they do as a single purple**. I'll
> only combine them once I get another item to fit that open slot."

**The single most important number in the design:** one merged tier-N+1 weapon
deals LESS damage than the two tier-N copies it consumed. You never merge for
damage. You merge for **space** (one footprint instead of two) and for
**effect unlocks** (see below). Merging is a sacrifice with two currencies,
and expert play is deciding *when* the sacrifice pays.

→ Our rule: `damage(tier N+1) < 2 × damage(tier N)`, always. `[TUNE]` the
ratio (~1.6–1.8×), never ≥ 2×, or the whole decision collapses into
"always merge" and the inventory game dies.

## Tiers gate effects, not just stats

> "Weapons get secondary effects at blue and purple rarity. These can be more
> important than the basic stats."

Grenade gains slow + stun chance; Launcher gains a DEF-lowering debuff (a
damage amplifier for everything else); Blade gains a bouncing multi-hit slow.
The tier ladder is a **capability ladder**, which is why lossy merging is
still tempting.

→ Our rule: every relic gets one new effect at tier 3 and one at tier 4, so
"is the merge worth it" never has a static answer.

## Some effects refuse to stack — creating "one-of" slots

> "A single shotgun is needed too since it has a knockback effect on its own…
> doesn't stack with multiple copies since they all hit simultaneously."
> "The Blade… you only need one since it bounces around the screen."

The arsenal splits into **carry stacks** (grenades × 8) and **utility
one-ofs** (knockback, slow). That split is what makes packing interesting —
you're not filling a case with copies of the best gun.

→ Our rule: at least two relics whose signature effect explicitly does not
stack, stated in their description.

## The pool can be thinned — deck-building the RNG

> "Remove the weapons you don't want early so you have a higher chance of
> getting the ones you want." "Min-max buffs by focusing on one or two weapon
> types. Coordinate with Weapon Removals."

There is a **weapon-removal** action: market offers draw from a pool, and
removing a weapon type from the pool raises the odds of everything else.
Build identity = category focus + pool thinning + buff targeting.

→ Our rule: keep it. It is one button in the market UI and it converts
"reroll and pray" into an actual plan.

## The economy is fully run-scoped, in two phases

> "Focus on getting Gold at first to buy all the Upgrades first. After that,
> Gold is only used for rerolls and **you can only use Gold earned in that
> run**, so there's no point hoarding it."

Phase 1: buy out a small per-run upgrade shop. Phase 2: everything into
rerolls (~95% of ~1M gold, per the result screens). No cross-run currency.
Separate reroll pools for gear and perks.

→ Our rule for the slice: run-scoped gold, one small upgrade set, then
rerolls. No meta-progression — honest for a capstone and cheaper to build.

## Draft pools contain deliberate traps

> "Levels cap at 40, which you'll hit before the waves get hard, so **EXP
> buffs are a complete waste**." "Do not pick exp perks ever. They are a trap."

The perk pool knowingly contains dead picks late-run. Reading the pool is a
skill. Also: "You won't get a level 100 run all the time. Sometimes you get
perks that suck" — high variance is accepted, the daily target-score reward
(1,000 pts) pays out regardless of depth.

→ Our slice: skip trap design (needs tuning maturity we don't have), keep
the variance-friendly scoring: score pays out even on a loss.

## The community invented damage-per-cell — our balance metric

> "Ark Pistol does have the highest ATK to size ratio…" "Supporter: Missile
> takes up too much space to be worth it."

Players evaluate weapons in **damage per grid cell**. That is exactly the
metric our headless simulator should report per relic, and the wave gate
should enforce a band on: no relic strictly dominant, none strictly dead.

## Community buff priority (their tuning, our starting point)

> "Whichever build you decide… **reload is king**. After that range, then
> knockback, then debuff, then blaze area, then damage."

Reload > range > utility > flat damage. Cooldown reduction compounds with
everything; flat damage doesn't. Inherit this shape when tuning trait
magnitudes.

## Full repacking is allowed, and it is gameplay

> "Sometimes it looks like an item won't fit, so just take everything out and
> rearrange. I've found a lot of the time if I build it differently I can
> make space for another gun."

Between waves you can lift the whole case and repack from scratch. The
packing puzzle is replayed, not append-only.

→ Our rule: the market screen has no placement commitment until you hit
Continue. Take-everything-out must be one button.

## Characters are builds, not skins

> "I used the character that starts with the bow and knockback ability."
> "I select the character that has the heal + reload speed skill."

Character choice = starting weapon + a passive/active kit that suggests a
build direction. Maps 1:1 to our two classes: Hunter and Titan differ in
starting relic, super, and loom shape.
