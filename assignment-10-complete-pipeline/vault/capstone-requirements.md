# Capstone requirements — what the course grades

Distilled from `../production/course-playbook.md`; this note is the
checklist, that document is the evidence.

## Dates

| | |
|---|---|
| **Aug 27** | internal: playable loop in course Discord (peer-feedback window) |
| **Sep 1** | **Assignment 10:** playable link (mandatory — ≤50% score without) + pipeline source/description + cost audit |
| **Sep 8** | capstone final; polish week; links stay editable |

## The bar

- Playable by a stranger within 2 minutes of clicking. **Endless mode is
  compliant**: the course states that for infinite modes "playing until you
  die is an end", tower-defense explicitly cited. The run must therefore END
  CLEANLY — Beacon breaks → score screen → play again in one input. The
  score screen is the ending, and it must feel like one.
- Web build on itch.io (HTML5). Upload in week 1 — WebGL renders
  differently; platform risk dies early, not the day before.
- Demo video 2–3 min, from launch, one complete loop; ≥1-min video on the
  itch page.
- AI-asset disclosure checkbox once PixelLab assets ship.
- Cost audit: aggregate `production/output/usage_log.jsonl` (recording since
  assignment 3) into a per-agent, per-model table.
- Content traceability: provenance sidecars — already standard.
- Alpha with documented bugs beats broken ambition: "a simple, fun, working
  game scores higher than an ambitious, broken, impressive one."
