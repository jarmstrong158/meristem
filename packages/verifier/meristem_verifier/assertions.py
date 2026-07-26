"""Derive testable assertions from the manifest. If the spec says move_speed 80,
that is checkable headlessly by driving input and measuring terminal velocity."""
from __future__ import annotations


TILE = 16


def _first_wall_pair(domains: dict):
    """((x, y), boundary_x) for the first passable cell whose right neighbour is solid,
    in the level the compiler treats as the start. None if the map has no such pair, or
    if the generators are not importable — in which case there is nothing to assert
    rather than something to assume."""
    try:
        from meristem_generators import solid_tiles
    except ImportError:
        return None
    solid = set(solid_tiles())
    levels = (domains.get("levels", {}) or {}).get("levels", [])
    if not levels:
        return None
    level = levels[0]
    legend, rows = level.get("legend", {}), level.get("rows", [])
    for y, row in enumerate(rows):
        for x in range(len(row) - 1):
            here, right = legend.get(row[x]), legend.get(row[x + 1])
            if here not in solid and right in solid:
                return (x, y), (x + 1) * TILE
    return None


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

    # Abilities: a projectile has the most moving parts of any ability -- its own scene,
    # a launch handoff, travel, and a collision -- so if it lands, the slot wiring and
    # the input binding are both real. A slot that is bound but inert is pressable and
    # silent, which is exactly what an author cannot see.
    # Gated on `arch` as well: the controller is what forwards ability input, so with no
    # resolvable control scheme there is no path from a keypress to a slot -- and the
    # manifest would not compile anyway.
    ability_defs = {a["id"]: a for a in (domains.get("abilities", {}) or {}).get("abilities", [])}
    if arch and player and enemy:
        for slot, ref in enumerate(player.get("abilities", [])):
            ab = ability_defs.get(ref)
            if not ab or ab.get("kind") != "projectile":
                continue
            hp = int(enemy.get("stats", {}).get("hp", 0))
            power = int(ab.get("power", 0))
            if hp > 0 and power > 0:
                out.append({"kind": "ability_damage", "entity": enemy["id"],
                            "ability": ref, "slot": slot, "power": power,
                            "reach": float(ab.get("range", 0.0)),
                            "expected": max(hp - power, 0)})
            break                       # one is enough to prove the wiring

    # Gear: equipping a weapon with an atk bonus must make the next hit harder. The
    # stats have been authorable since the beginning and did nothing, so "the manifest
    # says +2 atk" is exactly the claim that needs proving in the engine.
    if arch and arch["kind"] == "top_down_controller" and player and enemy:
        worn = [it for it in (domains.get("items", {}) or {}).get("items", [])
                if it.get("slot") in ("weapon", "armor", "accessory")
                and int((it.get("stats", {}) or {}).get("atk", 0)) > 0]
        if worn:
            item = worn[0]
            bonus = int(item["stats"]["atk"])
            base = int(player.get("stats", {}).get("atk", 0))
            if base > 0:
                out.append({"kind": "gear_bonus", "entity": enemy["id"],
                            "item": item["id"], "slot": item["slot"],
                            "base_atk": base, "bonus": bonus,
                            "expected": base + bonus})

    # Ability cost: spending must reduce the pool, and an ability that cannot be paid
    # for must not fire AND must not burn its cooldown.
    if arch and player:
        pool = int(player.get("stats", {}).get("mp", 0))
        costed = [(i, ability_defs[r]) for i, r in enumerate(player.get("abilities", []))
                  if r in ability_defs and int(ability_defs[r].get("cost", 0) or 0) > 0]
        if pool > 0 and costed:
            slot, ab = costed[0]
            out.append({"kind": "ability_cost", "ability": ab["id"], "slot": slot,
                        "cost": int(ab["cost"]), "pool": pool,
                        "expected": pool - int(ab["cost"])})

    # Loot: drop_tables were authorable from the start and nothing dropped on kill, so
    # "this enemy drops a sword" is the claim to prove. Only assert on a table with a
    # single guaranteed drop -- a weighted roll is not deterministic, and an assertion
    # that passes most of the time is worse than none.
    # Gated on `arch` like the others: a manifest whose control scheme does not resolve
    # will not compile, so there is no build to assert against.
    tables = (domains.get("items", {}) or {}).get("drop_tables", [])
    if arch and enemy:
        for dt in tables:
            if dt.get("enemy_id") != enemy["id"]:
                continue
            drops = dt.get("drops", [])
            if len(drops) == 1 and not int(dt.get("nothing_weight", 0) or 0):
                out.append({"kind": "loot_drop", "entity": enemy["id"],
                            "expected": drops[0]["item_id"]})
            break

    # Walls: the compiled ground was Sprite2D nodes and nothing else, so the player
    # walked over water and stone and the patrol AI's is_on_wall() could never fire.
    # Find a passable cell whose RIGHT neighbour is solid and prove the player stops.
    if arch and arch["kind"] == "top_down_controller":
        wall = _first_wall_pair(domains)
        if wall is not None:
            from_cell, boundary_x = wall
            out.append({"kind": "tile_collision", "from": list(from_cell),
                        "boundary_x": boundary_x})

    # Doors: every exit's baked target scene must load, and its arrival cell must
    # actually move the player. A wrong res:// path is the obvious failure mode and is
    # invisible until someone walks into the doorway.
    levels = (domains.get("levels", {}) or {}).get("levels", [])
    if any(lv.get("exits") for lv in levels):
        start = next((lv for lv in levels if lv.get("exits")), None)
        scene = "main.tscn" if start is levels[0] else f"level_{start['id']}.tscn"
        out.append({"kind": "room_transition", "from_scene": f"res://scenes/{scene}",
                    "doors": len(start.get("exits", []))})
    return out
