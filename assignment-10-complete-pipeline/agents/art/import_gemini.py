#!/usr/bin/env python3
"""Turn a chosen Gemini reference image into a game-ready sprite.

The Gemini images in `References/*-chosen.jpeg` are concept art, not sprites:
they are 1900-2800px on a side, JPEG, and (for the back sprites) still carry
their flat backdrop. This does the mechanical half of turning one into what
`art-specs.json` actually asks for — center-crop to the target aspect ratio,
downscale to the exact pixel size, cut the background on back sprites, export
PNG — and then runs the same deterministic checks the PixelLab pipeline runs,
so a sprite that doesn't fit the board is reported rather than shipped quietly.

It does NOT make these pixel art. A downscaled photo-shaded image keeps its
gradients and colour count; `sprite_rules.check()` below will say so. Fixing
that is a judgement call (accept the cinematic look, or run it through
`palette.py`'s ramp) that this script leaves to a person.

    python3 import_gemini.py                  # every mapped source
    python3 import_gemini.py --only weaver_titan_card
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

import cutout
import sprite_rules

HERE = Path(__file__).resolve().parent
REFERENCES = HERE.parents[1] / "References"
SPECS = HERE / "art-specs.json"
OUT = HERE / "approved"

# Which chosen reference feeds which spec id. The reference is the source of
# truth for the picture; the spec is the source of truth for size and kind.
SOURCES = {
    "weaver_titan_card": "Titan-card-chosen.jpeg",
    "weaver_hunter_card": "Hunter-card-chosen.jpeg",
    "weaver_warden_card": "Warden-card-chosen.jpeg",
    "weaver_titan_back": "Titan-back-chosen.jpeg",
    "weaver_hunter_back": "Hunter-back-chosen.jpeg",
    "weaver_warden_back": "Warden-back-chosen.jpeg",
    "battlefield": "Battlefield-chosen.jpeg",
}


def fit(img: Image.Image, width: int, height: int) -> Image.Image:
    """Center-crop to the target ratio, then downscale to exact size.

    A plain resize would stretch a landscape source into a portrait sprite.
    Cropping first keeps the figure's proportions the way it was drawn; the
    downscale is real information loss (this is not the 1:1 generation the
    PixelLab side of the pipeline insists on), so this is a concept-art import,
    not a native-resolution sprite.
    """
    target_ratio = width / height
    w, h = img.size
    ratio = w / h
    if ratio > target_ratio:
        new_w = round(h * target_ratio)
        x0 = (w - new_w) // 2
        img = img.crop((x0, 0, x0 + new_w, h))
    elif ratio < target_ratio:
        new_h = round(w / target_ratio)
        y0 = (h - new_h) // 2
        img = img.crop((0, y0, w, y0 + new_h))
    return img.resize((width, height), Image.LANCZOS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", help="a single spec id")
    args = ap.parse_args()

    specs = {s["id"]: s for s in json.loads(SPECS.read_text(encoding="utf-8"))}
    ids = [args.only] if args.only else list(SOURCES)
    OUT.mkdir(exist_ok=True)

    for sid in ids:
        if sid not in SOURCES:
            print(f"no Gemini source mapped for {sid}")
            continue
        spec = specs[sid]
        src = REFERENCES / SOURCES[sid]
        if not src.exists():
            print(f"{sid}: missing source {src}")
            continue

        img = Image.open(src).convert("RGBA")
        img = fit(img, spec["width"], spec["height"])

        is_back = spec["kind"] == "weaver_back"
        dest = OUT / f"{sid}.png"
        img.save(dest)
        if is_back:
            cleared = cutout.cut(dest)
            print(f"{sid}: cut {cleared * 100 // (spec['width'] * spec['height'])}% background")

        findings = sprite_rules.check(dest, spec["width"], spec["height"], cutout=is_back)
        (OUT / f"{sid}.json").write_text(json.dumps({
            "spec": spec,
            "source": "gemini (manual, via the Gemini web interface)",
            "source_file": f"References/{SOURCES[sid]}",
            "note": "center-cropped and downscaled from a higher-resolution "
                    "source, not generated at native sprite resolution",
            "checks": findings or "clean",
        }, indent=1), encoding="utf-8")

        status = "clean" if not findings else f"{len(findings)} finding(s)"
        print(f"{sid}: {dest.name} ({status})")
        for f in findings:
            print(f"    {f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
