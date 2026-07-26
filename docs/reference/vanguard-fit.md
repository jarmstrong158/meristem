# Sim test: building a real Vanguard scene with Meristem

A fit test, not a demo. [Vanguard](https://github.com/jarmstrong158/vanguard) is a GBA-era
turn-based JRPG with ~15 built overworld maps, a full battle engine and a finished 3-act design
doc set. The question was whether Meristem could take content from those docs — unchanged — and
compile it into something that runs.

**Scene chosen:** Act 1, 1-7 *The Greenweald Detour* — an optional marsh dungeon with agitated
wildlife, ending at Tova's empty cottage where Lida's rod is found. Picked because Vanguard's
overworld is top-down, which is the one control scheme Meristem's compiler emits.

The result is [`examples/vanguard-greenweald/`](../../examples/vanguard-greenweald/), built from
`quest_scene_list.md` 1-7, `enemy_design.md` section 7, `items_equipment.md` and
`second_pass_resolutions.md`.

![the compiled Greenweald marsh](vanguard-greenweald.png)

## What transferred, unchanged

| Vanguard content | Meristem | Notes |
|---|---|---|
| Marsh Viper (18 hp, 6 atk, 2 def) | `serpent` / `viper` | E1 stat line used verbatim |
| Bog Toad | `blob` / `slime` | no toad archetype; see gaps |
| Plains Wolf (22/7/3) | `quadruped` / `wolf` | |
| Thornwall Kestrel (16/5/2) | `flyer` / `bird` | |
| Mud Puddle (28/3/5) | `blob` / `ooze` | |
| Thornbug (25/5/6) | `beetle` / `beetle` | |
| Carved Rod, Militia Sword, Linen Tunic, Power Band | items with `slot` + `stats` | the rod is the documented 1-7 reward |
| Medicinal herbs as the marsh reward | `drop_tables` with `nothing_weight` | herbs drop from vipers and toads |
| Conduit Pulse / Mend | `projectile` / `heal` abilities with `mp` cost | |
| The marsh itself | `water` tiles, which are solid | ponds became real barriers |
| Tova's cottage | a second level plus a door each way | |
| Currency "Marks" | `economy.currency` | authored, but see gaps |

**44 assets generated, gated and provenance-tagged with no hand-drawing**, and all six enemy
families mapped onto archetypes that already existed. `validate_all` passed on the first run.

The compiled project imports and runs in Godot 4.6 with no script errors, and all **seven engine
assertions pass** against Vanguard's own numbers:

```
move_speed       72.0 measured 72.0
melee_damage     marsh_viper 18 -> 14   (Maren's atk 4)
ability_damage   conduit_pulse 18 -> 13 (power 5)
gear_bonus       carved_rod   atk 4 -> 8
ability_cost     mp 18 -> 15            (cost 3)
tile_collision   stopped at 298.99 against a wall at 304
room_transition  door -> level_tova_cottage.tscn, arrival applied
```

## What could not be expressed

Ordered by how much it matters for Vanguard specifically.

1. **Turn-based combat.** Vanguard's core. The compiler emits `top_down_controller` only and
   explicitly refuses `turn_based_combat`, so the scene had to be reinterpreted as real-time
   action. Everything below is downstream of this being a different game.
2. **The `mag` stat.** Vanguard entities are hp/atk/def/**mag**/spd, and Maren is a MAG-based
   support whose rod grants +MAG. Meristem consumes hp/atk/def only, so the rod's +4 MAG had to
   be authored as +4 atk — which changes what the item *means*.
3. **Elements and resistances.** Fire/ice/dark/earth/wind and per-enemy resistance profiles are
   central to Vanguard's encounter design. No concept exists in any schema.
4. **Status effects.** Marsh Viper's *Fang Strike* (20% Poison), Plains Wolf's *Snarl* (ATK
   debuff), Mud Puddle's *Stick* (SPD debuff) — every region-1 enemy has one, and none can be
   expressed. Enemies reduce to hp/atk plus a movement AI.
5. **Enemy abilities at all.** Related but distinct: `abilities` can only be bound to the player.
   An enemy may reference them in the schema, and nothing reads it.
6. **NPCs and dialog.** `entities.npcs` validates and the compiler never reads it. Tova's cottage
   is the emotional point of the scene and compiles to an empty room with loot in it.
7. **The party.** Vanguard runs Maren + Kael + Lida with followers on the overworld. Meristem has
   exactly one player character.
8. **Shops and economy.** The `economy` domain is authored and entirely unread, so "Marks" is
   decoration and the Thornwall General shop cannot exist.
9. **Bonds (BND), Attunements, job trees.** Vanguard's signature systems. Deeply specific, and
   correctly out of scope for a general tool — noted for completeness.
10. **No toad archetype.** Bog Toad became a green `blob`. The sprite library covers 6 of the 6
    region-1 families only because five were already close matches.

## The architectural finding

**Meristem output cannot be dropped into Vanguard.** They disagree at the scene level:

| | Vanguard | Meristem |
|---|---|---|
| ground | `TileMapLayer` | Sprite2D grid + one `Walls` body, built at runtime |
| player | `scenes/overworld/player.tscn` | its own `player.tscn` |
| actors | `npc.tscn`, `party_follower.tscn`, `save_crystal.tscn`, `transition_zone.tscn` | enemies, pickups, doors |
| per-map logic | a script per map (`scripts/overworld/*.gd`) | one shared `world.gd` |
| state | Vanguard's own autoloads | a generated `Game` autoload |

Meristem compiles a *whole standalone game*, not importable content. The one pipeline that does
work between them is **sprites** — already proven, when Meristem generated Vanguard's full
43-enemy bestiary as battle sheets.

So the honest summary: Meristem can build *a* Greenweald, and it did. It cannot build *Vanguard's*
Greenweald, and the gap is not art or level data — it is turn-based combat, stats, elements,
status effects and NPCs.

## What this suggests for Meristem

The gaps that are worth closing as a **general** tool, in rough value order:

- **A `mag`-style second offence stat**, or arbitrary stats reaching the runtime. Today only
  `atk`/`def` are consumed, so any item or entity built around a third stat silently does nothing.
  This is the cheapest fix with the widest reach.
- **Status effects** as a fixed archetype library (poison / slow / weaken), the same shape as
  ability kinds. Nearly every action RPG needs them, and enemies currently have no way to be
  interesting beyond a movement pattern.
- **Enemy abilities** — reuse the ability runner rather than inventing a second system.
- **NPCs and dialog**, even minimally. `entities.npcs` already validates and reads as supported.
  That is the most misleading gap in the schema today.
- **A second controller** (`platformer_controller` has a schema and no template). Turn-based is a
  much larger piece and arguably a different product.

## Reproducing

```
python -m meristem_compiler examples/vanguard-greenweald/manifest.json --out build/greenweald
```

Then open `build/greenweald` in Godot 4.6, or run the assertion loop with `meristem-verify`.
