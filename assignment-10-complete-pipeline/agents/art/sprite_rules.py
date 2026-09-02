#!/usr/bin/env python3
"""The countable half of "does this sprite ship?".

Everything here is measured before a human looks at anything, so the pick is
made from candidates that already fit the board rather than from whichever one
looks nicest in isolation. A sprite that is beautiful and 40x33 with an opaque
background is not a candidate, and no amount of taste fixes that.

What is NOT here: whether it reads as the relic it depicts, whether it looks
like this world, whether it is legible at 32px on a dark board. No check reaches
those, which is exactly why a person picks from the survivors.

Source: `loom-vault/art-direction.md`.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from PIL import Image

import palette

RGB = Tuple[int, int, int]

# A sprite may sit this far from the nearest palette colour, averaged over its
# opaque pixels, in plain RGB distance. Generation is guided toward the palette
# rather than clamped to it, so this allows shading the palette does not name
# while refusing a sprite in some other scheme entirely. [TUNE]
PALETTE_TOLERANCE = 60.0

# Pixel art with hundreds of colours is a photo that happens to be small. [TUNE]
MAX_COLOURS = 32

# Below this, the sprite is mostly empty and will read as a speck. [TUNE]
MIN_COVERAGE = 0.10
# Above this, nothing was cut out and the "transparent background" did not happen.
MAX_COVERAGE = 0.92


def _nearest(colour: RGB, allowed: List[RGB]) -> float:
    r, g, b = colour
    return min(((r - ar) ** 2 + (g - ag) ** 2 + (b - ab) ** 2) ** 0.5
               for ar, ag, ab in allowed)


def check(path: Path, width: int, height: int,
          allowed: List[RGB] | None = None, cutout: bool = True) -> List[str]:
    """Every measurable fault in one sprite, as sentences.

    `cutout=False` for the character cards. They are illustrations with their
    own background, not tokens laid on the board, so the rules that demand a
    silhouette — the coverage ceiling and the opaque-border test — do not apply
    to them. The size and palette rules still do.
    """
    allowed = palette.sprite_palette() if allowed is None else allowed
    findings: List[str] = []
    img = Image.open(path).convert("RGBA")

    if img.size != (width, height):
        findings.append(f"is {img.width}x{img.height}, not the {width}x{height} "
                        f"the grid is built on")
        return findings                      # everything below assumes the size

    pixels = list(img.getdata())
    opaque = [(r, g, b) for r, g, b, a in pixels if a > 200]
    coverage = len(opaque) / len(pixels)

    if coverage < MIN_COVERAGE:
        findings.append(f"only {coverage:.0%} of it is opaque — it will read as a "
                        f"speck at this size")
    elif cutout and coverage > MAX_COVERAGE:
        findings.append(f"{coverage:.0%} of it is opaque: the background was never "
                        f"cut out, and it will sit on the board as a rectangle")

    # The border is the honest test for a transparent background: a sprite that
    # fills its own frame has no silhouette, whatever the mean alpha says.
    border = ([pixels[x] for x in range(width)] +
              [pixels[(height - 1) * width + x] for x in range(width)] +
              [pixels[y * width] for y in range(height)] +
              [pixels[y * width + width - 1] for y in range(height)])
    opaque_border = sum(1 for _r, _g, _b, a in border if a > 200) / len(border)
    if cutout and opaque_border > 0.25:
        findings.append(f"{opaque_border:.0%} of its border is opaque — it is "
                        f"framed, not cut out")

    if not opaque:
        findings.append("is entirely transparent")
        return findings

    unique = len(set(opaque))
    if unique > MAX_COLOURS:
        findings.append(f"uses {unique} colours against a ceiling of {MAX_COLOURS} "
                        f"— this is a small photo, not pixel art")

    drift = sum(_nearest(c, allowed) for c in opaque) / len(opaque)
    if drift > PALETTE_TOLERANCE:
        findings.append(f"sits {drift:.0f} from the game's palette on average, "
                        f"past the {PALETTE_TOLERANCE:.0f} allowance — it belongs "
                        f"to some other game's colour scheme")

    return findings


def report(path: Path, width: int, height: int) -> dict:
    findings = check(path, width, height)
    return {"file": path.name, "ok": not findings, "findings": findings}
