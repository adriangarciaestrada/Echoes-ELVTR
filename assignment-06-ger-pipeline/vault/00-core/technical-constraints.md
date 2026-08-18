# Technical Constraints & Engine Rules — Echoes

## Engine & target architecture

There are **two projects, two engines**. Which one is open decides everything
below; check before acting.

| | `~/dev/ELVTR/Echoes` | `~/dev/ELVTR/Echoes-58` |
| --- | --- | --- |
| Engine | 5.7.4 | 5.8.1 |
| `DefaultBuildSettings` | `BuildSettingsVersion.V6` | `BuildSettingsVersion.V7` |
| Editor tooling | `ue-mcp` with a patched bridge plugin | Epic `ModelContextProtocol` + `EditorToolset` + `UMGToolSet` + `VibeUE` |
| Role | shippable fallback, untouched | active development |

Asset conversion is one-way, which is why these are separate clones rather than
branches. Never open the 5.7.4 project with 5.8.

- **Platforms:** native Linux is first-class and packages successfully; Windows
  packaging happens on the dual-boot side with the same engine version.
- **Execution rule:** launch via `./editor.sh`. Never `kill -9` the editor.
- **Packaging on 5.8.1** requires `r.PSOPrecaching`, `r.PSOPrecache.Compute` and
  `r.PSOPrecache.Global` all disabled in `[SystemSettings]`; precaching crashes
  the RADV driver on this host, and all three are needed — disabling one is not
  enough.
- **Every tooling plugin needs `"TargetAllowList": ["Editor"]`**, or the packaged
  game aborts at startup pulling in editor-only modules.

## Development ground rules

1. **Hybrid C++ and Blueprint**, with Enhanced Input. The project has a C++ game
   module at `Source/Echoes/`. The routing rule — what belongs in code and what
   belongs in an asset — is decided by *what verifies the work*, and is stated in
   the repository's `CLAUDE.md`. Decide the layer before authoring, not after.
2. **Zero GAS in game code.** No AbilitySystemComponent, no GameplayEffects, no
   GAS nodes. Tooling plugins mount GameplayAbilities transitively; that is
   tolerated, and the corresponding tool categories stay disabled. Never enable
   an "all toolsets" option, which pulls them back in.
3. **Data-driven tunables.** Hardcoded movement speeds, damage values, cooldowns,
   coyote time and i-frame durations are forbidden; they come from DataTables.
   The feel table exists: `Content/Data/DT_GameFeel`, imported from
   `SourceAssets/DT_GameFeel.csv` against the C++ row struct `FGameFeelRow`, and
   applied at run time by `UGameFeelComponent`. Enemy and balance tables follow
   the same shape when they are built.
4. **2.5D plane constraint.** Movement is confined to the plane: X horizontal, Z
   vertical, Y depth fixed (`bConstrainToPlane = true`).
5. **Runtime LLM policy.** The shipped game makes **zero LLM calls**. Models and
   agents are build-time tooling only. Run-time behaviour is classical and
   deterministic.
6. **Localization from day one.** All user-facing text is authored EN/ES and
   reaches widgets as a String Table binding, never as a literal. Text widgets
   are sized to the Spanish, the longer language.

## Where the rest lives

- The authoring pipeline and what may be automated: `08-pipeline/authoring-pipeline.md`
- Verified editor tool behaviour and its traps: `08-pipeline/editor-tooling.md`
- Measured movement reach, which decides what geometry is possible: `04-world/movement-reach.md`
