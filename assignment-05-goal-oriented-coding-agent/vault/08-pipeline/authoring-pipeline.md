# Authoring Pipeline — the contract

How generated content reaches the project. This note is normative: it says what
must happen and who may do it. The mechanics of individual tools live in
`08-pipeline/editor-tooling.md`, so that a tool change does not invalidate a rule.

## The four stages

**Generate → Validate → Review → Import.**

| Stage | Who | Produces |
| --- | --- | --- |
| Generate | An authoring agent, against an injected contract | A candidate artifact (JSON) |
| Validate | Deterministic Python, no model | A pass/fail report with named rule codes |
| Review | A reviewer agent that never generated the artifact | Findings a rule engine cannot compute |
| Import | Gated Python + the editor bridge | Assets and actors in the project |

Two properties hold across every content type:

- **The generator is never the evaluator.** A reviewer agent judges only artifacts
  it did not produce. Self-checks are permitted only against measurable rule sets,
  and independent judgment remains the exit gate.
- **Deterministic checks run before any reviewer agent.** Anything arithmetic —
  reach, budgets, exclusivity, grid alignment, character counts — is settled by
  Python first, so no model is paid to raise a question already answered.

## The two paths

**Content with a spec** — rooms, text, tuning tables, UI layouts — enters only
through the gated path. It requires a provenance record showing that the
deterministic gate passed, a review happened, a human approved, and the
artifact's hash still matches what was approved.

**Editor plumbing without a spec** — creating a folder, opening a level, moving
the viewport camera, compiling a Blueprint, taking a screenshot — is free for
agents, because there is nothing to approve and a mistake is visible and cheap.

A gate failure is never overridable. Review findings may be overridden with a
recorded note.

## Three execution layers

The bridge cannot run project Python (see `editor-tooling.md`). The pipeline is
therefore split by what each layer is physically able to do:

**Layer A — outside the editor.** Generation, the deterministic gate, provenance,
and geometry planning. Ordinary Python with no engine dependency, runnable and
testable without the editor open. This is where authority lives.

**Layer B — the bridge.** Layer A emits a tool script; the bridge executes it in
one call. The script is *emitted by the deterministic tool*, never authored by an
agent — that is what keeps the gate meaningful. An agent that could write the
import script directly would be an agent that could bypass every rule above.

**Layer C — the editor console.** Only for operations no registered tool exposes.
This layer should shrink over time; every item in it is a manual step in an
otherwise automated loop, and manual steps are where approval discipline decays.

## Rules that follow

- **A room's plan is computed before anything is spawned.** A spec that fails
  halfway must not leave half a room behind.
- **Imports are idempotent.** Re-importing after an edit leaves one artifact, not
  a merge of two. Generated actors carry a `GEN_<id>_` prefix so a re-run can
  clear its own output and nothing else.
- **User-facing text is never a literal.** Text properties are bound to a String
  Table key, not assigned a string. The binding is verifiable by reading the
  property back; a literal and a binding are distinguishable in export text.
- **Verify what landed, not what was sent.** An asset existing is not the same as
  an asset holding the rows the artifact carried. Every importer reads back.
- **Read design-time and run-time values from different places.** A Blueprint's
  defaults live on its class default object; a live actor's values do not. Reading
  the wrong one returns a plausible number that answers a different question.

## Model routing

Route by what the task can be checked against, not by how important it feels.

| Task | Tier |
| --- | --- |
| Mechanical, systematic, verifiable by diff (inventories, dumps, transcription) | Cheapest available |
| Bounded rule-following against an injected contract (reviewers) | Small |
| Design judgment, contract authoring, root-cause work | Largest available |

Before a fan-out run, declare the token budget and state what the run must return
to be worth it. Charge shared context once by pre-digesting it into the prompt
rather than letting each agent rediscover it.

Work that a script can do is not delegated to a model at all. The toolset
inventory of 2026-08-09 is the reference case: the dump was a shell loop costing
nothing, and only the reading of it was worth a model.
