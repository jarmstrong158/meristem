# 00 — The calibration bake-off

**The load-bearing experiment.** The entire project assumes a written style contract can constrain a
free generator hard enough that a set of unrelated assets reads as **one coherent game**. If that is
false, the architecture changes. This experiment tests it before it is built on.

*Rubric pre-registered 2026-07-22, before any asset was generated (DECISIONS dec-0010). Results appended
after the run — the pass/fail bar below is fixed and was not edited to match the outcome.*

---

## Falsifiable thesis

> Given the hand-authored [`style-contract.json`](../../experiments/00-bakeoff/style-contract.json)
> (PICO-8 16-color locked palette, fixed canvas sizes, outline/shading/anchor rules), at least one
> **per-asset-class backend assignment** produces an asset set that a blind judge reads as the work of
> a single artist — **without per-asset manual rescue** beyond the gate's automatic normalization.

## Asset set (11 assets)

4 terrain tiles (grass, dirt, water, stone) · 1 player (idle, front) · 1 enemy (slime, idle) ·
3 item icons (sword, potion, key) · 2 UI (heart, coin).

> **Note on the count:** the bootstrap prompt calls this "the 12-asset set" but enumerates 11. We run the
> 11 explicitly named assets; the enumerated list is authoritative over the round number.

## Backends

1. **Procedural** — pure Python, no model. Shape grammar + palette ramps + compositing. Deterministic,
   free forever. Expected strong on tiles/icons/UI, weak on characters.
2. **Agent-drawn** — Claude draws against a minimal Pillow canvas (palette-constrained primitives) with a
   visual feedback loop: coarse silhouette → export at 8× → look → refine. Minimum surface to run the
   experiment, not an editor.
3. **Local diffusion — CUT** (DECISIONS dec-0002). No permissively-licensed *pixel-art* model exists;
   base SDXL is commercial-safe but weak at 16px, and the pixel-art LoRAs that would fix that are
   non-commercial. Recorded, not run. GPU is ready if the CC0-LoRA path (dec-0003) is ever pursued.

## Pre-registered rubric

Every metric has a measurement method and a threshold. Subjective metrics are **blind-judged**: the judge
sees assets/sheets with **no backend labels and no expected-answer key**.

| # | Metric | How measured | Threshold |
|---|---|---|---|
| 1 | **Palette adherence** | % of opaque pixels exactly equal to one of the 16 locked hexes, measured pre- and post-normalization; plus unique-color count | Post-norm **100%** exact match, unique colors ⊆ palette. Pre-norm reported as "gate workload." |
| 2 | **Alpha discipline** | count of pixels with `0 < alpha < 255`; for tiles, count of transparent pixels | Post-norm **0** semi-transparent everywhere; tiles **0** transparent (fully opaque) |
| 3 | **Grid / tileability** | canvas size == contract size (exact); for terrain tiles, wrap-around seam discontinuity (opposite-edge pixel mismatch count) | Canvas exact. Tiles: seam score reported; lower = more tileable (informational, not a hard gate for single base tiles) |
| 4 | **Silhouette readability @ 1×** | (a) subject alpha-coverage ratio in band (char/enemy 25–75%, icon/ui 20–70%); (b) **blind 1× ID test** — judge names each native-size asset with no context | ≥ **10/11** correctly identified |
| 5 | **Cross-asset coherence** | blind contact sheet scored 1–5 "one artist?"; **odd-one-out** forced choice; objective sub-checks: single shared palette (gate), uniform outline adherence, consistent light direction | Mean coherence ≥ **4/5** AND no asset picked odd-one-out by a majority |
| 6 | **Cost** | wall-clock + token spend per asset per backend | Reported, not gated |
| 7 | **Determinism** | run twice, hash outputs | Procedural **byte-identical**; agent-drawn variance noted |

## Pre-registered verdict rule

- **Thesis HOLDS** iff there exists a per-class backend assignment whose 11-asset contact sheet meets:
  (1) 100% palette adherence + 0 alpha violations post-norm across all assets, **and**
  (2) mean coherence ≥ 4/5 with no majority odd-one-out, **and**
  (3) ≥ 10/11 blind 1× ID.
- **Thesis FAILS** if no assignment reaches that bar without manual per-asset rescue beyond automatic
  normalization. **The correct response to a failure is a different architecture, not more code.**

## Outputs produced by the run

- `experiments/00-bakeoff/procedural/*.png`, `experiments/00-bakeoff/agent-drawn/*.png` (native size)
- `experiments/00-bakeoff/contact-sheets/*` — per-backend contact sheet + a mock game scene composed
  from the assets (coherence is judged on the **sheet/scene**, not individual assets)
- metrics JSON per backend
- the blind judge's raw responses

---

## Results

*(appended after the run — not yet populated)*

### Per-metric measurements
_TBD_

### Blind judging
_TBD_

### Per-class backend assignment (the verdict)
_TBD_

### Does the thesis hold?
_TBD — measured against the fixed bar above, not adjusted to it._
