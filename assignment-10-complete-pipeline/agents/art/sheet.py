#!/usr/bin/env python3
"""A contact sheet of candidates, for the human pick.

Numbered, on the board's own background, at the size they will be seen. Judging
sprites in a file browser at whatever zoom it feels like is how a sprite that
does not read at 32px gets chosen.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

import palette

OUT = Path(__file__).parent / "candidates"
BG = palette.load()["bg"]


def sheet(paths: list[Path], scale: int = 1, pad: int = 16) -> Path:
    imgs = [Image.open(p).convert("RGBA") for p in paths]
    if scale != 1:
        imgs = [im.resize((im.width * scale, im.height * scale), Image.NEAREST) for im in imgs]
    w = sum(im.width for im in imgs) + pad * (len(imgs) + 1)
    h = max(im.height for im in imgs) + pad * 2 + 18
    out = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(out)
    x = pad
    for i, im in enumerate(imgs):
        out.paste(im, (x, pad + 18), im)
        draw.text((x + 4, 4), f"[{i}]", fill=(200, 208, 224))
        x += im.width + pad
    dest = OUT / "sheet.png"
    out.save(dest)
    return dest


if __name__ == "__main__":
    pattern = sys.argv[1] if len(sys.argv) > 1 else "*__*.png"
    scale = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    files = sorted(p for p in OUT.glob(pattern) if not p.name.startswith("REJECTED"))
    if not files:
        sys.exit(f"no candidates matching {pattern}")
    print(sheet(files, scale))
