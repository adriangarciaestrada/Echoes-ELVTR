# Echoes — Goal-Oriented Coding Agent

**ELVTR "Multi-Agent AI for Game Development" — Assignment #5.**

An agent that reads the design documents of **Echoes** — a 2.5D sci-fi metroidvania
in Unreal Engine 5.8 — scans the project's own source tree, works out which
described systems do not exist yet, ranks them, and writes the one that should be
built first.

It runs on personal subscriptions through headless CLIs. No API keys, no paid
endpoints.

```bash
python3 agents/goal_coder.py --plan-only      # read, scan, rank; build nothing
python3 agents/goal_coder.py                  # …and write the top feature
python3 agents/goal_coder.py --refresh        # re-read the design instead of the cache
```

Stages 1 and 5 call a model; 2, 3 and 4 do not. The design reading is cached to
`production/output/goal_coder_features.json`, so `--plan-only` re-runs the whole
reasoning layer offline and reproduces the ranking below exactly.

The game repository travels with this submission as far as it usefully can: the
source trees the scan reads are included under `scanned/`, and the names of the
project's 91 binary assets as a manifest, since `.uasset` files cannot ship.
Without that manifest every piece of content the design describes would read as
missing.

---

## The shape of it

Five stages, and the division of labour between them is the design decision worth
defending:

| | Stage | Who does it |
|---|---|---|
| 1 | Read the design | **a model** — a GDD is prose |
| 2 | Scan the code | deterministic — a symbol either exists or it does not |
| 3 | Detect gaps | deterministic |
| 4 | **Prioritise** | **deterministic, and it prints its arithmetic** |
| 5 | Write the feature | **a model** — code is prose too |

Only the ends are model work. The reasoning in the middle can be read, argued
with, and re-run without spending a token. A ranking produced by asking a model
*"what should I build first?"* cannot be checked by anyone, including the model
that produced it.

The cost of that choice is visible in the run: re-ranking after a rule change
takes under a second, because only the two ends are calls.

---

## What it decided, and why

```
63 features declared   ·   31 source files, 91 assets scanned
35 of 63 are missing

note: boss_goap_blackboard and enemy_stats_datatable tie at 13;
      broken toward the layer a compiler can check

[13] boss_goap_blackboard — shared GOAP perception blackboard
       +3  the scoped GDD requires it for the slice
       +10 blocks boss_la_costurera_witch, boss_revived_knights,
           boss_goap_witch_brain, boss_goap_knight_brain,
           boss_revive_weave_mechanic
       -0  lands in cpp

[13] enemy_stats_datatable — DT_EnemyStats (TTK tiers, HP per archetype)
       +3  the scoped GDD requires it for the slice
       +12 blocks six enemy and encounter features
       -2  lands in asset
```

### The scoring signals

They are not invented for the exercise. Each one is something this project has
already paid for.

**`+4` already referenced.** Something in the repository writes or reads this
feature's data while nothing implements the behaviour. That is not a missing
feature — it is a promise being broken right now. The room contract declares
`is_one_way` on platforms; the importer tags the actor and no collision code has
ever honoured it, which was discovered by a human walking into a platform that
should have let them through.

**`+3` observed failure.** There is recorded evidence it has already caused a
defect. Read out of the design notes rather than asserted: a warning written into
a contract is the record of something that went wrong.

**`+3` on the slice path.** The scoped GDD lists it as required for the
deliverable rather than the long-term vision.

**`+2` per dependent, `−5` if itself blocked.** Ordering, not importance.

**`−cost` by layer.** C++ and Python are cheapest because a compiler and a diff
can check them; an asset is dearest because only a human eye can. This is the
repository's own routing rule, not a preference introduced here.

### Why the tie broke that way

Two features scored 13. Breaking that by list order would make the top of a build
list depend on the order a model happened to emit its features in, so the tie
goes to the layer whose result a compiler can verify. The blackboard is C++; the
DataTable is an asset.

---

## What it built

`UGoapBlackboardComponent` — the shared perception state La Costurera's squad
plans against, in three files under `Source/Echoes/`.

The design describes one boss encounter with three planning brains: the Witch and
two Revived Knights. Every brain scores its goals against the same facts — which
class the player picked, whether the Titan's shield is up, how far the revive
weave has progressed, whether each Knight is down. The GDD names seven blackboard
keys. None of them existed in code.

The agent implemented all seven rather than only the four it had listed as
evidence, on the grounds that the three it added are required by the same feature
and by everything downstream of it. It mirrored the module's existing
`FGameFeelRow` / `UGameFeelComponent` split — plain-data `USTRUCT` plus a thin
component that owns one instance — and kept the design document's key names
verbatim, including booleans without Unreal's usual `b` prefix, so that the
document and the header stay comparable by eye.

---

## Was it run in the game?

Yes, and the check went further than "it compiles", because compiling is a weak
claim about Unreal code: reflection macros can be syntactically fine and still
produce a class the engine never registers.

**It built, first attempt, no edits.**

```
[1/4] Compile GoapBlackboardComponent.cpp
Result: Succeeded
```

Unreal Header Tool accepted the reflection and emitted
`GoapBlackboardComponent.generated.h`, `GoapBlackboardTypes.generated.h` and both
`.gen.cpp` files, so the `UCLASS`, `USTRUCT` and `UENUM` declarations are valid
and not merely compilable C++.

**The editor loaded it and offers it.** Queried against the running editor, the
class is registered and addable to any actor:

```
/Script/Echoes.GoapBlackboardComponent
  category "Echoes" · base ActorComponent · display name "Goap Blackboard Component"
```

**Every field survived reflection**, which is the part a compile does not prove.
Read back from the class default object:

```
playerClass · hunterDodgeHabitScore · titanShieldActive · witchVulnerable
knight1State · knight2State · reviveWeaveProgress
enums: Hunter · Titan · Active · Weaving · Downed
```

All seven blackboard keys the design document names, and both enumerations.

**Re-running closes the loop.** With the component in the tree, the same command
no longer lists it, and `enemy_stats_datatable` takes the top of the ranking. The
agent is not remembering what it did — it is finding the same evidence a reader
would, in the source it has just written.

Run from this submission rather than from the live repository, that second pass
reports 29 source files and 30 of 63 features missing. The counts differ by a
little from the figures above because what travels here is a snapshot of the
trees the scan reads, not the working repository; the ranking and the decision
are the same.

What has **not** happened: nothing consumes it yet. The Witch and the Knights are
themselves unbuilt — they are the features this one unblocks, which is why it
ranked above them. The component is real, loaded and reflected; the encounter
that will read it is the next entry on the same list.

---

## What the agent gets wrong

Stated because a gap-finder that is trusted blindly is worse than none.

**The reader names evidence from memory, and sometimes misnames it.** It asked
whether `03-level-designer.md` existed when the crew numbers that file `01`, and
reported the feature missing. The scanner now compares the descriptive part of a
filename and ignores the ordinal, but the general problem stands: the model
proposes what would prove a feature exists, and it can propose the wrong thing.

**A first version searched only source text.** It reported Enhanced Input as
missing while five Input Action assets sat in the project, and the room importer
as missing while two files implemented it. A design document names things that
live in three different places — a class in source, an asset in the content tree,
a script by its filename — and evidence has to be looked for in all three.

**Mentions are not implementations, and the test for that is crude.** A symbol on
a line beginning with a comment marker counts as a mention; anything else counts
as built. That is enough to separate a contract that describes a field from code
that acts on it, which is the distinction the ranking depends on, but it would
miscount a symbol inside a multi-line string.
