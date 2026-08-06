# Terminology & IP Guard Rules — Echoes (GDD V2)

## Shipped IP Cleanliness Mandate
The world must feel Destiny-adjacent but ship 100% legally clean in both English and Spanish. Working Destiny terms used during initial drafting are STRICTLY PROHIBITED from all shipped text, lore records, UI strings, and asset metadata.

## Banned Placeholder Terms vs Approved Universe Terms

| Banned Destiny Placeholder | Required Approved Universe Term | Context / Meaning |
|---|---|---|
| Traveler / Light | **Architects / Weave** | The ancient cosmic origin & energy |
| Ghost | **Beacon** | Architect checkpoint & respawn anchor |
| Hive / Vex / Fallen / Scorn | **Remnants / Facets** | The alien antagonist factions |
| Crota | **Warden** | Scripted 2.5-3x knight boss (reference ADN) |
| Rhulk | **Fragment** | Adaptive GOAP duelist boss (reference ADN) |
| Witch / Wizard | **La Costurera** | Main boss: alien witch commanding revived knights |
| Engram | **Architect Fragment / Data Node** | Lore node / collectible |
| Guardians | **Weavers** | The player class lore skin |

## Banned Region References

The setting is a what-if Golden Age that prospered in Mexico, and it is
**recognised, never announced** (GDD §1.2). The country is never named in shipped
text in either language, and the loaded pre-Hispanic iconography package that
"Mexican games" default to ships only from an approved-hint allowlist — which is
**empty by default**. The place is carried by geology, light, vegetation, Spanish
signage fragments and plausible toponymy instead.

These are text proxies for a rule that is partly visual: the words below are what
a text gate can catch. A legitimate use is resolved by adding the specific hint to
the allowlist, never by weakening the row. The architectural rows are the ones
most likely to need that — `pyramid` in particular is `[TUNE]`, since a ruin can
be described without invoking the iconography.

Two parsers read this table: the term guard in `validators.py`, which makes these
bind lore as well as interface text, and `ui_rules.load_region_denylist()`. Cells
therefore hold terms and nothing else — no markers, no parentheses.

| Banned Region Reference | Required Treatment |
|---|---|
| Mexico / México / Mexican / mexicano / mexicana | never named |
| Aztec / azteca / Mexica / mexica | off-allowlist iconography |
| Mayan / maya | off-allowlist iconography |
| Nahuatl / náhuatl | off-allowlist iconography |
| Quetzalcoatl / feathered serpent / serpiente emplumada | off-allowlist iconography |
| pyramid / pirámide | off-allowlist iconography |

## The ban is on the capital, not on the word

A term in the first table is banned **only in its capitalised form**, matched
case-sensitively. `Light` is the Destiny placeholder; `light` is a word, and a
world of decaying ruins needs it:

- ✅ *"The light in the corridor died long before we did."* — ordinary vocabulary.
- ❌ *"The Light of the Traveler reached this hall."* — the placeholder, twice.

The capital is the signal that the word is being used as the proper noun, so the
guard reads the capital rather than the letters. Two consequences to know:

- **At the start of a sentence the capital carries no information** — it is
  mandatory there. A sentence-opening `Light` is reported as a warning rather
  than a hard failure, and a human or the Style & IP Guard settles it. The gate
  does not guess.
- **A term written lowercase in a table stays case-insensitive**, because it has
  no proper-noun signal to lose. That is why `mexicano` and `pyramid` are caught
  in any casing, and why the region table is unaffected by this rule: a country
  name is a leak in every form.

## Enforcement
The **Style & IP Guard Agent (05)** audits all generated text payloads against this table. Any match on banned terms results in an automatic `FLAGGED` status (the agent's schema statuses are `APPROVED | FLAGGED`).

⚠️ **Known gap — the Spanish side of the first table is unguarded.** The mandate
above claims both languages, and the banned column holds English placeholders
only: `La Luz del Viajero` passes while its English equivalent fails twice.
Closing it means deciding the approved Spanish terms (`Weave` → *Tejido*?
`Beacon` → *Faro*? `Weavers` → *Tejedores*?), which is naming work. `La Costurera`
already ships in Spanish in both languages, so there is precedent either way.
