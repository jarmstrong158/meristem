"""Cross-reference validation across domains. Structural (per-domain) validity is
necessary but not sufficient: an item that drops from a nonexistent enemy is a valid
items object and a valid entities object, but an invalid *manifest*."""
from __future__ import annotations


def _ids(seq, key="id"):
    return {e[key] for e in seq if isinstance(e, dict) and key in e}


def _sprite_errors(domains: dict) -> list[str]:
    """Validate each entity/item sprite descriptor against the generator catalog:
    the archetype's build/kind/shape must be a known option, not just schema-valid.
    Soft-imports the generators — if they aren't installed the schema enum still
    guards the archetype name, so this check is simply skipped."""
    try:
        from meristem_generators import validate_sprite
    except Exception:
        return []
    errs: list[str] = []
    entities = domains.get("entities", {}) or {}
    for group in ("characters", "enemies", "npcs"):
        for e in entities.get(group, []):
            sp = e.get("sprite")
            if isinstance(sp, dict) and sp.get("archetype"):
                for p in validate_sprite(sp["archetype"], sp.get("config")):
                    errs.append(f"entity {e.get('id')!r} sprite: {p}")
    for it in (domains.get("items", {}) or {}).get("items", []):
        sp = it.get("sprite")
        if isinstance(sp, dict) and sp.get("archetype"):
            for p in validate_sprite(sp["archetype"], sp.get("config")):
                errs.append(f"item {it.get('id')!r} sprite: {p}")
    return errs


def _level_errors(domains: dict) -> list[str]:
    """Levels must be internally coherent (rectangular rows, legend covers every char,
    spawns in bounds) and resolve their refs (region, enemy/item ids, known tiles)."""
    errs: list[str] = []
    levels = (domains.get("levels", {}) or {}).get("levels", [])
    if not levels:
        return errs
    entities = domains.get("entities", {}) or {}
    enemy_ids = _ids(entities.get("enemies", []))
    item_ids = _ids((domains.get("items", {}) or {}).get("items", []))
    region_ids = _ids((domains.get("world", {}) or {}).get("regions", []))

    try:                                             # tile names the generator can build
        from meristem_generators.procedural import ProceduralGenerator
        known_tiles = set(ProceduralGenerator._TILES)
    except Exception:
        known_tiles = None                           # generators absent -> skip tile check

    seen: set = set()
    for lv in levels:
        lid = lv.get("id")
        if lid in seen:
            errs.append(f"level id {lid!r} is defined more than once")
        seen.add(lid)
        if region_ids and lv.get("region") not in region_ids:
            errs.append(f"level {lid!r} region {lv.get('region')!r} is not a world region")
        rows = lv.get("rows", [])
        legend = lv.get("legend", {})
        w = len(rows[0]) if rows else 0
        for i, row in enumerate(rows):
            if len(row) != w:
                errs.append(f"level {lid!r} row {i} length {len(row)} != row 0 length {w}")
            for ch in row:
                if ch not in legend:
                    errs.append(f"level {lid!r} row {i} uses {ch!r} which is not in the legend")
                    break
        if known_tiles is not None:
            for ch, tile in legend.items():
                if tile not in known_tiles:
                    errs.append(f"level {lid!r} legend {ch!r} -> {tile!r} is not a known tile "
                                f"({sorted(known_tiles)})")
        h = len(rows)
        ps = lv.get("player_spawn", {})
        if ps and (ps.get("x", 0) >= w or ps.get("y", 0) >= h):
            errs.append(f"level {lid!r} player_spawn ({ps.get('x')},{ps.get('y')}) is outside the {w}x{h} grid")
        for sp in lv.get("spawns", []):
            if sp.get("x", 0) >= w or sp.get("y", 0) >= h:
                errs.append(f"level {lid!r} spawn {sp.get('id')!r} ({sp.get('x')},{sp.get('y')}) "
                            f"is outside the {w}x{h} grid")
            pool = enemy_ids if sp.get("kind") == "enemy" else item_ids
            if sp.get("id") not in pool:
                errs.append(f"level {lid!r} {sp.get('kind')} spawn {sp.get('id')!r} does not resolve")

    # world regions listing level ids must have them defined (when levels domain present)
    for r in (domains.get("world", {}) or {}).get("regions", []):
        for lid in r.get("levels", []):
            if lid not in seen:
                errs.append(f"world region {r.get('id')!r} lists level {lid!r} which is not defined in levels")
    return errs


def cross_reference_errors(domains: dict) -> list[str]:
    errs: list[str] = []
    entities = domains.get("entities", {}) or {}
    items = domains.get("items", {}) or {}
    mechanics = domains.get("mechanics", {}) or {}
    world = domains.get("world", {}) or {}
    narrative = domains.get("narrative", {}) or {}
    project = domains.get("project", {}) or {}

    enemy_ids = _ids(entities.get("enemies", []))
    all_entity_ids = enemy_ids | _ids(entities.get("characters", [])) | _ids(entities.get("npcs", []))
    item_ids = _ids(items.get("items", []))
    rarity_ids = _ids(items.get("rarity_tiers", []))
    archetype_ids = _ids(mechanics.get("archetypes", []))
    region_ids = _ids(world.get("regions", []))
    faction_ids = _ids(narrative.get("factions", []))

    # items: drop tables reference real enemies + items; items reference real rarities
    for dt in items.get("drop_tables", []):
        eid = dt.get("enemy_id")
        if eid not in enemy_ids:
            errs.append(f"drop_table references enemy_id {eid!r} which is not in entities.enemies")
        for drop in dt.get("drops", []):
            iid = drop.get("item_id")
            if iid not in item_ids:
                errs.append(f"drop_table for {eid!r} references item_id {iid!r} which is not in items")
    for it in items.get("items", []):
        rar = it.get("rarity")
        if rar is not None and rar not in rarity_ids:
            errs.append(f"item {it.get('id')!r} references rarity {rar!r} which is not in rarity_tiers")

    # entities: behavior archetype must exist
    for group in ("characters", "enemies", "npcs"):
        for e in entities.get(group, []):
            ba = e.get("behavior_archetype")
            if ba is not None and ba not in archetype_ids:
                errs.append(f"entity {e.get('id')!r} behavior_archetype {ba!r} is not a mechanics archetype")

    # project: control scheme must be an archetype (only if mechanics is present)
    cs = project.get("control_scheme")
    if cs is not None and archetype_ids and cs not in archetype_ids:
        errs.append(f"project.control_scheme {cs!r} is not a mechanics archetype")

    # world: connections reference real regions; level ids unique
    for c in world.get("connections", []):
        for end in ("from", "to"):
            rid = c.get(end)
            if rid not in region_ids:
                errs.append(f"world connection {end}={rid!r} is not a region id")
    seen_levels: set = set()
    for r in world.get("regions", []):
        for lvl in r.get("levels", []):
            if lvl in seen_levels:
                errs.append(f"world level id {lvl!r} is used in more than one region")
            seen_levels.add(lvl)

    # narrative: character faction must exist
    for ch in narrative.get("characters", []):
        fac = ch.get("faction")
        if fac is not None and fac not in faction_ids:
            errs.append(f"narrative character {ch.get('id')!r} faction {fac!r} is not a faction id")

    # sprites: each entity/item sprite's variant must be a real generator build
    errs.extend(_sprite_errors(domains))

    # levels: rectangular, legend-covered, refs resolve, spawns in bounds
    errs.extend(_level_errors(domains))

    return errs
