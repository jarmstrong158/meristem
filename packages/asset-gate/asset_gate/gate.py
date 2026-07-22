"""The gate: normalize an image to a style contract, or reject it with reasons.

Two asset shapes, inferred from the contract's anchor rule:
  * tiles  (anchor == "top_left")  — must be full-bleed material: exact canvas size,
    zero transparency. The gate VALIDATES these strictly (reject-and-report); it does
    not invent a background color. Tileability is the compiler's job (dec-0012).
  * sprites (anchor center / bottom_center) — quantized, trimmed, optionally outlined,
    and repivoted onto the canvas. Rejected only if empty or larger than the canvas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from PIL import Image

from . import ops, palette as palette_mod
from .contract import StyleContract
from .provenance import Provenance

GATE_VERSION = "0.1.0"


@dataclass
class GateResult:
    accepted: bool
    asset_class: str
    reasons: list[str] = field(default_factory=list)      # why it was rejected (hard)
    warnings: list[str] = field(default_factory=list)     # soft notes, still accepted
    report: dict = field(default_factory=dict)            # measured metrics
    image: Optional[Image.Image] = None                   # normalized asset (None if rejected)
    provenance: Optional[Provenance] = None

    def __bool__(self) -> bool:
        return self.accepted


def _measure(arr: np.ndarray, contract: StyleContract) -> dict:
    a = arr[..., 3]
    opaque_mask = a == 255
    opaque = arr[opaque_mask][:, :3]
    pal_set = contract.palette_set
    if len(opaque) == 0:
        exact_pct, uniq, subset = 100.0, 0, True
    else:
        tuples = {tuple(int(c) for c in px) for px in opaque}
        matches = sum(1 for px in opaque if tuple(int(c) for c in px) in pal_set)
        exact_pct = round(100.0 * matches / len(opaque), 3)
        uniq = len(tuples)
        subset = tuples.issubset(pal_set)
    return {
        "size": [int(arr.shape[1]), int(arr.shape[0])],
        "opaque_px": int(opaque_mask.sum()),
        "transparent_px": int((a == 0).sum()),
        "semi_transparent_px": int(((a > 0) & (a < 255)).sum()),
        "palette_exact_pct": exact_pct,
        "unique_colors": uniq,
        "subset_of_palette": bool(subset),
        "coverage": round(float(opaque_mask.mean()), 3),
    }


def normalize(
    image: Image.Image,
    asset_class: str,
    contract: StyleContract,
    *,
    quantize: str = "nearest",
    outline: Optional[bool] = None,
    alpha_threshold: int = 128,
    provenance: Optional[Provenance] = None,
) -> GateResult:
    """Return a normalized asset or a GateResult with `accepted=False` + reasons."""
    reasons: list[str] = []
    warnings: list[str] = []

    # class must exist in the contract
    try:
        cw, ch = contract.canvas_of(asset_class)
    except Exception as e:  # ContractError
        return GateResult(False, asset_class, reasons=[str(e)])
    anchor = contract.anchor_of(asset_class)
    is_tile = anchor == "top_left"

    arr = ops.to_rgba_array(image)
    semi_before = int(((arr[..., 3] > 0) & (arr[..., 3] < 255)).sum())
    if semi_before:
        warnings.append(f"{semi_before} semi-transparent px hardened at threshold {alpha_threshold}")
    arr = ops.enforce_hard_alpha(arr, alpha_threshold)
    arr = palette_mod.quantize(arr, contract.palette_rgb, quantize)

    if is_tile:
        # strict validation: full-bleed material
        if arr.shape[1] != cw or arr.shape[0] != ch:
            reasons.append(f"tile size {arr.shape[1]}x{arr.shape[0]} != canvas {cw}x{ch}")
        transp = int((arr[..., 3] == 0).sum())
        if transp:
            reasons.append(f"terrain tile must be fully opaque; found {transp} transparent px")
        result_arr = arr
    else:
        # sprite: trim -> fit check -> place -> outline
        content, box = ops.trim(arr)
        if box is None:
            return GateResult(False, asset_class, reasons=["image is empty (no opaque pixels)"],
                              warnings=warnings)
        chh, cww = content.shape[:2]
        if cww > cw or chh > ch:
            reasons.append(f"content {cww}x{chh} exceeds canvas {cw}x{ch}")
            result_arr = arr
        else:
            canvas, _ = ops.place_on_canvas(content, cw, ch, anchor)
            do_outline = (contract.outline_policy != "none") if outline is None else outline
            if do_outline:
                oc = ops.darkest_opaque_color(canvas)
                if oc is None:
                    oc = contract.colors[contract.outline_fallback_index].rgb
                canvas = ops.apply_outline(canvas, oc)
            result_arr = canvas

    report = _measure(result_arr, contract)
    # hard invariants that must always hold post-normalization
    if report["semi_transparent_px"] != 0:
        reasons.append(f"{report['semi_transparent_px']} semi-transparent px remain")
    if not report["subset_of_palette"]:
        reasons.append(f"{report['unique_colors']} colors, not all in the locked palette")

    accepted = not reasons
    prov = provenance or Provenance(backend="imported")
    prov.contract_name = contract.name
    prov.contract_hash = contract.hash()
    prov.gate_version = GATE_VERSION
    report["outline_applied"] = (not is_tile) and accepted and (
        (contract.outline_policy != "none") if outline is None else bool(outline)
    )
    report["is_tile"] = is_tile

    return GateResult(
        accepted=accepted,
        asset_class=asset_class,
        reasons=reasons,
        warnings=warnings,
        report=report,
        image=ops.to_image(result_arr) if accepted else None,
        provenance=prov if accepted else None,
    )


def validate(image: Image.Image, asset_class: str, contract: StyleContract) -> GateResult:
    """Non-mutating conformance check for an already-normalized / hand-edited asset."""
    try:
        cw, ch = contract.canvas_of(asset_class)
    except Exception as e:
        return GateResult(False, asset_class, reasons=[str(e)])
    arr = ops.to_rgba_array(image)
    report = _measure(arr, contract)
    reasons = []
    if report["size"] != [cw, ch]:
        reasons.append(f"size {report['size']} != canvas [{cw}, {ch}]")
    if report["semi_transparent_px"]:
        reasons.append(f"{report['semi_transparent_px']} semi-transparent px")
    if not report["subset_of_palette"]:
        reasons.append("colors outside the locked palette")
    if contract.anchor_of(asset_class) == "top_left" and report["transparent_px"]:
        reasons.append(f"tile has {report['transparent_px']} transparent px (must be full-bleed)")
    return GateResult(not reasons, asset_class, reasons=reasons, report=report,
                      image=image if not reasons else None)
