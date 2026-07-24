"""Shared test data: a small, internally-consistent manifest.

It carries every domain in `REQUIRED_DOMAINS` — a manifest missing one of those is
now a validation failure (an absent domain used to pass by simply not being iterated,
then exploded downstream in the compiler with a bare KeyError)."""

from meristem_spec_store.scaffold import DEFAULT_STYLE_CONTRACT


def consistent_domains():
    return {
        "style_contract": DEFAULT_STYLE_CONTRACT,
        "mechanics": {"archetypes": [
            {"id": "topdown", "kind": "top_down_controller", "params": {"move_speed": 120, "accel": 800}}
        ]},
        "project": {"title": "Test", "genre": "adventure", "camera": "top_down",
                    "control_scheme": "topdown", "core_loop": "explore-fight-loot",
                    "target_resolution": {"w": 320, "h": 180}},
        "entities": {"enemies": [
            {"id": "slime", "name": "Slime", "stats": {"hp": 10, "atk": 2},
             "behavior_archetype": "topdown"}
        ]},
        "items": {
            "rarity_tiers": [{"id": "common", "name": "Common", "weight": 1}],
            "items": [{"id": "sword", "name": "Rusty Sword", "slot": "weapon", "rarity": "common"}],
            "drop_tables": [{"enemy_id": "slime", "drops": [{"item_id": "sword", "weight": 1}]}],
        },
        "world": {"regions": [
            {"id": "forest", "biome": "grass", "tileset_ref": "forest_tiles", "levels": ["forest_01"]}
        ]},
    }
