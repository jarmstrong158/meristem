---
name: pixel-art
description: Build and edit Meristem sprites to the studio standard — hue-shifted material ramps, archetype recipes, and a render-and-judge-by-eye loop. Free and editor-optional. Use whenever creating, improving, or fixing any sprite/tile/asset.
---

# Pixel-art — the Meristem sprite standard

Free, deterministic, no paid editor. Every sprite is built the same way, **judged by eye**, and
**grounded in references** — never guessed. This skill is how a person (or Claude) makes a sprite that
actually looks good, not just one that passes the gate.

## The standard (non-negotiable)

- **Materials → 3-shade hue-shifted ramps.** Each material has a base color; derive **shadow (shift
  cool, toward blue/purple, darker)** and **highlight (shift warm, toward yellow, lighter)** via
  `shading.Ramp` — never plain-darken, never grey (grey reads dirty). A brown with no ramp is why hair
  looks like a helmet.
- **One light direction: top-left.** Highlights on top/left edges, shadows bottom/right, a cast shadow
  under the hairline/chin/belt. *Tiles are the exception* — they use the ramp for **texture**
  (speckle/ripple), never a directional bevel, so they stay seamlessly tileable.
- **Selective outline:** a material's darkest shade, not pure black; pure black only on the outer
  silhouette against transparency.
- **Color budget: ≤15 per sprite** (SNES/GBA). One material = 3 shades, so a character tops out at ~5
  materials (skin/hair/shirt/pants/hat) + the shared outline. When a hat leaves hair showing, all five
  ramps are live at exactly 15 — **ornament with an existing ramp shade (`hat.highlight`), never a new
  literal colour**, or it overflows to 16 and fails the gate. Share shades to fit more (outline = a
  material's dark; boot = pants shadow).
- **Silhouette first:** the solid-black shape must read as the thing before any interior detail.

## Archetypes, not one-offs (parameters over a fixed library)

A new creature/item is **config on an archetype**, never new hand-drawing. The library is a
**registry** (`packages/generators/meristem_generators/archetypes.py`) — 13 archetypes today:

| archetype | class | build/kind/shape options | animated |
|-----------|-------|--------------------------|----------|
| `humanoid` | character | hair short/long/ponytail/spiky/bald · beard none/short/full · hat none/cap/wizard/helmet/crown | walk |
| `blob` | enemy | slime · king · cube · ooze | squash |
| `ghost` | enemy | ghost · wisp · specter | float |
| `quadruped` | enemy | dog · wolf · boar · cat | breathe |
| `flyer` | enemy | bat · bird · moth | flap |
| `serpent` | enemy | cobra · snake · viper | tongue/sway |
| `spider` | enemy | spider · tarantula · widow | leg-twitch |
| `weapon` | item_icon | sword·dagger·greatsword·axe·spear·staff·bow·mace·wand | — |
| `consumable` | item_icon | flask·bottle·vial·scroll·pouch | — |
| `pickup` | item_icon | coin·heart·key·gem·ring·skull·star | coin spin |
| `projectile` | item_icon | arrow·fireball·bolt·knife·shuriken | — |
| `chest` | item_icon | wood·iron·gold·crystal (×open) | — |
| `tile` | terrain_tile | grass·dirt·water·stone·sand·snow·lava·brick | — |

- **humanoid** is LPC-layered: one shared `Pose` per frame + z-ordered layers (body→pants→shirt→
  hair→face→beard→hat); a per-character palette is just `config`; new gear/hats = new layers that
  **animate for free**. → `humanoid.py`
- **Discover before you draw.** Never guess a build name — call the MCP tool
  `list_sprite_archetypes` (or `sprite_catalog()` in `catalog.py`) for the live menu, and
  `check_sprite(archetype, config)` to confirm a pick. A typo'd build is a `validate_all` error, not
  a silent fallback (the archetype is an enum; `build`/`kind`/`shape` are free config the catalog
  polices).
- **See the whole library** at a glance: `docs/reference/library.png` (regenerate with
  `python tools/contact_sheet.py`).

**Adding a variant vs a new archetype:** a *variant* (a new sword, a new build) is one builder
function + a dispatch-table entry — no schema change. A *new archetype* (a genuinely new topology,
e.g. the spider's legs) is a generator file **plus both schema `sprite.archetype` enum entries** (the
enum-sync test enforces registry↔schema parity). Reach for a variant first.

## Animation is a registry property

An archetype's motion rides its `frames` function — you don't hand-animate. Two mechanisms, chosen by
whether the motion **deforms the silhouette**: a **builder param knob** (blob `squash`, quad
`head_dy`, flyer `wing_dy`) for non-rigid motion, or a **palette-safe transform** of the static
sprite (`sprite.translate` bob, `sprite.squeeze_h` NEAREST spin) for rigid motion. **Frame 0 always
== the static build**, so the idle PNG and the animation's first frame are identical. Keep frames
palette-safe — a transform that invents a colour or soft alpha fails the gate.

## The loop that actually works (this is the skill)

1. **Author** params/pixels — coordinate-based (string grids are error-prone; that's how a mis-drawn
   mouth-blob got in).
2. **Render to PNG and LOOK** — at **1× (native)** *and* 2× *and* on a labelled pixel grid.
3. **Judge by eye.** The asset gate checks *conformance* (palette/alpha/canvas/budget), **not quality**.
   "Passes the gate" ≠ "looks good."
4. **Iterate 1px at a time.** Re-render, re-look. Stop when it reads at 1×.

## Ground in references — don't invent

- Read the research notes before drawing that thing: `docs/research/01-walk-cycle.md`,
  `02-character-sprites.md`, `03-quadruped.md` (the two-biped depth trick + the ≥3px leg-gap rule),
  and the Vanguard `sprite_style_guide.md` principles (hue-shift, 3 shades, top-left light, sel-out).
- `docs/reference/vanguard-comparison.md` — how the standard maps onto a real GBA-style RPG, and the
  known Meristem gaps it surfaced (per-material sel-out has a colour-budget tradeoff; no raptor/beetle
  archetype yet).
- **Study** (never ship) the LPC Universal Spritesheet Generator's layer/z-index/animation schema for
  layered animated humanoids.
- Ground shippable art on **CC0 only (Kenney.nl)**. Spriters Resource / LPC / RPG-Maker pixels are
  **study-only** (copyright/copyleft).

## Low-res face checklist (learned the hard way)

- Eyes = **1×2 dark dots, well-spaced** (≈4px of skin between). **Never** a centered blob between them.
- Mouth = **1px below the eyes, or omit**. No nose at 32px.
- Hair = tapered shape + warm highlight on top + cool hairline cast shadow + 3 real browns — not a flat
  helmet, not a grey stripe.
- No orphan pixels; one light direction; ≤3 shades per material.

## Hand-editing (free editor path)

Generated assets are plain, editable PNGs you own. To hand-tune a sprite, open it in **Pixelorama**
(free, MIT — the recommended editor) or **LibreSprite** (free). *Do not require Aseprite (paid).* Open
an asset by passing it to the Pixelorama binary (`Pixelorama.exe path/to/asset.png`); the installed
path on a given machine is recorded in `docs/environment.md`.

After editing, re-run the gate to re-validate the edit stays within the standard:

```
asset-gate validate <asset.png> --class <class> --contract <style-contract.json>
```

The gate accepts hand-edits that hold the budget / hard-alpha / canvas, and rejects with a specific
reason otherwise — so you can edit freely and know instantly if you broke the contract.
