# Spanish glossary — the law for `es` text

The terminology guard fixes the game's nouns in English only. Nothing fixed
their Spanish, so every generation translated the same term again from scratch
and the results disagreed: `Bolt` shipped as both *rayo* and *perno*, `Loom` and
`Weave` collapsed into one word, and `Nivel` served both `Tier` and `Level` on
screens the player sees at the same time. The checker passed all 106 strings —
it measured length, placeholders and region references, never consistency.

This file is that missing half. It is machine-read: `agents/glossary.py` parses
the tables below and enforces both directions — one English term has exactly one
Spanish word, and one Spanish word serves exactly one English term.

Where a cell reads `Oleada / OLA`, the first form is canonical and the rest are
accepted; the short ones exist because the HUD has no room for the long ones.

Variant: **neutral Latin American Spanish** (*haz clic*, *presiona*, *empaca*).
Not es-ES (*pulsa*). Pick one and stay in it.

## Fiction

| en | es | note |
|---|---|---|
| Loom | Telar | the apparatus; the game's title translates |
| Weave | Tejido | what comes off the loom |
| weave / woven (verb, merging twins) | tejer | |
| Weaver | Tejedor | masculine, to agree with the three class names |
| Beacon | Faro | |
| Best | Mejor | |
| Remnant | Remanente | |
| Architects | Arquitectos | |

## Categories

| en | es | note |
|---|---|---|
| Bolt | Rayo | not *perno*, which is a bolt of hardware |
| Burst | Estallido | not *ráfaga*, which is gunfire — that is what Bolt does |
| Construct | Constructo | not *construcción*, which is the act of building |

## Stats and progression

| en | es | note |
|---|---|---|
| range / reach | alcance | never *rango* |
| damage | daño / DÑ | |
| cooldown | recarga / REC | |
| Tier | Rareza | its values are rarities, not levels |
| Level | Nivel / NV | sole owner of the word |
| wave | Oleada / OLA | the short form is for the HUD |
| run | partida | **never *ronda*** — a *ronda* is a wave, and gold does carry across waves |
| depth | profundidad | |

## Rarities

| en | es |
|---|---|
| Common | Común |
| Uncommon | Poco común |
| Rare | Raro |
| Epic | Épico |
| Legendary | Legendario |

## Economy and actions

| en | es | note |
|---|---|---|
| Reroll | Renovar | not *barajar*, which belongs to cards and collides with shuffle |
| Shuffle | Reordenar | |
| buff | buff | deliberate loan word; standard in Spanish games and leaves *mejora* free |
| upgrade | Mejora | |
| Repair | Reparar | |
| Mend | Remendar | keeps the textile metaphor and stays distinct from Repair |
| Banish | Desterrar | |
| Take | Tomar | |
| scrap | desechar | |
| set aside | apartar | |
| tray | bandeja | never *bandeja de reserva* — one name |
| cell | celda | |
| lane | carril | |
| twin | gemela | |
| relic | reliquia | |
| Ultimate | Definitiva | a feminine **noun**, not an adjective |

## Two writing rules the glossary cannot express

**Do not juxtapose two nouns.** `Bolt damage` is English grammar. Spanish needs a
preposition or a colon, so stat lines take the form **`Sujeto: efecto`**:

    Rayo: daño +25%          not  Daño Rayo +25%
    Definitiva: recarga -18%  not  Recarga Definitiva -18%

This also front-loads the category, which is the one thing a buff's fantasy name
(*Hilo Tenso*) refuses to tell the player.

**Names are exempt from the forward rule.** `relic.*.name`, `buff.*.label`,
`class.*.label` and `ult.*.label` are invented names, not translations: *Shock
Burst* may become *Choque Explosivo* without owing the glossary its category
word. Their descriptions may not. The reverse rule still applies to them — a
name may not steal a word another concept owns.

**Spanish does not Title Case.** Capitalise relic and buff names as proper nouns;
leave descriptive text in sentence case.
