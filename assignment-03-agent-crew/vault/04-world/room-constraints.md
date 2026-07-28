# Room Geometry & Checkpoint Constraints — Echoes (GDD V2)

## Room Dimensional Constraints
- **Width:** 2000 units (small corridor) to 6000 units (large arena).
- **Height:** 1000 units (flat passage) to 3000 units (vertical shaft).
- **Plane Constraint:** Y-axis depth offset = 0. All walkable surfaces strictly along X/Z plane.

## Checkpoint Rules
- Checkpoint nodes MUST be placed at room entry points or adjacent to boss doors.
- Maximum of 4 consecutive rooms without a checkpoint.
- Checkpoints fully restore health (Dread convention).
- Checkpoints contain ZERO enemies.

## Camera Bounds Rules
- Every room spec MUST define a camera bounding box containing all walkable surfaces.
- Camera is author-controlled 2.5D follow (no manual player camera rotation).
