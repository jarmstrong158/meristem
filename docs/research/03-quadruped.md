# Quadruped archetype — construction spec

Reference notes behind `build_quadruped` (dec-0022). Verified against side-view
pixel beasts in the 32×32 / low-res tradition (Stardew critters, PICO-8 fauna,
LPC animals) — **researched, not recalled**, per the anti-drift rule.

The failure this spec exists to prevent: a **table** — a rectangular body sitting
on four identical vertical posts with one hole punched in the middle. That reads
as furniture, not an animal.

## 1. Silhouette first

A quadruped is legible from its outline alone. Three things must read at 32px:

1. **A horizontal body loaf** — clearly wider than tall, not a square.
2. **Four legs that separate** — three transparent gaps (outer-left, belly,
   outer-right), never one solid mass with a single hole.
3. **A head that juts** — off the front of the body on a short neck, with ears
   and a muzzle wedge breaking the round skull.

## 2. Depth: two biped pairs, not four equal legs

The single most important trick. Draw the animal as **two overlapping bipeds**:

- **Near pair** (the side facing the camera): `base` shade, paws on the ground
  line (row 28).
- **Far pair** (the side away): `shadow` shade **and** paws **1px higher**
  (row 27). Darker + shorter = "further away." This alone kills the table look,
  because the four legs stop being coplanar.

Offset the far pair 2–4px horizontally from its near partner so both are visible.

## 3. Legs: bend them

Identical vertical posts read as furniture. Give the pairs different bends:

- **Front legs** — near-vertical, a straight column from shoulder to paw.
- **Back legs** — **Z-bent** (thigh angles forward, shin drops back, like a
  lightning bolt). This is the haunch, and it's what makes it an *animal*.

Keep legs **thin (2px)** with **transparent gaps** between all four. Cols used:
far-back 6, near-back 11, far-front 16, near-front 21 — evenly spaced.

**Gaps must be ≥3px, not 2px.** The selective outline adds one dark pixel to
each side of a gap, so a 2px gap gets both columns painted and the four legs
**fuse into a floor bar** (the table again, from below). A 3px gap keeps its
middle column transparent after outlining, so the legs stand free to the ground.
For the same reason, don't add a bottom cast-shadow bar or inward-pointing paw
toe-caps — both re-bridge the feet.

## 4. Body form (top-left light)

- **Raised withers / curved back** — the spine is not flat; it rises toward the
  shoulders. A 1px `highlight` run along the top of the back sells the light.
- **Tucked belly** — the underside is `shadow` and tucks *up* toward the rear,
  not a flat plank.
- Muzzle underside and jaw are `shadow`; skull top is `highlight`.

## 5. Head details

- **Muzzle wedge** juts forward past the skull (1–2px), with a single dark
  `nose` pixel at its tip.
- **Eye** is a *single* dark pixel, set high and forward. Two pixels or a
  centered block reads as a bug or a mouth-blob (the character-face mistake).
- **Ears** are two short uprights at the top-back of the skull.

## 6. Parametric knobs (future)

The build is colour-parametric today (`config.color`). The knobs a fuller
library wants, all expressible over this same skeleton:

| variant | back | ears | muzzle | tail | proportion |
|---------|------|------|--------|------|------------|
| dog     | Z-bent | upright | short | curl up | balanced |
| wolf    | Z-bent | tall pointed | long | low straight | leggy |
| boar    | stubby | small | long snout | tiny | low + heavy |
| cat     | deep Z | small | short | long S-curve | slim |

These are proportion + appendage swaps over the fixed archetype — the same
"sprites are parameters over an archetype" principle as the rest of the library.

## 7. The gate does not judge this

Every rule above is about *reading as an animal*. The asset gate checks palette,
alpha, and canvas — it will happily pass a table. Conformance ≠ quality: render
at 1×/2×/3× and **judge the silhouette by eye** before shipping.
