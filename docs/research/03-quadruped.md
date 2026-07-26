# Quadruped archetype — construction spec

Reference notes behind `build_quadruped` (dec-0022). Verified against side-view
pixel beasts in the 32×32 / low-res tradition (Stardew critters, PICO-8 fauna,
LPC animals) — **researched, not recalled**, per the anti-drift rule.

The failure this spec exists to prevent: a **table** — a rectangular body sitting
on four identical vertical posts with one hole punched in the middle. That reads
as furniture, not an animal.

## 1. Silhouette first

A quadruped is legible from its outline alone. Three things must read at 32px:

1. **A thick horizontal body loaf** — wider than tall, but still a chunky mass
   (~8–9px tall at 32px), not a thin rail. Crucially, **legs start *below* the
   body** (they hang from the belly), never overlapping up into it — if the legs
   paint over the lower body the mass reads as ~6px and looks starved. Keep a
   **wide belly** at the bottom so all four legs still attach to it.
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

## 6. Parametric knobs (implemented)

Beyond `config.color`, the build takes `config.build` — a preset that reshapes
the one skeleton. Crucially, a preset reshapes the **torso**, not just what hangs
off it: `back` and `belly` are lists of `(col, row)` knots that `_edge` expands
into the top and bottom edges of the body, and each column is filled between
them. Shipped in `_QUAD_BUILDS`:

| variant | torso | legs | head | tail | reads as |
|---------|-------|------|------|------|----------|
| dog     | level back, medium depth | medium, paw 28 | mid-height, perky ears | curl up over the back | balanced hound |
| wolf    | long, deep chest, tucked waist | longest, paw 30 | carried **low and forward** | long, hangs low | lean predator loping |
| boar    | short, big shoulder hump, very deep | stubby, paw 27 | big, low, tusked | tiny stub | low & heavy |
| cat     | short, shallow, **arched** back | thin (1px), paw 27 | small, high | tall vertical S | slim feline |

Adding a variant is a row in the preset table, not new drawing code.

**This section used to say the opposite, and it was wrong.** The original build
shared one hardcoded body loaf across all four presets and varied only leg length,
ear height, muzzle jut and tail — and this doc claimed that was "enough to read
four distinct beasts at 1×". It was not. Rendered as pure alpha masks the four
silhouettes were nearly the same animal: the closest pair differed by 46px, and
most of that was tail. Appendages decorate a silhouette; they do not create one.
The rule in §1 — *a quadruped is legible from its outline alone* — applies just as
much **between variants** as it does to a single beast against the background.

The regression guard is `test_quadruped_builds_differ_in_silhouette`, which
compares alpha masks rather than pixels (a byte-difference test passes on a 1px
ear and so caught none of this). Worst pair is now 144px.

## 7. The gate does not judge this

Every rule above is about *reading as an animal*. The asset gate checks palette,
alpha, and canvas — it will happily pass a table. Conformance ≠ quality: render
at 1×/2×/3× and **judge the silhouette by eye** before shipping.
