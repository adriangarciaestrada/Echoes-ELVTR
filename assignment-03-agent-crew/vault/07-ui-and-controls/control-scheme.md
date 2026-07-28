# Control Scheme & Game Feel Parameters — Echoes (GDD V2)

## Control Input Philosophy
- **Gamepad First:** Designed primarily for controller play via Enhanced Input plugin. Full keyboard fallback. NO mouse aiming.

## Default Game Feel Parameters (`DT_PlayerFeel`)
- **Coyote Time:** 120 ms.
- **Jump Input Buffer:** 150 ms.
- **Variable Jump Height:** ~40% minimum jump hold threshold.
- **Dodge Duration:** 400 ms total with 250 ms core i-frames.
- **Cancel Priority:** Defense has priority (fire is always cancelable into dodge/shield).
- **Turnaround:** Instant turnaround on horizontal axis.
- **Landing Lag:** 0 ms landing lag on standard jumps.
