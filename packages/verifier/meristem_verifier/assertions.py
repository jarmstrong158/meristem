"""Derive testable assertions from the manifest. If the spec says move_speed 80,
that is checkable headlessly by driving input and measuring terminal velocity."""
from __future__ import annotations


def derive_assertions(domains: dict) -> list[dict]:
    out: list[dict] = []
    archetypes = {a["id"]: a for a in domains.get("mechanics", {}).get("archetypes", [])}
    control = domains.get("project", {}).get("control_scheme")
    arch = archetypes.get(control)
    if arch and arch["kind"] in ("top_down_controller", "platformer_controller"):
        ms = arch.get("params", {}).get("move_speed")
        if ms:
            out.append({"kind": "move_speed", "entity": "player",
                        "expected": float(ms), "tolerance": max(2.0, float(ms) * 0.08)})
    return out
