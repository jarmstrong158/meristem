---
name: game-interview
description: Turn a game idea into a valid Meristem manifest through ~5 questions and a strawman the user can mutate. Use when someone wants to start a new 2D game.
---

# Game interview

Your job is to get from "I want to make a game" to a **valid, compilable manifest** with as little
friction as possible. Ask a few questions, scaffold a strawman, then let the user mutate it. **Do not
run a 40-question wizard — question fatigue kills this tool.**

## Step 1 — Ask at most five questions

Ask these conversationally, accept short answers, and infer the rest. If the user already gave an
answer, don't re-ask it.

1. **What's the game?** — a title and a one-line premise ("a cozy farming game", "a dungeon crawler").
2. **Genre / feel?** — one or two words.
3. **How does it play?** — top-down, side-scroller, or turn-based. Map to a control archetype:
   - top-down → `top_down_controller`
   - side-scroller / platformer → `platformer_controller`
   - turn-based → `turn_based_combat`
4. **Who's the protagonist?** — a name.
5. **What's the first enemy?** — a name.

Infer `biome` from the premise (grass, cave, desert, snow…); default `grass`. Don't ask a sixth question.

## Step 2 — Scaffold the strawman

Call the spec-store MCP tool `scaffold_project` with the answers:

```
scaffold_project(title, genre, control, premise, protagonist, enemy, biome)
```

This writes a complete, `validate_all`-clean manifest across all 10 domains (PICO-8 palette, one
region, the protagonist + enemy, a starter weapon, a drop table, a real starter level, and two
starter abilities). It is deliberately generic — that's the point: a valid baseline the user shapes,
not a blank page.

## Step 3 — Present and mutate

Summarize the strawman in plain terms (title, how it plays, the hero, the enemy, the starter item,
the region). Then invite changes. Apply each with a **validated write** — read the domain with
`get_domain`, edit the value, preview with `diff_domain`, then `set_domain`. If a write is rejected,
show the user the reason and fix it; never force an invalid state.

Good mutations to offer: rename things, tweak stats, add an item or enemy, change the biome, adjust
move speed / jump height. Enrich the narrative (premise, beats) with the user's ideas.

**Editing the map.** The scaffold authors a real starter level in the `levels` domain: a
character-grid (`legend` maps one char to a tile, `rows` is the map) plus `player_spawn` and
`spawns` (enemy/item placements at grid cells). To reshape the world, edit those strings —
add a lake (`~`), wall off a path (`#`), move or add enemy spawns, drop an item pickup —
then `set_domain("levels", ...)`. Cross-ref validation catches ragged rows, unknown legend
chars, unknown tiles, out-of-bounds or unresolvable spawns, so mutate freely and re-validate.
Spawned enemies each get their own scene/stats; a spawned item must have a sprite descriptor.

**Connecting rooms.** A level's `exits` are doors: `{x, y, to, to_spawn?}` moves the player to
another level's scene, arriving at `to_spawn` or that level's own `player_spawn`. Every authored
level compiles to its own room, so adding a level and a door each way is all a second room needs.

**Giving something a look.** When you add or reskin an entity/item, set its `sprite: {archetype,
config}` — but **discover the vocabulary first**, don't guess a build. Call `list_sprite_archetypes`
for the live menu (every archetype + its build/kind/shape options + colours), pick one that fits the
fiction (a bat enemy → `{archetype: "flyer", config: {build: "bat"}}`; a boss slime →
`{archetype: "blob", config: {build: "king"}}`), and confirm it with `check_sprite` before the write.
A bogus build (`{build: "dragon"}`) is schema-valid but a `validate_all` cross-ref error — so verify,
don't ship it. No sprite field → the archetype's default build. To *see* a pick before writing it,
call `preview_sprite` — it renders the sprite against this manifest's own style contract.

**Giving something to do.** Abilities are the `abilities` domain, and like mechanics they are
parameters over a fixed kind library — never freeform code:

| kind | what it does | reads |
|---|---|---|
| `projectile` | fires a travelling shot that damages the first enemy it hits | `power`, `speed`, `range`, `sprite` |
| `melee_arc` | damages every enemy in reach, all round | `power`, `range` |
| `heal` | restores the player's hp | `power` |
| `dash` | a burst of movement in the facing direction | `power` (pixels) |

An entity holds them in `abilities: [id, …]`, and **order is significant** — they bind to
`ability_1`, `ability_2`, `ability_3` in that order. Three slots exist; a fourth is refused rather
than compiled into something unreachable. A `kind` the compiler cannot emit is refused too, so an
ability is never bound to a key that silently does nothing.

An optional `cost` is spent from the caster's **`mp` stat** (with `mp_regen` per second refilling
it). An ability that cannot be paid for does not fire *and does not burn its cooldown*. Cross-ref
refuses a `cost` larger than the caster's whole `mp` pool — that ability could never be used once.

**Making gear matter.** An item's `slot` and `stats` are live: picking up something in a worn slot
(`weapon`, `armor`, `accessory`) equips it, and its `stats` move the player's effective `atk` and
`def` — the swing asks `Game.atk()` every time rather than carrying a frozen number. `consumable`
and `key_item` are carried and grant nothing. So `{"slot": "weapon", "stats": {"atk": 2}}` is a real
+2 to every hit, and defence subtracts from incoming damage (a hit always lands for at least 1).

## Step 4 — Hand off

When the user is happy, `validate_all` (must be ok), save the manifest, and tell them to compile:

```
meristem-compile <manifest.json> --out <project-dir>
```

Then they can open the generated Godot project, or run the verifier (`meristem-verify`) to check it
against the spec. Keep them in the loop — this is a human-in-the-loop tool with checkpoints.
