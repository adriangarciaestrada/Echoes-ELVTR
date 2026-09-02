# Art direction — PixelLab pipeline

Owns the asset pipeline decisions. Art is LAST: the loop must be fun as
coloured rectangles first (course law and ours).

- **Style:** clean flat vector illustration — geometric simplified shapes,
  bold silhouette, flat colour fills, uniform line weight, subtle paper
  grain. Chosen 2026-08-31 by side-by-side comparison against painted,
  cel-shaded and pixel-free-concept candidates on three test subjects
  (`tools/art/style-samples.md` records the procedure and the winning
  clause). Replaces the original pixel-art direction: the shipped
  "pixel art" was in practice downscaled painted concept art (see
  `tools/art/import_gemini.py`), an unresolved compromise between two
  styles. Portrait layout and the dark stone-and-thread palette are
  unchanged — the cosmology binds tone (silent, decaying, luminous
  threads). The place is recognised, never announced: no off-allowlist
  iconography in any sprite or its metadata (guard binds asset ids too).
- **Sprite sizes `[TUNE]`:** relic icons 32×32 (1 grid cell = 32px);
  enemies 32–48; bosses 96; Beacon 64.
- **Tier colours** are CELL BACKGROUNDS, not sprite recolours (reference
  pattern): White · Green · Blue · Purple · Yellow, owned by
  `relic-contract.md`. They must stay distinguishable at 32px against the
  dark board, and must not rely on hue alone (accessibility).
- **Pipeline:** PixelLab REST API, generation gated like all content —
  spec (prompt + size + palette) → generate N → deterministic checks
  (dimensions, palette conformance, transparent background) → human pick →
  import. Provenance sidecars as ever.
- **Disclosure:** itch.io AI-generated-assets checkbox is mandatory the
  moment the first PixelLab sprite ships (`capstone-requirements.md`).
