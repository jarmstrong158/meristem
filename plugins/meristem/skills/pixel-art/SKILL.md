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
- **Color budget: ≤15 per sprite** (SNES/GBA). Share shades to fit (outline = eye color; boot = pants
  shadow).
- **Silhouette first:** the solid-black shape must read as the thing before any interior detail.

## Archetypes, not one-offs (parameters over a fixed library)

A new creature is **params on an archetype**, not new hand-drawing. Before drawing from scratch, reach
for — or extend — an archetype:

- **humanoid** = LPC layered: one shared skeleton (`Pose` per frame) + z-ordered layers (body → pants →
  shirt → hair → face → gear); a per-character palette is just a `config`; new gear/hats = new layers
  that animate for free. → `packages/generators/meristem_generators/humanoid.py`
- **blob/creature, weapon, consumable, container, tile** = parametric recipes → `agent_drawn.py`,
  `procedural.py`.

## The loop that actually works (this is the skill)

1. **Author** params/pixels — coordinate-based (string grids are error-prone; that's how a mis-drawn
   mouth-blob got in).
2. **Render to PNG and LOOK** — at **1× (native)** *and* 2× *and* on a labelled pixel grid.
3. **Judge by eye.** The asset gate checks *conformance* (palette/alpha/canvas/budget), **not quality**.
   "Passes the gate" ≠ "looks good."
4. **Iterate 1px at a time.** Re-render, re-look. Stop when it reads at 1×.

## Ground in references — don't invent

- Read `docs/research/01-walk-cycle.md`, `docs/research/02-character-sprites.md`, and the Vanguard
  `sprite_style_guide.md` principles (hue-shift, 3 shades, top-left light, sel-out).
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
(free, MIT — the recommended editor) or **LibreSprite** (free). *Do not require Aseprite (paid).* After
editing, re-run the gate to re-validate the edit stays within the standard:

```
asset-gate validate <asset.png> --class <class> --contract <style-contract.json>
```

The gate accepts hand-edits that hold the budget / hard-alpha / canvas, and rejects with a specific
reason otherwise — so you can edit freely and know instantly if you broke the contract.
