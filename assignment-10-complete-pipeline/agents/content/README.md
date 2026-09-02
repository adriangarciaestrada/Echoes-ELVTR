# Content pipeline — retrieve, generate, gate, review

The retrieval-grounded bilingual UI copy pipeline this game's strings were
originally approved through (see `strings.generated.ts`'s header) had four
stages. The generator and reviewer never made it into this repo when Loom
was split out of the ELVTR course monorepo — only their approved output
did. This folder rebuilds all four.

```bash
python3 retriever.py --query "what a market reroll button should say" --k 3
python3 retriever.py --stats

python3 gate.py --key "buff.cd_bolt.label" --en "Quick Shuttle" --es "Lanzadera Rapida"
python3 gate.py --check-generated   # validates all 109 already-approved records — 0 errors

python3 pipeline.py --key "buff.hold_warden.label" --widget-class BuffLabel \
    --brief "a buff that makes the Warden's Knot ultimate grind longer before releasing" \
    --out demo_test
```

## The pipeline

```
retriever.py (BM25 over loom-vault)
   -> writer.py: pinned law (terminology-guard, architects-cosmology,
      ui-and-strings) + retrieved fact -> Sonnet writes one bilingual
      StringRecord, citing which chunk each part came from
   -> gate.py: deterministic — caps, placeholder parity, banned terms
      FAIL -> stop here. The reviewer never runs on illegal content.
   -> reviewer.py: Haiku judges what arithmetic can't — software voice,
      Spanish that reads as translated, whether the record does the
      screen's job — reading the gate's own report so it never
      recomputes what already ran
```

`ai_call.py` (`../ai_call.py`, shared with `tools/lore/`) is the `claude`
CLI headless wrapper both the writer and reviewer call through.

## What a real run found

The first real end-to-end run (`output/demo_test.*`) — a hypothetical
Warden buff, "the knot grinds longer before it breaks" — passed the gate
clean (no cap or placeholder violations) and the reviewer still flagged it
`REVISE`: the English describes a *duration* effect ("grinds longer"), the
Spanish drifted to an *intensity* effect ("aprieta más" — squeezes harder).
Not a translation-register problem — a genuinely different mechanic
described in each language, invisible to a gate that only checks length and
placeholder tokens. Exactly the class of bug the reviewer layer exists for.

## Where the mapping is a reconstruction, not a recovered artifact

`gate.py`'s key-to-widget-class table is rebuilt from this repo's own key
naming, not recovered from the lost generator. Checked against the actual
109 already-approved records before being trusted: a first pass mapped
every `ui.*` key to the tightest cap and failed 41 of them — its bug, not a
defect in already-shipped content. Corrected, re-checked: 0 errors.
