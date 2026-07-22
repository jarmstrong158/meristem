# 01 — Front-facing walk cycle (technique)

*Grounded in animation principles, not guessed. Sources at the bottom. This is why the
generator's `generate_frames` builds the poses it does.*

## The mistake this replaced

The first attempt horizontally shifted the lower third of the sprite left/right. That reads as a
**lean/shear**, not a walk, because a walk is **vertical and alternating**, not a lateral slide:

- no **foot plant** — every leg pixel moved, so the character skated ("moonwalk");
- both legs moved **together** instead of in opposition;
- no **vertical bob**, so no sense of weight.

## The principle (four key poses → low-res reduction)

A stride has four keys — **contact, down/recoil, passing, up** (Williams, *Animator's Survival Kit*).
The two things that sell a walk are the **vertical body bob** (lowest on the weight-recoil beat,
highest at passing) and the **planted foot** (a foot on the ground stays locked to its pixels).

A **front-facing** character can't stride through screen-space (legs point at the camera), so the
motion reduces to *lift–plant–push* almost in place: one foot lifts while the other plants, with a 1px
body bob. (Final Boss Blues, front/back RPG cycle.)

## What the generator emits (4-frame RPG cycle: step → stand → step → stand)

Standing/idle is the **tall neutral**. The **step frames are 1px shorter** — the head+torso block drops
1px (the weight-recoil dip) while the feet stay planted, and the *opposite* foot lifts 1px:

| Frame | Body | Feet |
|---|---|---|
| F0 step-left | dipped 1px | screen-left planted, screen-**right** foot lifted |
| F1 stand | tall (= idle) | both planted |
| F2 step-right | dipped 1px | screen-right planted, screen-**left** foot lifted |
| F3 stand | tall (= idle) | both planted |

Played at ~8 fps, the tall↔short alternation is the bob and the alternating single-foot lift is the
step. Implemented deterministically from the idle sprite: `_squash_body` (drop torso, keep feet) +
`_lift_foot` (raise one leg's foot pixels), with the legs split by the central gap (`_leg_columns`).

## Timing

~6–10 fps (100–150 ms/frame), equal durations. In Godot the `SpriteFrames` `walk` animation runs at
`speed = 8.0`. Ideally frame cadence scales with move speed so feet don't skate (a follow-up).

## Not yet done (honest)

Arm swing in opposition (very subtle at 32px — deferred), a distinct passing/high-point pose separate
from idle, and 8-directional variants. The core cycle is correct; these are polish.

## Sources

- Final Boss Blues — Walk Cycles [Part 1](http://finalbossblues.com/walk-cycles-p1/) /
  [Part 2](http://finalbossblues.com/walk-cycles-part-2/) (front-facing RPG cycle; step frames 1px shorter)
- RPG Maker 3-frame convention ([OpenGameArt](https://opengameart.org/content/3-frame-walk-cycles),
  [Galv](https://galvs-scripts.com/2020/08/31/mz-character-frames/))
- Pedro Medeiros / Saint11 pixel-art walk-cycle tutorial
- Richard Williams, *The Animator's Survival Kit* — four key poses
