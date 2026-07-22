"""Filenames per the contract's naming convention."""
from __future__ import annotations

from typing import Optional

from .contract import StyleContract


def asset_filename(contract: StyleContract, asset_class: str, name: str,
                   variant: Optional[str] = None) -> str:
    prefix = contract.class_prefixes.get(asset_class, asset_class)
    stem = f"{prefix}_{name}" + (f"_{variant}" if variant else "")
    conv = contract.naming_convention
    # convention uses {class}_{name}[_{variant}].png; we substitute the assembled stem
    if conv.endswith(".png"):
        return stem + ".png"
    return stem
