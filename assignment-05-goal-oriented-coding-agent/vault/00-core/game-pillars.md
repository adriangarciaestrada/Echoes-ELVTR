# Game Pillars & Design Law — Echoes (GDD V2)

## In One Sentence
A 15–25-minute 2.5D sci-fi metroidvania where one map plays as two different games depending on the class you pick — built by a crew of AI agents that playtest every build to keep the two classes provably fair.

## Core Design Pillars

| Pillar | Player-Facing Promise | How We Test & Validate It |
|---|---|---|
| **One Map, Two Games** | The same world plays differently depending on your class (Hunter vs Titan). | The two runs diverge in verbs, route, and boss pressure — the QA crew's per-class cause-of-death mix must differ measurably by ≥20 points. |
| **Asymmetry Budgets Difficulty, Never Possibility** | Nothing is ever class-impossible; hard is never unfair. | Clearability is 100% at every competent bot profile; both classes sit in a 15–35%-per-attempt win band, within ±10 points of each other. |
| **Movement is the Reward** | Traversal feels good enough to be its own payoff. | Feel parameters live in DataTables and are swept headless; pure-traversal rooms must read as fluid, not filler. |

## Deliverable & Win/Loss Conditions
- **Win Condition:** Defeat the boss, **La Costurera**, and reach the run-complete screen.
- **Loss Condition:** Health reaching zero. Death is a soft loss: respawn at last checkpoint at full health with world state intact. Max loss: ~2–3 minutes of traversal.
