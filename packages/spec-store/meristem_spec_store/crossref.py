"""Cross-reference validation across domains. Structural (per-domain) validity is
necessary but not sufficient: an item that drops from a nonexistent enemy is a valid
items object and a valid entities object, but an invalid *manifest*."""
from __future__ import annotations


def _ids(seq, key="id"):
    return {e[key] for e in seq if isinstance(e, dict) and key in e}


def _sprite_errors(domains: dict, skipped: list[str]) -> list[str]:
    """Validate each entity/item sprite descriptor against the generator catalog:
    the archetype's build/kind/shape must be a known option, not just schema-valid.

    `meristem_generators` is a declared dependency, so it should always be importable.
    If it genuinely isn't (a broken/partial install), the check cannot run — and that
    is RECORDED in `skipped` rather than silently returning "no errors". A skipped
    check must never be reported as a passed check."""
    try:
        import meristem_generators as _gen
    except ImportError as e:
        skipped.append(
            f"sprite_archetypes: meristem_generators is not importable ({e}); "
            "entity/item sprite configs were NOT cross-checked against the generator catalog")
        return []
    validate_sprite = _gen.validate_sprite   # renamed away -> AttributeError, loudly
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
    for ab in (domains.get("abilities", {}) or {}).get("abilities", []):
        sp = ab.get("sprite")
        if isinstance(sp, dict) and sp.get("archetype"):
            for p in validate_sprite(sp["archetype"], sp.get("config")):
                errs.append(f"ability {ab.get('id')!r} sprite: {p}")
    return errs


def _ability_errors(domains: dict, skipped: list[str]) -> list[str]:
    """Abilities must be internally coherent and every entity reference must resolve.
    A projectile also needs the numbers that make it a projectile — without speed and
    range it has no way to travel, and defaulting those silently would ship an ability
    that looks authored and does not behave as specified."""
    errs: list[str] = []
    abilities = (domains.get("abilities", {}) or {}).get("abilities", [])
    seen: set = set()
    for ab in abilities:
        aid = ab.get("id")
        if aid in seen:
            errs.append(f"ability id {aid!r} is defined more than once")
        seen.add(aid)
        if ab.get("kind") == "projectile":
            for key in ("speed", "range"):
                if ab.get(key) is None:
                    errs.append(f"ability {aid!r} is a projectile but has no {key}")
            if not ab.get("sprite"):
                errs.append(f"ability {aid!r} is a projectile but has no sprite to fire")
        elif ab.get("kind") == "melee_arc" and ab.get("range") is None:
            errs.append(f"ability {aid!r} is a melee_arc but has no range")

    entities = domains.get("entities", {}) or {}
    for group in ("characters", "enemies", "npcs"):
        for e in entities.get(group, []):
            for ref in e.get("abilities", []):
                if ref not in seen:
                    errs.append(f"entity {e.get('id')!r} references ability {ref!r} "
                                f"which is not in the abilities domain")
    return errs


def _level_errors(domains: dict, skipped: list[str]) -> list[str]:
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
        import meristem_generators.procedural as _proc
    except ImportError as e:                         # generators absent -> record the gap
        known_tiles = None
        skipped.append(
            f"level_tiles: meristem_generators is not importable ({e}); "
            "level legend tile names were NOT cross-checked against the generator")
    else:
        # A PUBLIC accessor on purpose: this used to read the private
        # ProceduralGenerator._TILES behind a bare `except Exception`, so renaming it
        # would have quietly turned this check into a no-op. Now a rename raises.
        known_tiles = set(_proc.known_tiles())

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

    # exits: a door must sit on its own grid, point at a real level, and land the player
    # somewhere inside THAT level. Checked in a second pass so a door may target a level
    # defined later in the array.
    sizes = {lv.get("id"): (len(lv.get("rows", [{}])[0]) if lv.get("rows") else 0,
                            len(lv.get("rows", [])))
             for lv in levels}
    for lv in levels:
        lid = lv.get("id")
        w, h = sizes.get(lid, (0, 0))
        for ex in lv.get("exits", []):
            if ex.get("x", 0) >= w or ex.get("y", 0) >= h:
                errs.append(f"level {lid!r} exit ({ex.get('x')},{ex.get('y')}) is outside "
                            f"the {w}x{h} grid")
            target = ex.get("to")
            if target not in seen:
                errs.append(f"level {lid!r} exit leads to {target!r} which is not a defined level")
                continue
            if target == lid:
                errs.append(f"level {lid!r} exit leads to itself")
            ts = ex.get("to_spawn")
            if ts:
                tw, th = sizes.get(target, (0, 0))
                if ts.get("x", 0) >= tw or ts.get("y", 0) >= th:
                    errs.append(f"level {lid!r} exit to {target!r} arrives at "
                                f"({ts.get('x')},{ts.get('y')}), outside that level's {tw}x{th} grid")

    # world regions listing level ids must have them defined (when levels domain present)
    for r in (domains.get("world", {}) or {}).get("regions", []):
        for lid in r.get("levels", []):
            if lid not in seen:
                errs.append(f"world region {r.get('id')!r} lists level {lid!r} which is not defined in levels")
    return errs


def cross_reference(domains: dict) -> tuple[list[str], list[str]]:
    """Return (errors, checks_skipped). A check lands in `checks_skipped` when it could
    not run at all — the caller must surface that, because "no errors found" and "the
    check never ran" are different outcomes and only one of them is a pass."""
    skipped: list[str] = []
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
    errs.extend(_sprite_errors(domains, skipped))

    # abilities: coherent per kind, and every entity reference resolves
    errs.extend(_ability_errors(domains, skipped))

    # levels: rectangular, legend-covered, refs resolve, spawns in bounds
    errs.extend(_level_errors(domains, skipped))

    return errs, skipped


def cross_reference_errors(domains: dict) -> list[str]:
    """Errors only. Prefer `cross_reference`, which also reports skipped checks."""
    return cross_reference(domains)[0]
