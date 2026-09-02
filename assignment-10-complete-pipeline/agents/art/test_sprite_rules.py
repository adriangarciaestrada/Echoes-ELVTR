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


# ---- the prompts, and where they come from -------------------------------

import json

import generate
import inventory


def test_every_subject_has_a_curated_prompt():
    """The game decides WHAT needs a sprite; the vault decides how it is
    described. A subject with no line in the inventory would silently fall back
    to a prompt built from its stat line — "a Remnant that walks the lane to the
    Beacon" — which is how a boss ends up looking like a walker."""
    specs = json.loads((Path(__file__).parent / "art-specs.json").read_text())
    bodies = inventory.prompt_bodies()
    missing = [s["id"] for s in specs if s["id"] not in bodies]
    assert not missing, f"no prompt in asset-inventory.md for: {missing}"


def test_the_parser_reads_only_the_subject_tables():
    """The global-parameters table has the same three-column shape. An earlier
    version read it too and produced subjects called `enemy_no_background`."""
    bodies = inventory.prompt_bodies()
    assert not [k for k in bodies if "background" in k or "guidance" in k], bodies.keys()
    # Tied to the export, not to a constant. A literal 15 here went stale the
    # day the Weavers were added — the same failure the copy pipeline's coverage
    # test had, for the same reason.
    specs = json.loads((Path(__file__).parent / "art-specs.json").read_text())
    assert len(bodies) == len(specs), f"{len(bodies)} prompts for {len(specs)} subjects"


def test_a_prompt_survives_to_the_request():
    """The curated words, not the export's fallback."""
    spec = {"id": "enemy_bulwark", "kind": "boss", "subject": "bulwark",
            "detail": "a Remnant that walks the lane"}
    assert "hulking armoured husk" in generate.prompt_for(spec)


def test_a_card_and_an_icon_are_generated_under_different_briefs():
    """A 32px relic must read as a token at a glance; a 300x400 card is the one
    screen the player stops at, so the figure is the subject. Same style words,
    different brief — and different coverage."""
    card = {"id": "weaver_titan_card", "kind": "weaver_card", "subject": "the titan Weaver"}
    icon = {"id": "relic_bolt_needle", "kind": "relic", "subject": "Swift Fang"}
    assert generate.brief(card) == "card" and generate.brief(icon) == "icon"
    assert "character illustration" in generate.prompt_for(card)
    assert "game icon" in generate.prompt_for(icon)
    assert generate.COVERAGE["card"] > generate.COVERAGE["icon"]


def test_size_picks_the_endpoint():
    """bitforge carries the style anchor but stops at 200px, so the cards fall
    to pixflux by being 300x400 — not by anyone remembering to switch."""
    import pixellab
    anchor = Path("/tmp/anchor.png")
    assert pixellab.endpoint_for(32, 32, anchor).endswith("bitforge")
    assert pixellab.endpoint_for(96, 112, anchor).endswith("bitforge")
    assert pixellab.endpoint_for(300, 400, anchor).endswith("pixflux")


def test_a_flat_field_is_cut_and_the_figure_survives():
    """`no_background` is a request the model can ignore. The cut is a flood
    fill from the border, never a global colour match: a colour that also
    appears inside the figure is only erased where it connects to the edge."""
    import cutout
    img = Image.new("RGBA", (40, 40), (200, 200, 210, 255))     # flat field
    px = img.load()
    for y in range(10, 30):
        for x in range(10, 30):
            px[x, y] = (200, 200, 210, 255) if 18 <= x <= 21 and 18 <= y <= 21 else (20, 30, 40, 255)
    path = write(img)
    assert cutout.looks_framed(Image.open(path).convert("RGBA"))
    cleared = cutout.cut(path)
    after = Image.open(path).convert("RGBA").load()
    assert cleared > 0
    assert after[0, 0][3] == 0, "the border field should be gone"
    assert after[19, 19][3] == 255, "an enclosed pocket of the same colour must survive"
    assert after[12, 12][3] == 255, "the figure must survive"
