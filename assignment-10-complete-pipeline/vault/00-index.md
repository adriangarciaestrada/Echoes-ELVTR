# The Loom — vault index

Start here. This section is the law for the Echoes spin-off ("The Loom", web,
Phaser 3). One note owns each rule; nothing is restated. Agents load ONLY the
notes their task names — a guide assembled from a subset of the law will
confidently approve what the missing note forbids, in either direction.

## Loom-section notes

| Note | Owns |
|---|---|
| `loom-design.md` | the pitch, the loop, and nothing numeric |
| `differentiators.md` | where we diverge from the reference, and why |
| `relic-contract.md` | RelicSpec: schema, tiers, the four relic laws, what the gate enforces |
| `loom-grid.md` | grid geometry, expansion, class asymmetry as shape |
| `combat-model.md` | deterministic battle resolution; the pure-core architecture law |
| `wave-contract.md` | WaveSpec: enemy roster, budgets, the simulator gate |
| `economy.md` | gold, market, rerolls, pool removal, EXP alternation |
| `bosses.md` | the three recurring boss archetypes |
| `ui-and-strings.md` | Loom screens, widget classes and caps; how the style loop applies |
| `art-direction.md` | PixelLab pipeline, sprite sizes, tier colours, disclosure |
| `capstone-requirements.md` | deadlines and deliverables the course grades |
| `reference-game.md` | EVIDENCE, not law — the reverse-engineered reference |
| `prologue-origin.md` | how the Weaver ends up alone at the Beacon — generated lore, not hand-authored |

## Forked from the Echoes vault — `from-echoes/`

This vault is **self-contained by design**: the two games evolve
independently, so the binding universe and pipeline notes were FORKED here
on 2026-08-21 rather than referenced across vaults. From that date, these
copies are this game's law and may diverge; the originals in the Echoes
originals keep governing the other game alone. Each fork was **reduced to
what binds here** — metroidvania law inside them was removed as noise.

| Note | Status here |
|---|---|
| `from-echoes/terminology-guard.md` | **BINDS.** Every string, name, and asset id |
| `from-echoes/architects-cosmology.md` | **BINDS.** The tone, the Architects, the constructs |
| `from-echoes/class-asymmetry-contract.md` | **BINDS in principle** — "exclusivity by placement, never raw power"; `loom-grid.md` is its application |
| `from-echoes/ui-constraints.md` | **BINDS** for GLANCE→GRASP→ACT→TRUST and plain-where-plain-is-correct; its screen list is the OLD game's — `ui-and-strings.md` owns this game's screens |
| `from-echoes/authoring-pipeline.md` | **BINDS.** Generate→Validate→Review→Import, provenance, rules fingerprint |

## Not part of this vault — do NOT load into this game's agents

Anything from the Echoes vault not forked above: `04-world/*` (metroidvania
geometry), `ui-budgets.md`/`uispec.md` (caps redefined in
`ui-and-strings.md`), the old enemy and boss rosters, `editor-tooling.md`
(Unreal-specific). Craft knowledge lives in `../gamedev-vault/`, which is
game-agnostic and safe to load anywhere.
