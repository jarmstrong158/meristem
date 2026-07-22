"""Atlas packing + JSON manifest, with animation-tag metadata.

A shelf packer places frames into rows under a max width. The manifest records each
frame's rect (and optional pivot) plus any animation tags, so the compiler can emit
Godot AtlasTexture / SpriteFrames from a single source of truth."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image


@dataclass
class AnimationTag:
    name: str                     # "player_walk"
    frames: list[str]             # ordered frame names present in the atlas
    fps: int = 8
    loop: bool = True


@dataclass
class Frame:
    name: str
    x: int
    y: int
    w: int
    h: int
    pivot: Optional[tuple[int, int]] = None


@dataclass
class Atlas:
    image: Image.Image
    frames: list[Frame]
    animations: list[AnimationTag] = field(default_factory=list)

    def manifest(self) -> dict:
        return {
            "size": [self.image.width, self.image.height],
            "frames": {
                f.name: {"x": f.x, "y": f.y, "w": f.w, "h": f.h,
                         **({"pivot": list(f.pivot)} if f.pivot else {})}
                for f in self.frames
            },
            "animations": [asdict(a) for a in self.animations],
        }

    def save(self, image_path: str | Path, manifest_path: Optional[str | Path] = None) -> tuple[Path, Path]:
        ip = Path(image_path)
        self.image.save(ip)
        mp = Path(manifest_path) if manifest_path else ip.with_suffix(".json")
        mp.write_text(json.dumps(self.manifest(), indent=2), encoding="utf-8")
        return ip, mp


def pack(entries: list[tuple[str, Image.Image]], *, max_width: int = 256,
         padding: int = 0, pivots: Optional[dict[str, tuple[int, int]]] = None,
         animations: Optional[list[AnimationTag]] = None) -> Atlas:
    """Shelf-pack (name, image) pairs into one atlas. Frames are placed left-to-right
    into rows, wrapping at max_width; taller frames set the row height."""
    if not entries:
        return Atlas(Image.new("RGBA", (1, 1), (0, 0, 0, 0)), [])
    pivots = pivots or {}
    # tallest-first reduces wasted shelf height
    ordered = sorted(entries, key=lambda e: e[1].height, reverse=True)

    frames: list[Frame] = []
    x = y = row_h = 0
    total_w = 0
    for name, img in ordered:
        w, h = img.width, img.height
        if x > 0 and x + w + padding > max_width:
            x = 0
            y += row_h + padding
            row_h = 0
        frames.append(Frame(name, x, y, w, h, pivots.get(name)))
        x += w + padding
        row_h = max(row_h, h)
        total_w = max(total_w, x - padding if padding else x)
    sheet_h = y + row_h
    sheet_w = min(max_width, total_w) if total_w else 1
    sheet_w = max(sheet_w, max(f.x + f.w for f in frames))

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
    by_name = dict(entries)
    for f in frames:
        sheet.alpha_composite(by_name[f.name].convert("RGBA"), (f.x, f.y))
    # restore stable (input) frame order in the manifest
    order = {n: i for i, (n, _) in enumerate(entries)}
    frames.sort(key=lambda f: order[f.name])
    return Atlas(sheet, frames, animations or [])
