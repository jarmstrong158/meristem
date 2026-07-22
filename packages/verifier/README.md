# meristem-verifier

Two free verifier loops. A clean compile is not evidence — gate on both.

```bash
meristem-verify examples/slice-01/game \
  --manifest examples/slice-01/manifest.json \
  --godot /path/to/godot --visual
```

## Assertion loop (headless)

Derives testable assertions from the manifest and checks them by driving the compiled game
in Godot under true `--headless` (physics runs without a renderer). If the spec says
`move_speed: 80`, the harness spawns the player, holds `move_right` to terminal velocity, and
asserts the measured speed matches — **verified on the slice: measured 80.0 = spec.**

## Visual loop (offscreen render)

Captures a real rendered frame of the running game and critiques it against spec-derived
expectations with a vision model. Because Godot's `--headless` uses a dummy renderer that cannot
draw (dec-0007), capture runs **windowed** (real GL renderer) via
`get_viewport().get_texture().get_image().save_png()` — confirmed working on Windows, no Xvfb.

The loop catches what assertions can't: missing textures, off-palette pixels, z-order faults,
unreadable silhouettes, and bad placement. On the first slice run it immediately flagged the
**enemy standing on the water pond** — a placement bug no physics assertion would surface.

## What it does not do

The vision critique itself is performed by the orchestrating model against the printed
expectations checklist; this package produces the capture + the checklist, not the verdict.

## Tests

```bash
python -m pytest -q                                   # 3 always-on unit tests
MERISTEM_GODOT=/path/to/godot python -m pytest -q     # + 2 real-engine loops (assertion + capture)
```
