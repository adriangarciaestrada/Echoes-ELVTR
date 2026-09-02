#!/usr/bin/env python3
"""PixelLab REST client.

Contract read from the live schema at https://api.pixellab.ai/v1/openapi.json,
not from memory: POST /v1/generate-image-pixflux, Bearer auth, 16-400px, and a
base64 PNG in `image.base64`.

The key is read from PIXELLAB_API_KEY, or from 1Password when the value looks
like an `op://` reference. It is never written to a file, and never logged.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

BASE = "https://api.pixellab.ai/v1"

# The API's own failure modes, spelled out. A pipeline that prints "HTTP 402"
# and stops has told the operator nothing they can act on.
MEANINGS = {
    401: "the API key was rejected",
    402: "the account is out of credits",
    422: "the request was malformed (check image_size bounds: 16-400)",
    429: "rate limited",
    529: "PixelLab is overloaded",
}


_CACHED_KEY: Optional[str] = None


def api_key() -> str:
    """Read once per process.

    It used to shell out to `op` on every request, which turns one expired
    1Password session into a traceback halfway through a batch — and the
    traceback went to stderr, where a caller filtering stdout never saw it. The
    run died silently three times before that was noticed.
    """
    global _CACHED_KEY
    if _CACHED_KEY:
        return _CACHED_KEY

    raw = os.environ.get("PIXELLAB_API_KEY", "").strip()
    if not raw:
        raise SystemExit(
            "PIXELLAB_API_KEY is not set.\n"
            "  export PIXELLAB_API_KEY='...'            (this shell only)\n"
            "  export PIXELLAB_API_KEY='op://Private/PixelLab/credential'")
    if raw.startswith("op://"):
        done = subprocess.run(["op", "read", raw], capture_output=True, text=True)
        if done.returncode != 0:
            raise SystemExit(
                f"1Password would not read {raw}.\n"
                f"  {done.stderr.strip().splitlines()[-1] if done.stderr.strip() else 'no detail'}\n"
                "The session expires on its own; unlock it with `op signin` and "
                "run this again. Nothing was generated, so nothing was spent.")
        _CACHED_KEY = done.stdout.strip()
    else:
        _CACHED_KEY = raw
    return _CACHED_KEY


def balance() -> float:
    r = requests.get(f"{BASE}/balance", headers={"Authorization": f"Bearer {api_key()}"},
                     timeout=30)
    if r.status_code != 200:
        raise SystemExit(f"balance: {MEANINGS.get(r.status_code, r.status_code)}")
    return r.json().get("usd", r.json())


# The two generation endpoints, and why both exist here:
#
#   bitforge  carries `style_image`, so a whole roster can inherit one approved
#             look — but it stops at 200x200.
#   pixflux   reaches 400x400, which the character cards need, and has no
#             `style_image` at all. It has `init_image`, which is the nearest
#             thing: it seeds from an approved sprite without pinning the pose.
#
# Size decides the endpoint, so the caller never has to remember the ceiling.
BITFORGE_MAX = 200

# Undocumented in the OpenAPI schema, learned from a 422: both dimensions must
# be divisible by 4. Checked before the request so a bad size costs nothing and
# says so, rather than coming back as a malformed-request error mid-run.
SIZE_STEP = 4

# /rotate is stricter than everything else: four square canvases, nothing else.
ROTATE_SIZES = {(128, 128), (64, 64), (32, 32), (16, 16)}


def _b64(path: Path) -> Dict:
    return {"type": "base64", "base64": base64.b64encode(path.read_bytes()).decode()}


def _b64_sized(path: Path, width: int, height: int) -> Dict:
    """A reference image, resized to the output canvas.

    Every image the API takes alongside a generation — `style_image`,
    `init_image`, `from_image` — must match the output exactly, and says so with
    a 500 rather than a 422. Undocumented, and the same rule three times, so the
    client does the fitting instead of each caller remembering.
    """
    from io import BytesIO
    from PIL import Image
    img = Image.open(path).convert("RGBA")
    if img.size != (width, height):
        img = img.resize((width, height), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return {"type": "base64", "base64": base64.b64encode(buf.getvalue()).decode()}


def endpoint_for(width: int, height: int, style: Optional[Path]) -> str:
    if style is not None and max(width, height) <= BITFORGE_MAX:
        return "generate-image-bitforge"
    return "generate-image-pixflux"


def generate(description: str, width: int, height: int, *, seed: Optional[int] = None,
             palette_png: Optional[Path] = None, guidance: float = 8.0,
             style_png: Optional[Path] = None, style_strength: int = 55,
             init_png: Optional[Path] = None, init_strength: int = 120,
             negative: Optional[str] = None, coverage: Optional[float] = None,
             no_background: bool = True, view: Optional[str] = None,
             direction: Optional[str] = None, retries: int = 3) -> Tuple[bytes, Dict]:
    """One sprite. Returns (png bytes, usage).

    `no_background` asks for a cut-out rather than a framed picture, and
    `color_image` hands the generator the game's own palette — both are the
    request-side half of checks that `sprite_rules.py` then enforces, because
    asking politely is not the same as verifying.
    """
    for name, value in (("width", width), ("height", height)):
        if value % SIZE_STEP:
            raise SystemExit(
                f"{name} {value} is not divisible by {SIZE_STEP}; PixelLab "
                f"refuses it. Nearest allowed: {value - value % SIZE_STEP}.")
    path = endpoint_for(width, height, style_png)
    body: Dict = {
        "description": description,
        "image_size": {"width": width, "height": height},
        "no_background": no_background,
        "text_guidance_scale": guidance,
    }
    if seed is not None:
        body["seed"] = seed
    if palette_png is not None:
        body["color_image"] = _b64(palette_png)
    if coverage is not None:
        body["coverage_percentage"] = coverage
    # The inventory has specified these since it was written and the client was
    # not sending them: `view` is the camera, `direction` is which way the
    # subject faces. Asking for "seen from behind" in prose while leaving
    # `direction` unset is asking the model to guess what a field already says.
    if view:
        body["view"] = view
    if direction:
        body["direction"] = direction
    if path.endswith("bitforge"):
        if style_png is not None:
            body["style_image"] = _b64_sized(style_png, width, height)
            body["style_strength"] = style_strength
        if negative:
            body["negative_description"] = negative
    elif init_png is not None:
        # pixflux's substitute for style transfer: seed from an approved sprite
        # at low strength, enough to carry palette and treatment without
        # copying the pose — and the card poses have to differ from each other.
        body["init_image"] = _b64_sized(init_png, width, height)
        body["init_image_strength"] = init_strength

    for attempt in range(retries):
        r = requests.post(f"{BASE}/{path}", json=body, timeout=180,
                          headers={"Authorization": f"Bearer {api_key()}"})
        if r.status_code == 200:
            payload = r.json()
            return base64.b64decode(payload["image"]["base64"]), payload.get("usage", {})
        if r.status_code in (429, 529) and attempt < retries - 1:
            wait = 2 ** attempt * 5
            print(f"    {MEANINGS[r.status_code]}; waiting {wait}s")
            time.sleep(wait)
            continue
        detail = ""
        try:
            detail = json.dumps(r.json())[:200]
        except Exception:
            detail = r.text[:200]
        raise SystemExit(f"generate: {MEANINGS.get(r.status_code, r.status_code)} — {detail}")
    raise SystemExit("generate: retries exhausted")


def rotate(from_png: Path, width: int, height: int, *,
           from_direction: str = "south", to_direction: str = "north",
           from_view: str = "side", to_view: str = "high top-down",
           guidance: float = 6.0, palette_png: Optional[Path] = None,
           seed: Optional[int] = None, retries: int = 3) -> Tuple[bytes, Dict]:
    """The same character, seen from somewhere else.

    This is what keeps the battlefield sprite and the card the same person: the
    card is rotated rather than described again. Describing a character twice
    gets you two characters.

    Directions are the subject's facing — `south` looks at the viewer, `north`
    looks away up the lane. Views are the camera; the board is read from above
    and behind, so `side` becomes `high top-down`.
    """
    # Also undocumented: /rotate takes only these four square canvases. The
    # sprite is framed out of the result afterwards.
    if (width, height) not in ROTATE_SIZES:
        raise SystemExit(f"rotate accepts only {sorted(ROTATE_SIZES)}, got {width}x{height}")
    body: Dict = {
        "image_size": {"width": width, "height": height},
        "from_image": _b64_sized(from_png, width, height),
        "from_direction": from_direction, "to_direction": to_direction,
        "from_view": from_view, "to_view": to_view,
        "image_guidance_scale": guidance,
    }
    if palette_png is not None:
        body["color_image"] = _b64(palette_png)
    if seed is not None:
        body["seed"] = seed

    for attempt in range(retries):
        r = requests.post(f"{BASE}/rotate", json=body, timeout=180,
                          headers={"Authorization": f"Bearer {api_key()}"})
        if r.status_code == 200:
            payload = r.json()
            return base64.b64decode(payload["image"]["base64"]), payload.get("usage", {})
        if r.status_code in (429, 529) and attempt < retries - 1:
            time.sleep(2 ** attempt * 5)
            continue
        detail = r.text[:220]
        raise SystemExit(f"rotate: {MEANINGS.get(r.status_code, r.status_code)} — {detail}")
    raise SystemExit("rotate: retries exhausted")


if __name__ == "__main__":
    print(f"balance: {balance()}")
