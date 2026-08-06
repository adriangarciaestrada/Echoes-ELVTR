# Technical Constraints & Engine Rules — Echoes (GDD V2)

## Engine & Target Architecture
- **Engine Version:** Unreal Engine 5.7.4 (Installed at `~/UnrealEngine/Linux_Unreal_Engine_5.7.4`).
- **Platforms:** Windows and Native Linux (Nobara Linux dev host; Windows dual-boot packaging).
- **Execution Rule:** Launch editor via `./editor.sh` (`SDL_VIDEODRIVER=x11`). Never `kill -9` the editor.

## Development Ground Rules
1. **Blueprints + Enhanced Input:** Gameplay logic implemented in Blueprints. No C++ game modules unless explicitly authorized.
2. **Zero GAS:** GameplayAbilities (GAS) is prohibited in game code. Use clean Blueprint components.
3. **Data-Driven Architecture:** Hardcoded tunables are forbidden. All movement speeds, damage values, cooldowns, coyote time, and i-frame durations MUST be read from DataTables (`DT_PlayerFeel`, `DT_EnemyStats`).
4. **2.5D Plane Constraint:** All movement is constrained to the 2D plane along the X-axis (horizontal) and Z-axis (vertical). Y-axis depth offset is zero (`bConstrainToPlane = true`).
5. **Runtime LLM Policy:** Shipped game makes **ZERO LLM calls**. All runtime AI uses classical GOAP and deterministic Blueprints.
