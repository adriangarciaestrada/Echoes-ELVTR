#!/usr/bin/env python3
"""Repair a sprite whose figure was eaten by the background cut.

`cutout.py` floods from the border and stops at any pixel outside its tolerance.
That holds for flat pixel-art fields. It does not hold for a JPEG source: lossy
compression scatters the background into hundreds of near-shades, and where the
figure's own colour sits inside the tolerance the flood walks straight through
the silhouette and hollows the body out. Two of the three Weavers arrived that
way — the titan reduced to 61% of its pixels in 61 disconnected shards.

The cut overwrote colour as well as alpha, so the eaten pixels are unrecoverable.
What survives is the outline, and that is enough to rebuild from:

  1. close the breaks in the outline, so the body is an enclosed region again
  2. keep the largest blob, so specks of leftover background do not become body
  3. fill it, and colour each recovered pixel from its nearest surviving
     neighbour — the armour reads as large flat plates, so nearest-neighbour
     keeps plate colours instead of smearing a gradient across them

This is reconstruction, not restoration: the result is the silhouette the artist
drew filled with the colours that survived beside it. Provenance records say so.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

# Bridges the widest gap the flood tore in an outline without welding a limb to
# the torso. Measured on the titan, the worst of the three. [TUNE]
CLOSE = 4


def damage(mask: np.ndarray) -> tuple[int, float]:
    """Pieces the opaque region is in, and the share held by the largest."""
    lab, k = ndimage.label(mask, structure=np.ones((3, 3), bool))
    if k == 0:
        return 0, 0.0
    sizes = np.bincount(lab.ravel())[1:]
    return k, float(sizes.max() / mask.sum())


def looks_eaten(mask: np.ndarray) -> bool:
    """A cut that ate the figure leaves the outline in many shards."""
    pieces, biggest = damage(mask)
    return pieces > 12 or biggest < 0.75


def repair(path: Path) -> tuple[int, int]:
    """Rebuild the figure in place. Returns (before, after) opaque counts."""
    a = np.array(Image.open(path).convert("RGBA"))
    rgb, mask = a[..., :3], a[..., 3] > 0
    before = int(mask.sum())

    closed = ndimage.binary_closing(mask, structure=np.ones((CLOSE, CLOSE), bool))
    filled = ndimage.binary_fill_holes(closed)
    lab, k = ndimage.label(filled)
    body = filled if k == 0 else (lab == int(np.bincount(lab.ravel())[1:].argmax() + 1))

    _, idx = ndimage.distance_transform_edt(~mask, return_indices=True)
    out = rgb.copy()
    new = body & ~mask
    out[new] = rgb[idx[0][new], idx[1][new]]

    res = np.dstack([out, np.where(body, 255, 0)]).astype(np.uint8)
    Image.fromarray(res, "RGBA").save(path)
    return before, int(body.sum())


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        p = Path(arg)
        m = np.array(Image.open(p).convert("RGBA"))[..., 3] > 0
        pieces, biggest = damage(m)
        if not looks_eaten(m):
            print(f"{p.name}: intact ({pieces} piece(s), largest {biggest:.0%}) — skipped")
            continue
        b, aft = repair(p)
        m2 = np.array(Image.open(p).convert("RGBA"))[..., 3] > 0
        p2, big2 = damage(m2)
        print(f"{p.name}: {b} -> {aft} opaque px, {pieces} -> {p2} piece(s), "
              f"largest {biggest:.0%} -> {big2:.0%}")
