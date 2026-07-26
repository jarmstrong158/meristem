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
  under the hairline/chin/belt. *Tiles are the exception* — they use the ramp for **texture and
  structure**, never a directional bevel, so they stay seamlessly tileable (see **Tiles are a torus**).
- **Selective outline:** a material's darkest shade, not pure black; pure black only on the outer
  silhouette against transparency.
- **No colour-count limit.** The gate does not cap colours — a tight ≤15 SNES/GBA palette is a *style
  choice*, not a rule. Still prefer discipline for cohesion: one material = a 3-shade hue-shifted ramp,
  reuse an existing ramp shade for small ornament (`hat.highlight`) rather than a scattered new literal,
  and share shades where natural (outline = a material's dark; boot = pants shadow). Restraint reads as
  "one artist"; sprawl reads as noise. Discipline by taste, not by a hard budget.
- **Silhouette first:** the solid-black shape must read as the thing before any interior detail —
  and it must read as a *different* thing from its sibling variants. See **Distinctness is silhouette**.

## Archetypes, not one-offs (parameters over a fixed library)

A new creature/item is **config on an archetype**, never new hand-drawing. The library is a
**registry** (`packages/generators/meristem_generators/archetypes.py`) — 15 archetypes today
(the live list is always `list_sprite_archetypes`; this table is a reading aid):

| archetype | class | build/kind/shape options | animated |
|-----------|-------|--------------------------|----------|
| `humanoid` | character | hair short/long/ponytail/spiky/bald · beard none/short/full · hat none/cap/wizard/helmet/**hood**/crown · **held** none/staff/rod/flamestaff/shield/daggers · **garment** none/apron/scarf/cloak · **feet** boots/bare · **arms** normal/stone · **hair_accent** none/flora | walk |
| `blob` | enemy | slime · king · cube · ooze | squash |
| `ghost` | enemy | ghost · wisp · specter | float |
| `quadruped` | enemy | dog · wolf · boar · cat | breathe |
| `flyer` | enemy | bat · bird · moth | flap |
| `serpent` | enemy | cobra · snake · viper | tongue/sway |
| `spider` | enemy | spider · tarantula · widow | leg-twitch |
| `raptor` | enemy | raptor · drake · roc | idle |
| `beetle` | enemy | beetle · mite · scorpion | idle |
| `weapon` | item_icon | sword·dagger·greatsword·axe·spear·staff·bow·mace·wand | — |
| `consumable` | item_icon | flask·bottle·vial·scroll·pouch | — |
| `pickup` | item_icon | coin·heart·key·gem·ring·skull·star | coin spin |
| `projectile` | item_icon | arrow·fireball·bolt·knife·shuriken | — |
| `chest` | item_icon | wood·iron·gold·crystal (×open) | — |
| `tile` | terrain_tile | grass·dirt·water·stone·sand·snow·lava·brick | — |

- **humanoid** is LPC-layered: one shared `Pose` per frame + z-ordered layers (body→pants→feet→shirt→
  arms→garment→hair→accent→face→beard→hat→held); a per-character palette is just `config`; new
  gear/hats = new layers that **animate for free**. → `humanoid.py`
- **Distinctness is SILHOUETTE, not palette.** Two characters who differ only in `skin`/`hair`/`shirt`
  colour read as recolours of one body — the fix is a **prop/accessory layer**, not another hue. The
  humanoid archetype carries these as config knobs, each grounded in what the character actually
  carries or wears:
  - `held`: **staff · rod · flamestaff · shield · daggers** — a held item, coloured by `held_color`.
    Rides the hand/leg offset so it swings with the walk; drawn front-most and caught by the one shared
    outline pass (never self-outline a prop — draw it *before* `cv.outline`).
  - `garment`: **apron · scarf · cloak** (`garment_color`) — over-clothing on top of the shirt.
  - `feet`: **bare** overrides the baked boots with skin (barefoot monks, etc).
  - `arms`: **stone** overlays the exposed forearms with a `arm_color` ramp (reinforced/stone skin).
  - `hair_accent`: **flora** tucks sprigs into the hair; `hat: hood` frames the face for a rogue.
  Adding the *next* prop (a quiver, a book, pauldrons) is one builder function + one dispatch-table
  entry + one `catalog.py` line — the same variant recipe as a new sword, and it animates for free.
- **Discover before you draw.** Never guess a build name — call the MCP tool
  `list_sprite_archetypes` (or `sprite_catalog()` in `catalog.py`) for the live menu, and
  `check_sprite(archetype, config)` to confirm a pick. A typo'd build is a `validate_all` error, not
  a silent fallback (the archetype is an enum; `build`/`kind`/`shape` are free config the catalog
  polices). `check_sprite` also returns **`warnings`** for config *keys* the archetype does not read —
  `shpae`, or a British `hat_colour`. Those cannot fail a build; they are silently ignored and the
  default renders, so read them.
- **Colour defaults are per variant where the colour is part of the identity.** `pickup` resolves
  `color` per shape — a heart is red, a gem blue, a skull bone — because one global gold produced a gold
  heart and a gold star. Passing `color` explicitly still wins.
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

## Distinctness is silhouette — *between* variants too

Two builds of the same archetype that share an outline read as **the same creature twice**, however
different their palette or interior detail. This is the single most expensive mistake the library has
made, twice:

- `quadruped` dog/wolf/boar/cat were one hardcoded body loaf with ±1px of ear and leg. Closest pair:
  46px of silhouette difference, most of it tail.
- `flyer` bird and moth were the same ellipse pair, separated only by interior feather lines — which
  are invisible in a 32px silhouette.

Both passed their tests the whole time, because those tests asserted the two renders were not
**byte-equal** — which a single pixel satisfies. **A byte-difference test is not a distinctness test.**

So: a variant must reshape the **subject**, not decorate it. A quadruped build declares `back`/`belly`
knots that become the torso outline; a wing kind has its own outline, not just its own shading.
Appendages decorate a silhouette, they do not create one.

**Check it by looking at masks, not art:** `compare_builds` renders every variant of an archetype as a
labelled strip of alpha masks. Colour and interior detail actively *hide* outline collisions, which is
why that view defaults to silhouettes.

## Tiles are a torus

Two hard rules, both learned from shipped bugs that a single-tile thumbnail cannot show:

- **Every feature must WRAP, never clamp.** Draw through the wrap-safe `_put`/`_disc` in
  `procedural.py`. The crack walk used to clamp (`min(w-1, max(0, x))`), so a crack running off an edge
  piled its remaining pixels against the border — a dark smudge that repeated at *every* tile boundary.
- **A periodic feature's period must DIVIDE the tile.** `_wave` stepped 3 rows into a 16px tile, so its
  courses landed at rows 0,3,…,15 and the last sat 1px from the next tile's first. Take the spacing from
  a named constant (`WAVE_PERIOD`, `RIPPLE_PERIOD`) that a test asserts divides the canvas.

**Always inspect a tile laid out 3×3**, never alone — both bugs above are invisible in one tile and
obvious in nine.

Speckle alone cannot distinguish two materials: grass, dirt, sand, snow and stone were one white-noise
field at five densities, so every soft surface read as the same gravel. Give each material **structure**
(blades, pebbles, ripples, drifts, fissures) — and prefer inverting the figure/ground where it helps
(lava is dark crust over a glowing base, so the *gaps* read as molten).

## The loop that actually works (this is the skill)

1. **Author** params/pixels — coordinate-based (string grids are error-prone; that's how a mis-drawn
   mouth-blob got in).
2. **Render to PNG and LOOK.** Use the MCP tools — this is the step that finds real defects:
   - `preview_sprite(archetype, config)` — one sprite, magnified; `frame=N` for an animation frame,
     `silhouette=true` for the mask alone. It renders against the **manifest's own** `style_contract`
     and reports the gate verdict beside the picture. It **refuses** a descriptor whose build does not
     exist, rather than showing you the default under your label.
   - `compare_builds(archetype)` — every variant side by side, as masks. Run this whenever you add or
     change a build.
   - Offline: `docs/reference/library.png` (`python tools/contact_sheet.py`) for the whole library.
   Look at **1× (native)** as well as magnified — a sprite that only reads at 6× does not read in game.
3. **Judge by eye.** The asset gate checks *conformance* (palette/alpha/canvas), **not quality**.
   "Passes the gate" ≠ "looks good." Nothing automated will tell you a sprite reads as what it is named.
4. **Iterate 1px at a time.** Re-render, re-look. Stop when it reads at 1×.

## If you reach for a metric, validate the metric first

Quality checks here are easy to get confidently wrong. Before asserting on any statistic, **measure it
against both the old and the new render** and confirm it separates them in the direction you expect.
Three that were built and thrown away for failing that:

- *Tile seam energy* (seam difference vs interior mean) — flags `brick` and `water`, whose own mortar
  and ripple periods make a **correct** seam look like a discontinuity. It reports "cannot tell" as
  "broken".
- *Autocorrelation structure score* — new `grass` scored 0.169 against a 0.145 pure-noise control, and
  new `dirt` scored *below* its own control. It cannot tell structure from noise at 16×16.
- *Silhouette XOR, applied to the specter* — the hood rewrite moved ghost/specter from 96px apart to
  74px while making them far easier to tell apart, because what changed is *where* the shape narrows.
  An XOR threshold would have failed a real improvement; an apex ratio (0.378 → 0.175) caught it.

A test that passes for the wrong reason, or fails a good change, is worse than no test. Prefer an exact
invariant you can state (primitives wrap; periods divide the tile) over a plausible-looking score.

## Ground in references — don't invent

- Read the research notes before drawing that thing: `docs/research/01-walk-cycle.md`,
  `02-character-sprites.md`, `03-quadruped.md` (the two-biped depth trick + the ≥3px leg-gap rule),
  and the Vanguard `sprite_style_guide.md` principles (hue-shift, 3 shades, top-left light, sel-out).
- `docs/reference/vanguard-comparison.md` — how the standard maps onto a real GBA-style RPG, and the
  known Meristem gaps it surfaced (the raptor/beetle gap it named has since been filled).
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
