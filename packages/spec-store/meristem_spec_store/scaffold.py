"""Scaffold a valid strawman manifest from a few high-level answers.

The game-interview skill asks ~5 questions; this turns the answers into a complete,
cross-reference-consistent manifest across all 8 domains that `validate_all` accepts.
The model then enriches it — but it is never structurally invalid, and never starts
from a blank page."""
from __future__ import annotations

from .store import SpecStore

# PICO-8 (CC0) default locked palette — dec-0006.
_PICO8 = [
    ("#000000", "black"), ("#1D2B53", "dark_blue"), ("#7E2553", "dark_purple"),
    ("#008751", "dark_green"), ("#AB5236", "brown"), ("#5F574F", "dark_grey"),
    ("#C2C3C7", "light_grey"), ("#FFF1E8", "white"), ("#FF004D", "red"),
    ("#FFA300", "orange"), ("#FFEC27", "yellow"), ("#00E436", "green"),
    ("#29ADFF", "blue"), ("#83769C", "lavender"), ("#FF77A8", "pink"), ("#FFCCAA", "peach"),
]

DEFAULT_STYLE_CONTRACT = {
    "name": "pico8-default-v1", "version": 1,
    "palette": {"source": "PICO-8 (Lexaloffle)", "license": "CC0",
                "colors": [{"i": i, "hex": h, "name": n} for i, (h, n) in enumerate(_PICO8)],
                # all sprites use per-material hue-shifted ramps (dec-0020/0021),
                # validated against a colour budget, not this locked palette:
                "free_classes": ["character", "enemy", "item_icon", "ui_element", "terrain_tile"],
                "max_colors": 15},
    "canvas": {"terrain_tile": {"w": 16, "h": 16}, "character": {"w": 32, "h": 32},
               "enemy": {"w": 32, "h": 32}, "item_icon": {"w": 16, "h": 16},
               "ui_element": {"w": 16, "h": 16}},
    "outline": {"policy": "selective_dark_1px", "color_rule": "darkest_shade_of_subject_ramp",
                "fallback_color_index": 0},
    "shading": {"ramp_steps": 3, "light_direction": "top_left"},
    "anchor": {"terrain_tile": "top_left", "character": "bottom_center", "enemy": "bottom_center",
               "item_icon": "center", "ui_element": "center"},
    "background": {"mode": "transparent", "alpha": "hard"},
    "grid": {"base_unit": 16},
    "naming": {"convention": "{class}_{name}[_{variant}].png",
               "class_prefixes": {"terrain_tile": "tile", "character": "char", "enemy": "enemy",
                                  "item_icon": "icon", "ui_element": "ui"}},
    "asset_set": [{"class": "terrain_tile", "name": n} for n in ("grass", "dirt", "water", "stone")],
}

_PARAMS = {
    "top_down_controller": {"move_speed": 80, "accel": 600, "friction": 400, "diagonal_normalized": True},
    "platformer_controller": {"move_speed": 110, "accel": 900, "jump_height": 48, "gravity": 980,
                              "coyote_time": 0.1, "jump_buffer": 0.1, "air_control": 0.6},
    "turn_based_combat": {"initiative_stat": "spd", "damage_formula": "atk_minus_def",
                          "crit_chance": 0.05, "crit_multiplier": 1.5},
}
_CAMERA_FOR = {"top_down_controller": "top_down", "platformer_controller": "side",
               "turn_based_combat": "top_down"}


def strawman(*, title: str = "Untitled", genre: str = "adventure",
             control: str = "top_down_controller", premise: str = "A hero sets out on a journey.",
             protagonist: str = "Hero", enemy: str = "Slime", biome: str = "grass") -> dict:
    """Return a complete, validate_all-clean set of domains."""
    if control not in _PARAMS:
        raise ValueError(f"unknown control {control!r}; known: {sorted(_PARAMS)}")
    return {
        "style_contract": DEFAULT_STYLE_CONTRACT,
        "mechanics": {"archetypes": [{"id": "main", "kind": control, "params": _PARAMS[control]}]},
        "project": {"title": title, "genre": genre, "camera": _CAMERA_FOR[control],
                    "control_scheme": "main", "core_loop": "explore, face enemies, grow stronger",
                    "target_resolution": {"w": 320, "h": 180}},
        "narrative": {"premise": premise,
                      "beats": ["the journey begins", "the first challenge", "a turning point"],
                      "factions": [{"id": "allies", "name": "Allies"}],
                      "characters": [{"id": "player", "name": protagonist, "role": "protagonist",
                                      "faction": "allies"}]},
        "entities": {
            "characters": [{"id": "player", "name": protagonist,
                            "stats": {"hp": 20, "atk": 4, "def": 2, "spd": 6},
                            "behavior_archetype": "main", "sprite": {"archetype": "humanoid"}}],
            "enemies": [{"id": "slime", "name": enemy, "stats": {"hp": 8, "atk": 2, "def": 1, "spd": 3},
                         "behavior_archetype": "main", "sprite": {"archetype": "blob"}}]},
        "items": {"rarity_tiers": [{"id": "common", "name": "Common", "weight": 1}],
                  "items": [{"id": "sword", "name": "Starter Sword", "slot": "weapon",
                             "rarity": "common", "stats": {"atk": 2},
                             "sprite": {"archetype": "weapon", "config": {"kind": "sword"}}}],
                  "drop_tables": [{"enemy_id": "slime", "drops": [{"item_id": "sword", "weight": 1}]}]},
        "economy": {"currency": {"name": "Coins", "symbol": "C"},
                    "progression_pacing": {"xp_curve": "linear", "levels": 10}},
        "world": {"regions": [{"id": "start_region", "biome": biome, "tileset_ref": "start_tiles",
                               "levels": ["level_01"]}]},
        # a real authored starter map (legend + rows), immediately hand-editable:
        # two slimes to fight and the starter sword placed as a pickup.
        "levels": {"levels": [{
            "id": "level_01", "region": "start_region",
            "legend": {".": biome if biome in ("grass", "dirt", "sand", "snow") else "grass",
                       "=": "dirt", "~": "water", "#": "stone"},
            "rows": [
                "....................",
                "....................",
                ".............~~~~...",
                ".............~~~~...",
                "....................",
                "....................",
                "====================",
                "====================",
                "....................",
                "..##................",
                "..##................",
                "....................",
            ],
            "player_spawn": {"x": 4, "y": 5},
            "spawns": [
                {"id": "slime", "kind": "enemy", "x": 13, "y": 8},
                {"id": "slime", "kind": "enemy", "x": 16, "y": 4},
                {"id": "sword", "kind": "item", "x": 7, "y": 10},
            ],
        }]},
    }


def scaffold_store(**answers) -> SpecStore:
    """Build a SpecStore from strawman answers, validated. Raises if inconsistent."""
    store = SpecStore()
    for domain, value in strawman(**answers).items():
        store.set_domain(domain, value, {"actor": "scaffold", "reason": "game-interview strawman"})
    report = store.validate_all()
    if not report.ok:
        raise RuntimeError(f"scaffold produced an invalid manifest: {report.to_dict()}")
    return store
