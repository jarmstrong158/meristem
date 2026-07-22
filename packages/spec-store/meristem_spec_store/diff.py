"""Structural diff between two manifest states (domain dicts)."""
from __future__ import annotations

from typing import Any


def _walk(old: Any, new: Any, path: str, out: dict) -> None:
    if isinstance(old, dict) and isinstance(new, dict):
        for k in old.keys() | new.keys():
            p = f"{path}.{k}" if path else k
            if k not in new:
                out["removed"][p] = old[k]
            elif k not in old:
                out["added"][p] = new[k]
            else:
                _walk(old[k], new[k], p, out)
    elif isinstance(old, list) and isinstance(new, list):
        if old != new:
            out["changed"][path] = [old, new]
    else:
        if old != new:
            out["changed"][path] = [old, new]


def diff(old: dict, new: dict) -> dict:
    out = {"added": {}, "removed": {}, "changed": {}}
    _walk(old or {}, new or {}, "", out)
    out["has_changes"] = bool(out["added"] or out["removed"] or out["changed"])
    return out
