# Schemas

JSON Schema (Draft 2020-12) for each manifest domain. These are the enforced contract at the
spec-store boundary — the compiler and generators trust that anything in the store already validated.

| File | Domain | Notes |
|---|---|---|
| `project.schema.json` | project | title, genre, camera (enum), control_scheme (→ mechanics), core_loop, target_resolution |
| `style-contract.schema.json` | style_contract | locked palette + canvas/outline/shading/anchor rules (Phase 0 shape) |
| `narrative.schema.json` | narrative | premise, beats, factions, characters (→ factions) |
| `entities.schema.json` | entities | characters/enemies/npcs with stats, behavior_archetype (→ mechanics), and a `sprite: {archetype, config}` descriptor (dec-0023) |
| `items.schema.json` | items | items with `slot` + `stats` (worn slots equip on pickup and move the player's atk/def), a `sprite` descriptor, rarity_tiers, drop_tables (→ entities.enemies, items) — rolled on kill, with `nothing_weight` as the miss chance |
| `mechanics.schema.json` | mechanics | **parameters over a fixed archetype library**; per-kind typed params via if/then |
| `economy.schema.json` | economy | currency, price_curves, progression_pacing |
| `world.schema.json` | world | regions (biome, tileset_ref, levels) + connections (→ regions) |
| `levels.schema.json` | levels | character-grid maps: legend (char→tile), rows, player_spawn, spawns (→ entities.enemies, items), exits (→ levels) |
| `abilities.schema.json` | abilities | activatable actions over a **fixed kind library** (projectile · melee_arc · heal · dash), with an optional `cost` spent from the caster's `mp` stat; entities reference them by id (→ abilities) |

Arrows (→) are **cross-references** validated by the spec store's `validate_all`, not by JSON Schema
alone: structural validity per domain is necessary but not sufficient for a valid manifest.
