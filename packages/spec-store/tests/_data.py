"""Shared test data: a small, internally-consistent manifest."""


def consistent_domains():
    return {
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
