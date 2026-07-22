"""Cross-reference validation across domains. Structural (per-domain) validity is
necessary but not sufficient: an item that drops from a nonexistent enemy is a valid
items object and a valid entities object, but an invalid *manifest*."""
from __future__ import annotations


def _ids(seq, key="id"):
    return {e[key] for e in seq if isinstance(e, dict) and key in e}


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

    return errs
