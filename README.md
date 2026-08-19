# Echoes — ELVTR Course Deliverables

Development-time deliverables for the ELVTR course *"Multi-Agent AI for Game
Development"*, built around the capstone game **Echoes** — a 2.5D sci-fi
metroidvania in Unreal Engine 5.8.

Each deliverable lives in its own self-contained folder (its own README and,
where relevant, runnable code and evidence). This repository is the single
submission link for the course.

| Assignment | Deliverable | Folder |
|---|---|---|
| #3 — Build an Agent Crew | Multi-agent content pipeline (generate → deterministic validate → semantic review) that emits JSON imported into UE as DataTables | [`assignment-03-agent-crew/`](assignment-03-agent-crew/) |
| #4 — Dynamic Content Pipeline | Retrieval-augmented UI copy pipeline: BM25 over the design corpus → bilingual EN/ES generation → deterministic gate → semantic review, with retrieval accuracy measured | [`assignment-04-dynamic-content-pipeline/`](assignment-04-dynamic-content-pipeline/) |
| #5 — Goal-Oriented Coding Agent | Reads the design, scans the source, ranks what is missing with arithmetic that prints its own terms, and writes the top gap — a C++ component that compiles and the editor registers | [`assignment-05-goal-oriented-coding-agent/`](assignment-05-goal-oriented-coding-agent/) |
| #6 — Build a GER Pipeline | Generate → Evaluate → Refine over room geometry: an agent writes a RoomSpec, a deterministic gate proves the critical path is walkable, a refiner sends back the rule rather than the complaint, and a circuit breaker escalates with a diagnosis when the loop stops converging | [`assignment-06-ger-pipeline/`](assignment-06-ger-pipeline/) |
| #7 — Style Guide Agent | Generate → Evaluate → Refine over user-facing text: three constraint types read live from the game's own vault contracts, an evaluator that scores 1–10 with a reason on evidence measured in Python first, and a refiner that rewrites from that reason | [`assignment-07-style-guide-agent/`](assignment-07-style-guide-agent/) |

Engine note: assignments #3 and #4 were built against Unreal Engine 5.7.4, before
the project moved to 5.8. The pipelines are unchanged by the move; only the
editor-side tooling they hand off to differs.
