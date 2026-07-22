"""Style contract: the locked palette + canvas/outline/shading/anchor rules that
every asset must conform to. Loaded from the same JSON shape used in the Phase 0
bake-off (experiments/00-bakeoff/style-contract.json)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


@dataclass(frozen=True)
class PaletteColor:
    i: int
    hex: str
    name: str

    @property
    def rgb(self) -> tuple[int, int, int]:
        return _hex_to_rgb(self.hex)


class ContractError(ValueError):
    """Raised when a style contract is structurally invalid."""


@dataclass
class StyleContract:
    name: str
    version: int
    colors: list[PaletteColor]
    canvas: dict[str, tuple[int, int]]
    anchor: dict[str, str]
    outline_policy: str
    outline_color_rule: str
    outline_fallback_index: int
    ramp_steps: int
    light_direction: str
    background_mode: str
    background_alpha: str
    grid_base_unit: int
    naming_convention: str
    class_prefixes: dict[str, str]
    free_palette_classes: list[str] = field(default_factory=list)
    max_colors: int = 15
    raw: dict = field(repr=False, default_factory=dict)

    def is_free_palette(self, asset_class: str) -> bool:
        """Free-palette classes (e.g. characters) use per-material hue-shifted ramps
        (dec-0020) and are checked against a color budget, not the locked palette."""
        return asset_class in self.free_palette_classes

    # ---- derived ----
    @property
    def palette_rgb(self) -> np.ndarray:
        return np.array([c.rgb for c in self.colors], dtype=np.int16)  # (N,3)

    @property
    def palette_set(self) -> set[tuple[int, int, int]]:
        return {c.rgb for c in self.colors}

    @property
    def name_to_index(self) -> dict[str, int]:
        return {c.name: c.i for c in self.colors}

    def canvas_of(self, asset_class: str) -> tuple[int, int]:
        if asset_class not in self.canvas:
            raise ContractError(f"unknown asset class {asset_class!r}; known: {sorted(self.canvas)}")
        return self.canvas[asset_class]

    def anchor_of(self, asset_class: str) -> str:
        return self.anchor.get(asset_class, "center")

    def hash(self) -> str:
        """Stable content hash of the contract, for provenance sidecars."""
        payload = json.dumps(self.raw, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(payload).hexdigest()[:32]

    # ---- construction ----
    @classmethod
    def from_dict(cls, d: dict) -> "StyleContract":
        try:
            pal = d["palette"]["colors"]
            colors = [PaletteColor(i=c["i"], hex=c["hex"], name=c["name"]) for c in pal]
            if not colors:
                raise ContractError("palette has no colors")
            canvas = {k: (v["w"], v["h"]) for k, v in d["canvas"].items()}
            outline = d.get("outline", {})
            shading = d.get("shading", {})
            bg = d.get("background", {})
            naming = d.get("naming", {})
            return cls(
                name=d["name"],
                version=int(d.get("version", 1)),
                colors=colors,
                canvas=canvas,
                anchor={k: v for k, v in d.get("anchor", {}).items() if k != "note"},
                outline_policy=outline.get("policy", "none"),
                outline_color_rule=outline.get("color_rule", "darkest_shade_of_subject_ramp"),
                outline_fallback_index=int(outline.get("fallback_color_index", 0)),
                ramp_steps=int(shading.get("ramp_steps", 3)),
                light_direction=shading.get("light_direction", "top_left"),
                background_mode=bg.get("mode", "transparent"),
                background_alpha=bg.get("alpha", "hard"),
                grid_base_unit=int(d.get("grid", {}).get("base_unit", 16)),
                naming_convention=naming.get("convention", "{class}_{name}.png"),
                class_prefixes=naming.get("class_prefixes", {}),
                free_palette_classes=d.get("palette", {}).get("free_classes", ["character", "enemy"]),
                max_colors=int(d.get("palette", {}).get("max_colors", 15)),
                raw=d,
            )
        except KeyError as e:
            raise ContractError(f"style contract missing required key: {e}") from e


def load_contract(path: str | Path) -> StyleContract:
    p = Path(path)
    if not p.exists():
        raise ContractError(f"style contract not found: {p}")
    return StyleContract.from_dict(json.loads(p.read_text(encoding="utf-8")))
