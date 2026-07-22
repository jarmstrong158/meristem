# Schemas

JSON Schema (Draft 2020-12) for each manifest domain. These are the enforced contract at the
spec-store boundary — the compiler and generators trust that anything in the store already validated.

| File | Domain | Notes |
|---|---|---|
| `project.schema.json` | project | title, genre, camera (enum), control_scheme (→ mechanics), core_loop, target_resolution |
| `style-contract.schema.json` | style_contract | locked palette + canvas/outline/shading/anchor rules (Phase 0 shape) |
| `narrative.schema.json` | narrative | premise, beats, factions, characters (→ factions) |
| `entities.schema.json` | entities | characters/enemies/npcs with stats + behavior_archetype (→ mechanics) |
| `items.schema.json` | items | items, rarity_tiers, drop_tables (→ entities.enemies, items) |
| `mechanics.schema.json` | mechanics | **parameters over a fixed archetype library**; per-kind typed params via if/then |
| `economy.schema.json` | economy | currency, price_curves, progression_pacing |
| `world.schema.json` | world | regions (biome, tileset_ref, levels) + connections (→ regions) |

Arrows (→) are **cross-references** validated by the spec store's `validate_all`, not by JSON Schema
alone: structural validity per domain is necessary but not sufficient for a valid manifest.
