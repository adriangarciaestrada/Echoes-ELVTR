# The Loom grid — geometry and class asymmetry

Owns every grid number. The asymmetry contract's law — exclusivity by
placement, never raw power — applied as shape.

| | Hunter | Titan |
|---|---|---|
| Start | 3×4 (12 cells, tall) | 4×3 (12 cells, wide) |
| Full board | **5×8 = 40** | **8×5 = 40** |
| Per expansion | +4 cells, player-placed, edge-adjacent to unlocked cells | same |
| Expansions per run | until the board is full, ~6 (EXP alternation, `economy.md`) | same |

**40 = 12 + 4×7 exactly, and that is a constraint, not a coincidence.** The
first draft used a 35-cell envelope, which left three cells on the final
expansion of four — a pending cell with nowhere legal to go, and a run that
could never leave the expansion phase. Any change to these numbers must keep
`(w×h − 12)` divisible by 4; `expansionsToFill()` throws if it does not, and
the run converts unplaceable pending cells into buff choices as a second
guard.

Reference used 15 → +6 → 9×9. Ours is smaller per step but reaches its full
board the same way: over a long run, a deep player fills it. A run that ends
before the board is full ended because the player's decisions ran out, not
because the game withheld cells.

Rules:
- A placed expansion cell is permanent for the run.
- Relics may be lifted and repacked freely during any market phase; nothing
  commits until Continue (`economy.md` owns the market).
- Both classes reach the same 40-cell maximum; neither ever has more cells
  than the other — the difference is *where* they can put them. Asymmetry is
  placement, never power (`from-echoes/class-asymmetry-contract.md`).
