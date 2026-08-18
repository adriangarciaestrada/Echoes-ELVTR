# GOAP Blackboard & Goal Architecture — Echoes (GDD V2)

## Shared Blackboard Keys
- `PlayerClass`: "Hunter" | "Titan"
- `HunterDodgeHabitScore`: float (0.0 to 1.0, tracks preferred dodge vector)
- `TitanShieldActive`: boolean
- `Knight1State`: "Active" | "Weaving" | "Downed"
- `Knight2State`: "Active" | "Weaving" | "Downed"
- `ReviveWeaveProgress`: float (0.0 to 1.0)
- `WitchVulnerable`: boolean

## Goal Hierarchy
1. `ProtectWitch` (Knights: interpose between player and Witch while Witch is casting).
2. `PredictHunterDodge` (Witch: select volley angle covering `HunterDodgeHabitScore`).
3. `FlankTitanShield` (Knights: position at >90° relative angle from Titan facing).
4. `MaintainWeave` (Witch: channel revive weave when one knight is down).
