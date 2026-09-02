/**
 * Palette and layout constants. Art direction: dark stone and thread, tier
 * colour lives in the CELL BACKGROUND, never in the sprite (art-direction.md).
 */
export const W = 1280;
export const H = 720;

/** Three panels: arsenal | play | weave (ui-and-strings.md). */
export const PANEL = {
  left:   { x: 0,    w: 320 },
  centre: { x: 320,  w: 640 },
  right:  { x: 960,  w: 320 },
} as const;

export const C = {
  bg:        0x0b0d12,
  panel:     0x141822,
  panelEdge: 0x232a38,
  lane:      0x10141d,
  text:      "#c8d0e0",
  dim:       "#7b8698",
  accent:    "#8fd3c7",
  beacon:    0x8fd3c7,
  danger:    0xd8556b,
  gold:      "#e0c070",
  exp:       0x6ea8d8,
} as const;

/** Numeric twins of the string colours, for Graphics calls. */
export const CN = { accent: 0x8fd3c7, gold: 0xd8b23c, dim: 0x7b8698 } as const;

/**
 * The flat-vector UI language (decision: tools/art/style-samples.md). Drawn
 * chrome only — near-black linework at one uniform weight, corner cuts
 * echoing fitted stone blocks, the luminous thread as the single glow.
 * ui.ts consumes these; scenes take widgets from ui.ts, not raw rects.
 */
export const UI = {
  line: 2,              // the cards' outline weight; 1px reads as unstyled
  cut: 12,              // default corner cut on a block
  outline: 0x070a10,
  raised: 0x1a2130,     // stone face at rest
  raisedHi: 0x232c3e,   // stone face under the pointer
  well: 0x0f131c,       // sunken face (name strips, insets)
  edgeLight: 0x36425a,  // the top edge catches the light
  thread: 0x8fd3c7,
  hover: 0xe0c060,
} as const;

/**
 * Typography. One family everywhere — Chakra Petch, chosen from a rendered
 * side-by-side against Rajdhani and Teko; monospace stays the fallback (and,
 * for now, the in-run screens). display/body are kept as separate tokens so
 * a future split costs one line here, not a sweep of the scenes.
 */
export const F = {
  display: '"Chakra Petch", monospace',
  body: '"Chakra Petch", monospace',
} as const;

/** Tier backgrounds: White, Green, Blue, Purple, Yellow (relic-contract.md). */
export const TIER_BG = [0x9aa3b2, 0x4f9d5d, 0x3f7fc4, 0x8a56c8, 0xd8b23c] as const;

export const CATEGORY_MARK = { Bolt: 0xe08a5a, Burst: 0xd8556b, Construct: 0x6ea8d8 } as const;
