#!/usr/bin/env python3
"""Cut a flat background away from a generated sprite.

`no_background: true` is a request, not a guarantee: pixflux returned the first
character card on a solid grey field, fully opaque. Asking again is not a fix, so
the background is removed here instead — deterministically, and only when it is
genuinely flat.

Flood fill from the border, never a global colour match. A colour that also
appears inside the figure — the same grey in a visor, say — is only erased where
it connects to the edge, so the character keeps its own pixels.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image
from scipy import ndimage

# How far a pixel may sit from the corner colour and still count as background.
# Pixel art fields are flat; this allows for mild dithering and no more. [TUNE]
TOLERANCE = 26


def _close(a: Tuple[int, ...], b: Tuple[int, ...], tol: int) -> bool:
    return sum(abs(x - y) for x, y in zip(a[:3], b[:3])) <= tol


def looks_framed(img: Image.Image) -> bool:
    """Is there a flat field touching every corner worth cutting?"""
    w, h = img.size
    px = img.load()
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    return all(_close(corners[0], c, TOLERANCE) for c in corners[1:])


def cut(path: Path, tolerance: int = TOLERANCE) -> int:
    """Erase the border-connected background in place. Returns pixels cleared."""
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    px = img.load()
    target = px[0, 0]

    seen = bytearray(w * h)
    queue: deque = deque()
    for x in range(w):
        for y in (0, h - 1):
            queue.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            queue.append((x, y))

    cleared = 0
    while queue:
        x, y = queue.popleft()
        if not (0 <= x < w and 0 <= y < h) or seen[y * w + x]:
            continue
        seen[y * w + x] = 1
        if not _close(px[x, y], target, tolerance):
            continue
        px[x, y] = (0, 0, 0, 0)
        cleared += 1
        queue.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    # Did the flood eat the figure? On a flat field it stops at the silhouette
    # and what remains is one solid blob. On a JPEG source the background is
    # scattered into hundreds of near-shades, and wherever the figure's own
    # colour falls inside the tolerance the flood walks through the outline and
    # hollows the body out — leaving the outline in shards. That is exactly how
    # two of the three Weavers shipped, and nothing here noticed. It refuses now
    # rather than saving a hollow sprite that only looks right on a dark page.
    mask = np.array(img)[..., 3] > 0
    if mask.any():
        lab, pieces = ndimage.label(mask, structure=np.ones((3, 3), bool))
        biggest = np.bincount(lab.ravel())[1:].max() / mask.sum()
        if pieces > 12 or biggest < 0.75:
            raise ValueError(
                f"{path.name}: the cut shredded the figure into {pieces} pieces "
                f"(largest holds {biggest:.0%}). The source is probably lossy — "
                f"a JPEG background is not flat. Re-export it as PNG, or lower "
                f"the tolerance below {tolerance}. Not saved.")

    img.save(path)
    return cleared


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        p = Path(arg)
        n = cut(p)
        print(f"{p.name}: {n} px cleared ({n / (Image.open(p).width * Image.open(p).height):.0%})")
