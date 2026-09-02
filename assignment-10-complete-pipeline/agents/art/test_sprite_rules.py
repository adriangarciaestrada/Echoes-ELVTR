#!/usr/bin/env python3
"""Tests for the sprite checks, against images built on purpose.

    python3 -m pytest test_sprite_rules.py -q

Synthetic fixtures, so the checks are verified without spending a credit or
holding an API key — and so each rule is exercised by an image that breaks it
and nothing else.
"""
import tempfile
from pathlib import Path

import pytest
from PIL import Image

import palette
import sprite_rules as R

PAL = palette.sprite_palette()


def write(img: Image.Image) -> Path:
    path = Path(tempfile.mkdtemp()) / "s.png"
    img.save(path)
    return path


def sprite(size=(32, 32), colours=None, coverage=0.5, border=False):
    """A plausible sprite: palette colours in the middle, transparent around."""
    colours = colours or PAL[:4]
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    px = img.load()
    w, h = size
    filled = int(w * h * coverage)
    n = 0
    for y in range(h):
        for x in range(w):
            edge = x in (0, w - 1) or y in (0, h - 1)
            if edge and not border:
                continue
            if n >= filled:
                break
            px[x, y] = (*colours[n % len(colours)], 255)
            n += 1
    return img


def test_a_good_sprite_passes():
    assert R.check(write(sprite()), 32, 32) == []


def test_the_wrong_size_is_caught_first():
    out = R.check(write(sprite((40, 33))), 32, 32)
    assert len(out) == 1 and "not the 32x32" in out[0]


def test_an_uncut_background_is_caught():
    """The failure that matters most: a sprite that fills its frame has no
    silhouette and sits on the board as a rectangle."""
    solid = Image.new("RGBA", (32, 32), (*PAL[0], 255))
    out = R.check(write(solid), 32, 32)
    assert any("never cut out" in f for f in out)
    assert any("framed, not cut out" in f for f in out)


def test_an_empty_sprite_is_caught():
    out = R.check(write(Image.new("RGBA", (32, 32), (0, 0, 0, 0))), 32, 32)
    assert any("speck" in f or "entirely transparent" in f for f in out)


def test_a_foreign_palette_is_caught():
    """Neon magenta and lime belong to a different game."""
    out = R.check(write(sprite(colours=[(255, 0, 255), (0, 255, 0)])), 32, 32)
    assert any("colour scheme" in f for f in out)


def test_a_photo_is_caught():
    """Hundreds of distinct colours is a small photo, not pixel art."""
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    px = img.load()
    for y in range(4, 28):
        for x in range(4, 28):
            px[x, y] = (100 + x, 120 + y, 140, 255)
    out = R.check(write(img), 32, 32)
    assert any("not pixel art" in f for f in out)


def test_the_palette_comes_from_the_game():
    """Not a copied list: it is parsed from theme.ts, so a colour tuned in the
    game moves this check with it."""
    assert palette.load()["beacon"] == (0x8f, 0xd3, 0xc7)
    assert (0x8a, 0x56, 0xc8) not in PAL, "tier colours belong to the cell, not the sprite"

# The prompt-builder tests that used to follow here covered the generation
# path this deliverable does not ship — no image in the submitted build came
# from it — so they were removed with it. What remains is the deterministic
# check every shipped sprite actually passed through.
