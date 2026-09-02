#!/usr/bin/env python3
"""Crop a photographic reference down to its figure and fit it to a canvas.

A reference shot is a figure adrift on a studio backdrop. Handed to the API
whole, most of the seed is empty white, which is what the generator then copies.
This trims to the subject and centres it at the target size.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

import palette


def figure_box(img: Image.Image, tol: int = 28) -> tuple[int, int, int, int]:
    """Bounding box of everything that is not the backdrop."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    back = px[2, 2]
    xs, ys = [], []
    step = max(1, min(w, h) // 400)
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b = px[x, y]
            if abs(r - back[0]) + abs(g - back[1]) + abs(b - back[2]) > tol:
                xs.append(x); ys.append(y)
    if not xs:
        return (0, 0, w, h)
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def prepare(src: Path, width: int, height: int, dest: Path, margin: float = 0.06) -> Path:
    img = Image.open(src)
    x0, y0, x1, y1 = figure_box(img)
    pad_x = int((x1 - x0) * margin), 
    px_, py_ = int((x1 - x0) * margin), int((y1 - y0) * margin)
    box = (max(0, x0 - px_), max(0, y0 - py_),
           min(img.width, x1 + px_), min(img.height, y1 + py_))
    fig = img.crop(box).convert("RGB")
    # Fit inside the canvas without distorting, on the game's own ground.
    fig.thumbnail((width, height), Image.LANCZOS)
    out = Image.new("RGB", (width, height), palette.load()["bg"])
    out.paste(fig, ((width - fig.width) // 2, (height - fig.height) // 2))
    out.save(dest)
    return dest


if __name__ == "__main__":
    src = Path(sys.argv[1])
    w, h = int(sys.argv[2]), int(sys.argv[3])
    dest = Path(sys.argv[4])
    prepare(src, w, h, dest)
    print(f"{dest} ({w}x{h}) from {src.name}")
