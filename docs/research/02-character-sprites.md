# 02 — 32×32 character sprite construction

*Grounded in real references (sources below), after a reviewer correctly flagged the first hero's
face as broken — a 2×2 black blob dead-center that read as a giant mouth between the eyes. This is
why `build_hero` places the pixels it does.*

## The failure it replaced

The old face was `..0f7f00f7f0..` / `..0f0f00f0f0..` — two eye pixels with a **2×2 black block between
them**. Two compounding errors: (a) the mouth was 4× too big, (b) it sat in the dead center between the
eyes, where the brain reads a mouth — so it dominated the face. There was no facial construction at all.

## Principles (at 32px you draw a *symbol* of a face, not a face)

- **Proportions.** Big head (JRPG/chibi): head ≈ 1/3 of the figure. Leave 1–2px headroom; don't fill 32.
  Row budget used: headroom 0–1, **head+hair 2–13**, neck 14, **torso+arms 15–22**, belt 22,
  **legs 23–28**, feet 29. Head ~10–12px wide, centered on the col 15/16 seam.
- **Eyes are the load-bearing feature.** 1-wide × 2-tall dark dots, **cols 13 & 18, rows 9–10** →
  **4px of skin between them** (the nose bridge) and ~2px outside each. Well-spaced, never centered.
- **Mouth: 1px, or omit.** Here: a tiny mouth 2 rows *below* the eyes (row 12), never between them,
  never 2px+ centered.
- **No nose** at this scale.
- **Less is more.** Every extra dark pixel in the ~8×6px skin window competes with the eyes and muddies
  the face. Build around the eyes and stop.
- **Hair is a silhouette + color block** that frames the face and defines identity — shaped (rounded
  top, sideburns, fringe), with a second shade on the shade side, not a flat helmet box.
- **Shading:** 2–3 shades per material, one light direction (top-left), selective outline (dark, not a
  full black box), internal separations via a material's dark shade.
- **Silhouette first:** the solid-black shape must read as a front-facing person before any detail.

## What `build_hero` emits

A 32×32 front-facing hero drawn with explicit coordinates (not error-prone string grids): shaped brown
hair + a dark-grey shade, an 8px face window with the eyes/mouth above, blue tunic + dark-blue shade +
yellow belt, grey trousers, black boots, selective outline. The walk cycle (dec-0018) is derived from
this idle grid, so the fix flows into the animation automatically.

## Still deferred

Blink frame, more hair volume/shades, per-character palettes and silhouettes (only the one hero exists),
and applying the same rigor to the enemy/NPC sprites.

## Sources

- Slynyrd (Raymond Schlitter) — [Top-Down Character Sprites](https://www.slynyrd.com/blog/2019/10/21/pixelblog-22-top-down-character-sprites) (head ≈ 1/3–1/2; smaller = more abstracted)
- Saint11 / Pedro Medeiros (MiniBoss) — [pixel-art tutorials](https://saint11.art/blog/pixel-art-tutorials/) (portraits, silhouette, shading)
- Sandro Maglione — [pixel-art eyes](https://www.sandromaglione.com/articles/pixel-art-eyes-techniques-and-styles) (per-resolution eye size + spacing)
- jbahamon — [JRPG graphics & sprites](https://jbahamon.github.io/jrpgs/2021/01/22/graphics-and-sprites.html) (FF6 16×24, Chrono Trigger, Pokémon sizes; big-head proportions; faces are eyes-only)
- Stardew Valley Wiki — [Farmer sprite](https://stardewvalleywiki.com/Modding:Farmer_sprite) (16×32, 6×2px eye region)
