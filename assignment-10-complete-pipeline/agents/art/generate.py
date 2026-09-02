#!/usr/bin/env python3
"""spec -> generate N -> deterministic checks -> human pick -> import.

The gate is the point (`art-direction.md`): candidates that fail the measurable
rules never reach the person choosing, so taste is spent on sprites that already
fit the board instead of on ones that cannot ship.

    python3 generate.py --only relic_bolt_needle --n 4      # one subject
    python3 generate.py --kind relic --n 3                  # every relic
    python3 generate.py --dry-run                           # prompts, no spend

Nothing is imported into the game here. Survivors land in candidates/ with a
sidecar each, and `pick.py` moves a chosen one into the build.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from PIL import Image

import cutout
import inventory
import palette
import pixellab
import sprite_rules

HERE = Path(__file__).resolve().parent
SPECS = HERE / "art-specs.json"
OUT = HERE / "candidates"

# The house style, applied to every prompt. Kept in one place: a style restated
# per subject drifts subject by subject, which is how a roster ends up looking
# like fifteen different games.
PALETTE_WORDS = ("dark stone and luminous thread, muted desaturated palette of deep "
                 "blue-black with pale teal highlights, no text, no border")

# An icon and a character card are not the same brief. A 32px relic has to read
# as a token at a glance; a 300x400 card is the one place the player stops and
# looks, so the figure is the subject rather than a symbol.
STYLE = {
    "icon": ("pixel art game icon, clean readable silhouette, transparent "
             f"background, centred, {PALETTE_WORDS}"),
    # The card keeps its background: it is an illustration, and the world behind
    # the figure is part of what it shows.
    #
    # The FIGURE is science fiction and the SETTING is ancient — that contrast is
    # the picture. The house style's "dark stone and luminous thread" belongs to
    # the world, and applying it to the character produced fantasy knights:
    # `plate`, `helm` and `stone` in one prompt is a request for chainmail.
    "card": ("detailed pixel art character illustration, full figure, dynamic "
             "heroic pose, science-fiction powered armour, hard-surface "
             "mechanical panelling, NOT medieval, NOT a fantasy knight, "
             "standing on open ground ringed by ancient ruined pillars and "
             "collapsed walls scarred by battle, dark atmospheric depth, "
             "muted desaturated palette of deep blue-black, no text, no border"),
}

NEGATIVE = ("photorealistic, 3d render, blurry, antialiased, drop shadow, text, "
            "watermark, frame, border, white background")

# Cards are meant to be filled by their figure; icons need air around them.
COVERAGE = {"card": 70.0, "icon": 55.0}

# The cards keep their background — they are illustrations, and the world behind
# the figure is part of what they show. Everything that goes on the board is cut
# out, because a sprite without a silhouette is a rectangle.
WANTS_CUTOUT = {"card": False, "icon": True}

# Camera and facing, per family (asset-inventory.md). The board is read from
# above and behind, and the Weaver faces away up the lane.
VIEW = {"weaver_card": "side", "weaver_back": "high top-down",
        "relic": "side", "enemy": "high top-down", "boss": "high top-down",
        "beacon": "side"}
DIRECTION = {"weaver_card": "south", "weaver_back": "north"}


def palette_png(path: Path = HERE / "palette.png") -> Path:
    """The game's palette as an image, for the API's `color_image` field."""
    colours = palette.sprite_palette()
    img = Image.new("RGB", (len(colours), 1))
    img.putdata(colours)
    img = img.resize((len(colours) * 8, 8), Image.NEAREST)
    img.save(path)
    return path


def brief(spec: dict) -> str:
    """Which brief this subject is generated under."""
    return "card" if spec["kind"] == "weaver_card" else "icon"


def prompt_for(spec: dict, bodies: dict | None = None) -> str:
    """Subject from the game, words from the vault.

    The body is the curated line in `asset-inventory.md`. The export's own
    `detail` field is a fallback only: it is built from the enemy's stat line
    and reads like one.
    """
    bodies = inventory.prompt_bodies() if bodies is None else bodies
    body = bodies.get(spec["id"]) or (spec.get("detail") or "").rstrip(".")
    lead = f"{spec['subject']}, {body}" if body else spec["subject"]
    return f"{lead}. {STYLE[brief(spec)]}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate sprite candidates.")
    ap.add_argument("--only", help="a single spec id")
    ap.add_argument("--kind", help="relic | enemy | beacon")
    ap.add_argument("--n", type=int, default=3, help="candidates per subject")
    ap.add_argument("--dry-run", action="store_true", help="print prompts, spend nothing")
    ap.add_argument("--anchor", help="approved sprite to inherit style from (bitforge)")
    ap.add_argument("--init", help="image to seed from (pixflux)")
    ap.add_argument("--init-strength", type=int, default=120,
                    help="1-999; how hard the seed pulls. 300 is the API default")
    ap.add_argument("--suffix", default="", help="tag appended to candidate filenames")
    ap.add_argument("--body", help="override the vault's prompt body, for experiments")
    args = ap.parse_args()

    specs = json.loads(SPECS.read_text(encoding="utf-8"))
    bodies = inventory.prompt_bodies()
    if args.body:
        # Experiments only. The vault stays the source of truth for what ships;
        # this exists so a pose can be tried without editing the contract first.
        for spec in specs:
            bodies[spec["id"]] = args.body
    orphans = [s["id"] for s in specs if s["id"] not in bodies]
    if orphans:
        return print(f"no prompt in the vault for: {', '.join(orphans)}") or 1
    if args.only:
        specs = [s for s in specs if s["id"] == args.only]
    if args.kind:
        specs = [s for s in specs if s["kind"] == args.kind]
    if not specs:
        return print("no specs matched") or 1

    if args.dry_run:
        for s in specs:
            ep = pixellab.endpoint_for(s["width"], s["height"],
                                       Path(args.anchor) if args.anchor else None)
            print(f"\n{s['id']}  {s['width']}x{s['height']}  [{brief(s)}] {ep.split('-')[-1]}"
                  f"\n  {prompt_for(s, bodies)}")
        print(f"\n{len(specs)} subjects x {args.n} = {len(specs) * args.n} generations")
        return 0

    print(f"balance before: {pixellab.balance()}")
    OUT.mkdir(exist_ok=True)
    pal = palette_png()
    kept, dropped, spend = 0, 0, []

    for s in specs:
        print(f"\n{s['id']}  {s['width']}x{s['height']}")
        for i in range(args.n):
            # Recorded so a sprite anyone likes can be regenerated rather than
            # hunted for again — which needs the seed to be stable across runs.
            # Python's hash() is salted per process, so the same subject drew a
            # different seed every session and the promise was empty.
            seed = int(hashlib.sha1(s["id"].encode()).hexdigest()[:6], 16) % 100000 + i
            png, usage = pixellab.generate(
                prompt_for(s, bodies), s["width"], s["height"], seed=seed,
                palette_png=pal, negative=NEGATIVE, coverage=COVERAGE[brief(s)],
                no_background=WANTS_CUTOUT[brief(s)],
                view=VIEW.get(s["kind"]), direction=DIRECTION.get(s["kind"]),
                style_png=Path(args.anchor) if args.anchor else None,
                init_png=Path(args.init) if args.init else None,
                init_strength=args.init_strength)
            spend.append(usage)
            path = OUT / f"{s['id']}{args.suffix}__{i}.png"
            path.write_bytes(png)
            # `no_background` is a request the model can ignore, and on the
            # character cards it did — they came back on a solid field. Cut it
            # here, before the checks, and only when it is genuinely flat.
            wants = WANTS_CUTOUT[brief(s)]
            if wants:
                # `no_background` is a request the model can ignore, so the flat
                # field is removed here when there is one.
                from PIL import Image
                if cutout.looks_framed(Image.open(path).convert("RGBA")):
                    cleared = cutout.cut(path)
                    print(f"    cut {cleared * 100 // (s['width'] * s['height'])}% background")
            findings = sprite_rules.check(path, s["width"], s["height"], cutout=wants)
            if findings:
                dropped += 1
                path.rename(OUT / f"REJECTED_{s['id']}{args.suffix}__{i}.png")
                print(f"  [{i}] rejected: {findings[0]}")
            else:
                kept += 1
                (OUT / f"{s['id']}{args.suffix}__{i}.json").write_text(json.dumps({
                    "spec": s, "prompt": prompt_for(s, bodies), "seed": seed,
                    "usage": usage, "checks": "clean",
                }, indent=1), encoding="utf-8")
                print(f"  [{i}] kept")
            time.sleep(0.5)

    print(f"\n{kept} kept, {dropped} rejected -> {OUT}")
    print(f"balance after: {pixellab.balance()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
