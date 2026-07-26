"""Render a sprite to PNG bytes so a human — or a model — can LOOK at it.

The pixel-art standard's core loop is *render, then judge by eye*: the asset gate
checks conformance (canvas, hard alpha, palette subset where locked), never quality.
Nothing in the authoring path could actually produce a picture, though — an agent
composing a manifest through the MCP could list the sprite vocabulary and validate a
pick, then had to take on faith that the pick looked like the thing it named. Every
sprite defect fixed so far was found by rendering and looking, which is exactly the
step that was unavailable.

Two views, matching the two questions worth asking:

  render_sprite  — "what does this one config look like?"
  render_builds  — "do these variants read as different things?" (a labelled strip of
                   every build, optionally as pure alpha masks)

The alpha-mask view is not a novelty. Variant distinctness is a silhouette property,
and interior detail actively hides silhouette collisions: `flyer` bird and moth were
the same ellipse pair differentiated only by interior feather lines, and read as one
creature twice. Stripping colour is what makes that visible.

Pure functions over (contract, archetype, config) -> bytes. No MCP, no filesystem.
"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from .archetypes import (ARCHETYPES, archetype_class, archetype_frames,
                         build_archetype, known_archetypes)
from .catalog import variant_options

# A dark neutral backdrop. Sprites are transparent-background and often near-white
# (ghost, snow, bone), so compositing onto something is required to see them at all —
# on a white page a sheet ghost is an invisible rectangle.
_BG = (34, 37, 44, 255)
_CELL = (44, 48, 57, 255)
_LABEL = (168, 176, 190)
_MASK = (235, 235, 240, 255)
MAX_SCALE = 16


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, "PNG")
    return buf.getvalue()


def _zoom(img: Image.Image, scale: int) -> Image.Image:
    scale = max(1, min(int(scale), MAX_SCALE))
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST)


def _silhouette(img: Image.Image) -> Image.Image:
    """Alpha mask only: the shape, with colour and interior detail discarded."""
    mask = img.split()[3].point(lambda v: 255 if v > 0 else 0)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(_MASK, mask=mask)
    return out


def _on_backdrop(img: Image.Image, pad: int = 2) -> Image.Image:
    plate = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), _CELL)
    plate.alpha_composite(img, (pad, pad))
    return plate


def variant_key(archetype: str) -> str | None:
    """Which config key selects this archetype's variant (build / kind / shape / name).

    Derived from the catalog's variant table rather than assumed, because it differs
    per archetype and a hardcoded "build" would silently render one default nine times
    for weapons (`kind`), pickups (`shape`) and tiles (`name`)."""
    axes = variant_options(archetype)
    for candidate in ("build", "kind", "shape", "name"):
        if candidate in axes:
            return candidate
    return None


def render_sprite(contract, archetype: str, config: dict | None = None, *,
                  scale: int = 6, frame: int = 0,
                  silhouette: bool = False) -> tuple[bytes, dict]:
    """One sprite as PNG bytes, plus what it is. `frame` picks an animation frame
    (0 is always the static build); `silhouette` returns the alpha mask instead."""
    if archetype not in ARCHETYPES:
        raise KeyError(f"unknown archetype {archetype!r}; known: {known_archetypes()}")
    cfg = dict(config or {})
    frames = archetype_frames(contract, archetype, cfg)
    n = len(frames) if frames else 1
    idx = int(frame) % n
    img = frames[idx] if frames else build_archetype(contract, archetype, cfg)
    view = _silhouette(img) if silhouette else img
    meta = {"archetype": archetype, "asset_class": archetype_class(archetype),
            "native_size": [img.width, img.height], "frames": n, "frame": idx,
            "scale": max(1, min(int(scale), MAX_SCALE)), "silhouette": bool(silhouette),
            "config": cfg}
    return _png(_zoom(_on_backdrop(view), scale)), meta


def render_builds(contract, archetype: str, config: dict | None = None, *,
                  scale: int = 5, silhouette: bool = True) -> tuple[bytes, dict]:
    """Every variant of one archetype in a labelled strip — the distinctness review.

    Defaults to silhouettes because that is the question this view exists to answer;
    pass silhouette=False to compare the finished art."""
    if archetype not in ARCHETYPES:
        raise KeyError(f"unknown archetype {archetype!r}; known: {known_archetypes()}")
    key = variant_key(archetype)
    options = variant_options(archetype).get(key, []) if key else []
    if not options:                          # an archetype with no variant axis
        png, meta = render_sprite(contract, archetype, config, scale=scale,
                                  silhouette=silhouette)
        return png, {**meta, "builds": [], "variant_key": None}

    base = dict(config or {})
    cells = []
    for opt in options:
        img = build_archetype(contract, archetype, {**base, key: opt})
        cells.append((opt, _zoom(_on_backdrop(_silhouette(img) if silhouette else img), scale)))

    font = ImageFont.load_default()
    pad, label_h = 6, 12
    w = pad + sum(img.width + pad for _, img in cells)
    h = pad + max(img.height for _, img in cells) + label_h + pad
    sheet = Image.new("RGBA", (w, h), _BG)
    draw = ImageDraw.Draw(sheet)
    x = pad
    for name, img in cells:
        sheet.alpha_composite(img, (x, pad))
        draw.text((x, pad + img.height), name, fill=_LABEL, font=font)
        x += img.width + pad
    return _png(sheet), {"archetype": archetype, "asset_class": archetype_class(archetype),
                         "variant_key": key, "builds": options,
                         "silhouette": bool(silhouette),
                         "scale": max(1, min(int(scale), MAX_SCALE)), "config": base}
