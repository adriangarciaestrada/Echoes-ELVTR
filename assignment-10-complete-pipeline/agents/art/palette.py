#!/usr/bin/env python3
"""The game's palette, read from the game.

Parsed out of `src/game/theme.ts` rather than copied. A palette restated in a
second place is a palette that will disagree with itself the first time someone
tunes a colour, and the sprite checks would then be enforcing a scheme the game
no longer uses.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

THEME = Path(__file__).resolve().parents[2] / "src" / "game" / "theme.ts"

RGB = Tuple[int, int, int]


def _rgb(value: int) -> RGB:
    return ((value >> 16) & 255, (value >> 8) & 255, value & 255)


def load(path: Path = THEME) -> Dict[str, RGB]:
    """Every colour the game draws with, by name."""
    text = path.read_text(encoding="utf-8")
    out: Dict[str, RGB] = {}
    for name, hexed in re.findall(r"(\w+):\s*0x([0-9a-fA-F]{6})", text):
        out[name] = _rgb(int(hexed, 16))
    for name, hexed in re.findall(r'(\w+):\s*"#([0-9a-fA-F]{6})"', text):
        out[name] = _rgb(int(hexed, 16))
    # TIER_BG and CATEGORY_MARK are arrays/objects of bare hex; the two loops
    # above already caught the object form. Arrays need their own pass.
    for i, hexed in enumerate(re.findall(r"0x([0-9a-fA-F]{6})",
                                         re.search(r"TIER_BG = \[(.*?)\]", text, re.S).group(1))):
        out[f"tier{i}"] = _rgb(int(hexed, 16))
    return out


def sprite_palette(path: Path = THEME) -> List[RGB]:
    """The colours a SPRITE may use.

    Tier colour lives in the cell background and never in the sprite
    (art-direction.md), so the tier ramp is deliberately excluded — a sprite
    that paints itself purple would fight the cell it sits on.
    """
    all_colours = load(path)
    keep = ("bg", "panel", "panelEdge", "lane", "text", "dim", "accent",
            "beacon", "danger", "gold", "exp", "Bolt", "Burst", "Construct")
    return [all_colours[k] for k in keep if k in all_colours]


if __name__ == "__main__":
    for name, rgb in load().items():
        print(f"  {name:12} #{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}  {rgb}")
    print(f"\nsprite palette: {len(sprite_palette())} colours")
