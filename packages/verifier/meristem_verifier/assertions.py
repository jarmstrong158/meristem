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

    # Melee: if the spec gives the player an atk stat, then hitting an enemy must
    # actually reduce that enemy's hp by it. A string check on the generated script
    # only proves the code was written; this proves it CONNECTS -- that the swing
    # reaches the enemy's take_damage and the arithmetic lands.
    player = next((c for c in domains.get("entities", {}).get("characters", [])), None)
    enemy = next((e for e in domains.get("entities", {}).get("enemies", [])), None)
    if arch and arch["kind"] == "top_down_controller" and player and enemy:
        atk = int(player.get("stats", {}).get("atk", 0))
        hp = int(enemy.get("stats", {}).get("hp", 0))
        if atk > 0 and hp > 0:
            out.append({"kind": "melee_damage", "entity": enemy["id"],
                        "attack": atk, "enemy_hp": hp,
                        "expected": max(hp - atk, 0)})
    return out
