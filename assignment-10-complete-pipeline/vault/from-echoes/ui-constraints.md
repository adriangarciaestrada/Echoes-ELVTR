> **Forked 2026-08-21** from the Echoes vault, then reduced to what binds
> this game. Metroidvania-specific law was removed as noise. The original
> governs the metroidvania alone.

# UI constraints — the design law

This note owns *how* text and interface behave. This game's screens, panels
and caps are owned by `../ui-and-strings.md`.

## The thinnest layer

The interface is the thinnest layer that lets the player act. Anything it
shows must earn its place against the thing it covers.

## The string beat: GLANCE → GRASP → ACT → TRUST

Every string is a beat with four parts. A string missing one is either
decoration or documentation, and this game wants neither.

- **Glance** — it is seen without being looked for. If the player has to
  sweep the screen for it, the element is misplaced, not miswritten.
- **Grasp** — it lands in one pass. **Rereading is the failure.** This is
  read at speed, not at rest.
- **Act** — it changes a decision. *"What does the player do differently
  because they read this?"* must have an answer. A string that changes no
  decision is cut: it is not information, it is noise with a budget.
- **Trust** — it tells the truth about the state of the game, every time. A
  prompt that appears when the action is unavailable costs more than a
  prompt that never appears.

## Screens have jobs

Each screen has one job, and copy that serves a different job is wrong even
when it is well written. Plain where plain is correct — an interface with
voice in it, where the player is making a practical decision, is an
interface getting in the way.

## Both languages are origin

Authored in English and Spanish, never translated. Spanish decides fit.

## What makes copy fail review

Ranked by how often it happens:

1. **It is software copy.** "Settings". "Are you sure you want to quit?".
   Correct, clear, and it could belong to any game ever shipped. The most
   common failure by a wide margin, and no rule engine catches it.
2. **It explains the mechanic instead of naming the moment.** Name what is
   happening; do not specify how it works.
3. **It promises something the game does not have.** Checked against the
   cut-feature list.
4. **The Spanish is a translation, not an origin.** It passes the cap and
   reads as English wearing Spanish.
5. **It is doing another discipline's job** — narrating what the screen
   already shows.
