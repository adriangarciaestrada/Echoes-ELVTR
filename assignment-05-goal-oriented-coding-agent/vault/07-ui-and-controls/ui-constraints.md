# UI Copy Constraints — Echoes (GDD V2)

What a good string is, distilled from the pillars in `00-core/game-pillars.md`,
the HUD philosophy in `hud-and-screens.md`, and GDD §4.5 and §8.1. The shape a
screen may take is `uispec.md`; the counts it must respect are `ui-budgets.md`.
This note holds the part neither of those can: what the words are *for*.

## The thinnest layer

The UI is not a layer on top of the game. It is the thinnest possible layer *of*
the game. Every piece of information has somewhere it could live, and the screen
is the last of those places, not the first.

Before writing a string, place its information on this ladder and take the
highest rung that can carry it. The four rungs are the standard game-UI diegesis
taxonomy — Fagerholt & Lorentzon, *Beyond the HUD*, Chalmers University of
Technology, 2009, sorted on two axes: is the element part of the fiction, and is
it part of the world's geometry. The preference order below is ours.

1. **Diegetic** — in the fiction, in the world. The character perceives it. A
   Beacon that hums when it takes hold says "checkpoint" without a word.
2. **Spatial** — in the world, outside the fiction. The character does not see
   it. The `[X]` prompt beside a lever.
3. **Meta** — in the fiction, outside the world's geometry. It carries state by
   sensation rather than by display: the screen desaturating as health runs out,
   the edges of the frame reacting to a hit. **Meta feedback costs zero words**,
   which makes it this note's favourite rung after diegetic.
4. **Non-diegetic** — outside both. A pure screen overlay: the health pips, menu
   labels. **The last resort**, and anything that lands here owes an answer to:
   why could this information not live further up?

The pips are non-diegetic and stay — a run needs a countable health read. But
every *additional* health signal should be pursued on rung 3 before rung 4,
because "Minimalist Dread" is exactly what meta feedback does well.

Most of this game's information already lives on rungs 1 and 2 by design. That
is why the correct amount of text in the in-run HUD is close to none.

## The string beat: GLANCE → GRASP → ACT → TRUST

Every string is a beat, and the beat has four parts. A string missing one is
either decoration or documentation, and the slice wants neither.

- **Glance** — it is seen without being looked for. If the player has to sweep
  the screen to find it, the element is misplaced, not miswritten. Placement is
  a copy problem before it is a layout problem.
- **Grasp** — it lands in one pass. Rereading is the failure. This is a game
  read at speed, not a manual read at rest.
- **Act** — it changes a decision. A string that changes no decision is cut: it
  is not information, it is noise with a budget. "What does the player do
  differently because they read this?" has to have an answer.
- **Trust** — it tells the truth about the state of the game, every time. A
  prompt that appears when the action is unavailable costs more than a prompt
  that never appears at all.

## Glance is the budget

Text is priced in the attention it takes, not in the space it occupies. The
bands, by widget class:

- **In-run HUD element** — ~0.5 s `[TUNE]`. **Recognition, not reading.** If it
  has to be read, it does not belong in the HUD.
- **Contextual prompt** — ≤1 s `[TUNE]`. One action, one verb, no clause.
- **Menu label** — ≤2 s `[TUNE]`. List scanning; the player is comparing
  siblings, not parsing a sentence.
- **Run-Complete** — reading is allowed, and is the point. The run is over;
  nothing is competing for attention. This is the only screen where prose earns
  its place.

**Glance and dwell are different budgets, and the genre separates them
physically.** The HUD is recognised while play continues; a screen that asks to
be *inhabited* — read, compared, considered — belongs behind the pause, where
nothing competes for attention. This is the convention every metroidvania
follows, and it is why a pause screen may be wordy and a HUD may not. Never
resolve the conflict with visual hierarchy on a live screen; resolve it by moving
the information behind the pause.

The counts that implement these bands live in `ui-budgets.md`. They are budgets
on *reading cost and on whether the string changes a decision* — never on how it
is phrased. A rule that prescribes wording ("imperative mood, four words
maximum") produces uniform dead copy, which is this note's most common failure
below. Constrain the cost; leave the craft free.

## The UI never does the room's job

*Binds this agent directly.*

The visibility rule in `../04-world/room-constraints.md` requires that the
**lock** be visible in the world: the anchor above the ledge, the cracked wall
beside the chamber. The player reads the space and remembers it.

If a string explains that lock, the room's READ beat is dead and the room spent
its space for nothing. So:

- No text names a gate as class-locked, or says which class opens what. The
  geometry says it or it goes unsaid.
- No text points at a pocket, a route, or a reward. A pocket exists to be seen
  and not claimed; a label turns it into an errand.
- No text teaches a verb the movement teaches by being used. "Movement is the
  reward" is a pillar: narrating it spends the reward.

Where the world genuinely cannot speak — the locale switch, a remapped binding,
the name of a class at the moment of choosing it — the UI speaks, briefly.

## The map that is not there

*Binds this agent directly.*

The slice has **no map and no minimap** — an explicit cut (GDD §4.4), because a
map system is high-cost UI for a 15–25 minute run through two guided paths. The
map belongs to the full GDD, where the world is big enough to get lost in.

This rule is stated separately, and this emphatically, because the map is the
single most documented element of the genre. Every reference this note draws on
treats it as the centre of a metroidvania's interface — it is where progress,
the to-do list, and the memory of doors you could not open all live. Anything
writing UI copy from the genre's conventions will therefore reach for map copy
by default. It has to be refused explicitly rather than left unmentioned:

- No navigation copy of any kind: no location names as wayfinding, no "return
  here later", no completion percentage, no room counts, no distances.
- The wayfinding load sits on room geometry — the READ beat, the visibility
  rule, the camera framings. That is not a gap the UI fills; it is a
  responsibility the UI must not take.
- The one place the map's real job appears is **Run-Complete**, which names what
  this class never saw. In the genre that job is done by grey rooms and a
  percentage. Here it is done by a paragraph, and that is why this is the only
  screen where prose earns its place.

## Accessibility is a valve, not a mode

*Binds this agent directly.*

Empirical work on stripping non-diegetic interface elements — Iacovides, Cox,
Kennedy, Cairns & Jennett, *Removing the HUD*, CHI PLAY 2015 (CHI PLAY 2025
Lasting Impact Award) — found that removing them raises cognitive involvement and
sense of control **in expert players**. The effect is conditional on expertise. A
15–25 minute slice is played largely by people who have not yet learned to read
it.

So the minimalism above is a default, never a lock:

- Anything the design chose not to say must be *available*, not restored.
  Toggles live in the pause menu — §4.5 carries full input remapping, hold-vs-toggle
  for every sustained input, an effects toggle, and the no-colour-only rule; GDD §3
  puts the minimal options menu, including the locale switch, in scope. They default
  to the minimal state.
- A toggle's label states what it turns on, never that it is for players who
  need help. No copy anywhere frames accessibility as a concession.
- Aggressive minimalism without a valve is not restraint; it is exclusion. The
  reference case is the "HUD Lag" toggle in *Metroid Prime*: the most committed
  diegetic interface of its generation shipped an off switch for the part of it
  that made some players ill.

## Both languages are origin

`../05-lore/bilingual-string-tables.md` prohibits translation after the fact:
`text_en` and `text_es` are authored together, in the same payload, with
equivalent weight. This is design law, not localization hygiene — Spanish is the
place's own language, and it is the strongest hint of where the slice is set.

The 30% overflow cap is a widget constraint and is enforced arithmetically. The
part no arithmetic reaches: a line can sit inside the cap and still read as
translated. Spanish that mirrors English clause for clause has failed even when
it fits.

The region rule from GDD §1.2 binds every shipped string: **the country is never
named**, in either language, and no pre-Hispanic reference ships outside the
approved-hint allowlist (default: none). The place is recognised, never
announced.

## Screens have jobs

Four screens, from `hud-and-screens.md`. Each has one job, and copy that serves a
different job is wrong even when it is well written.

- **`HUD_Main`** — *sustain the run without interrupting it.* Pips, the Titan
  energy meter, contextual prompts, the keycard state after Boss 1. Nothing from
  the excluded list: no boss health bar, no minimap, no ammo, no damage numbers.
  Their absence is the design, so no string may substitute for one — a line that
  narrates the boss weakening is a health bar made of words.
- **Class Select** — *make the choice feel consequential before it can be
  understood.* It previews two fantasies, agility and force. It does not compare
  stats, rank the classes, or hint which is easier: "asymmetry budgets
  difficulty, never possibility" has to survive first contact.
- **Pause** — *let the player leave and come back, and change what needs
  changing.* Input remap, accessibility toggles, locale switch, exit run. Plain
  where plain is correct — a pause menu with voice in it is a pause menu getting
  in the way. Nothing here offers difficulty: the slice has none, and a label
  implying one promises a system that does not exist.
- **Run-Complete** — *sell the second run.* It names what this class never saw:
  the branch it could not enter, the pockets it could not claim. This screen
  carries the replay hook of the entire slice in a paragraph, and it is the one
  place where the writing is doing narrative work rather than staying out of the
  way. Death is a soft loss (checkpoint respawn, world state intact); the run
  ending is not a defeat to dramatise or a score to grade.

## Consistency is a property of the set

A string can be right on its own and the table still be broken. Room specs are
checked across a batch because a set of rooms fails by being **too similar**; a
set of strings fails by being **inconsistent**. Same mechanism, opposite sign.

Across the whole string table:

- One concept, one name. A Beacon is a Beacon on every screen — never a
  "checkpoint" here and a "Beacon" there. `../00-core/terminology-guard.md` is
  the authority, and it binds prompts and labels exactly as it binds lore.
- Prompts hold one grammatical mood. Mixed moods read as mixed authorship.
- Two keys with identical text mean one key is redundant, or a distinction was
  meant and got lost. Both are defects.
- A button is named the way the control scheme names it. Gamepad first, keyboard
  as fallback, and no string implies mouse aiming — there is none.

## What makes copy fail review

Ranked by how often it happens, not by how bad it is:

1. **It is software copy.** "Settings". "Are you sure you want to quit?". "Press
   A to continue". Correct, clear, and it could belong to any game ever shipped.
   This is the most common failure by a wide margin, and no rule engine catches
   it.
2. **It explains the mechanic instead of naming the moment.** A tooltip teaching
   dodge i-frames in a game whose pillar is that movement teaches itself. The
   test is GRASP versus documentation: name what is happening, do not specify
   how it works.
3. **It promises something the slice cut.** Difficulty, map completion, ammo,
   damage numbers, a boss health bar. Checked deterministically against the
   excluded list and the cut-feature denylist — and still worth ranking here,
   because the pull toward writing it is constant.
4. **The Spanish is a translation, not an origin.** It passes the overflow cap
   and reads as English wearing Spanish. The hardest finding to raise and the
   one that decides whether §8.1 is a feature or a checkbox.
5. **It names what the world should show.** The subordination rule above. The
   copy is fine; it is doing another discipline's job, and the room paid for it.

## Related

- `uispec.md` — the format, the key grammar, and what the gate enforces.
- `ui-budgets.md` — character counts, the overflow ratio, safe area.
- `hud-and-screens.md` — HUD philosophy, the excluded elements, the screen roster.
- `control-scheme.md` — gamepad-first input; how a button is named.
- `../05-lore/bilingual-string-tables.md` — the EN/ES origin rule and the seam.
- `../00-core/terminology-guard.md` — the single source of approved terms.
- `../04-world/room-constraints.md` — the visibility rule this note is subordinate to.
