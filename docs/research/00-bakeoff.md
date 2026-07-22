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

*Run 2026-07-22. Two backends over the 11-asset set. Local diffusion not run (cut, dec-0002).*

### Per-metric measurements (objective)

| Metric | Procedural | Agent-drawn | Bar | Result |
|---|---|---|---|---|
| Palette adherence (post-norm) | 100% all 11 | 100% all 11 | 100% | ✅ both (by construction — index-grid backends) |
| Alpha discipline (semi-transparent px) | 0 all 11 | 0 all 11 | 0 | ✅ both |
| Tile transparent px | 0 all tiles | 0 all tiles | 0 | ✅ both |
| Canvas size exact | ✅ 11/11 | ✅ 11/11 | exact | ✅ both |
| Determinism (byte-identical rebuild) | ✅ | ✅ | required | ✅ both |
| Tile seam discontinuity | 30 | 30 (tiles reused) | informational | ⚠️ see finding below |

The two clean backends are **palette-perfect and hard-alpha by construction** — they work in
palette-index space, so the normalizer/gate has *zero* work to do on their output. That is itself the
headline objective finding: license-safe procedural + agent-drawn output needs **no rescue** to pass the
gate. (The normalizer earns its keep only on a non-palette source such as diffusion — which is cut.)

### Blind judging (independent judge, no labels, no answer key)

Judge saw two neutrally-named sets. **Set A = agent-drawn sprites + procedural tiles. Set B = all-procedural.**

| | Set A (agent-drawn sprites) | Set B (all-procedural) |
|---|---|---|
| Coherence "one artist?" (1–5) | **5/5** | 3/5 |
| Odd-one-out | **none** | position 9 (procedural key — "blobby/seahorse") |
| Blind 1× identification | **11/11** read correctly | **8/11** — 3 misses |
| Misreads | — | sword → "fishing rod/wand"; key → "unclear/seahorse"; **heart → "gem/diamond"** |
| Mock scene | "coherent classic platformer screen… clean and legible" | "reads as a game screen" but pickup "nearly invisible/ambiguous", sprites "softer than the tiles" |

Verbatim final: *"Set A is more visually coherent and readable overall… every asset reads instantly (5/5).
Set B has strong tiles and a nice slime/coin, but three assets drag it down… making the set feel partly
mismatched (3/5)."*

### Per-class backend assignment (the verdict) — recorded as DECISIONS dec-0011

| Asset class | Winner | Why |
|---|---|---|
| Terrain tiles / textures | **Procedural** | Both sets' tiles judged coherent; procedural is deterministic, instant, ~0-token, and texture/noise is its strength. Agent-drawn reused them. |
| Character | **Agent-drawn** | Procedural character judged "rough proportions"; agent-drawn reads instantly as a hero. |
| Enemy (slime) | Agent-drawn (procedural acceptable) | Both read as a slime; agent-drawn slightly cleaner. |
| Item icons (sword/potion/key) | **Agent-drawn** | Procedural sword→"fishing rod", key→"seahorse" (2 blind misses). Agent-drawn all read correctly. |
| UI (heart/coin) | **Agent-drawn** | Procedural **heart misread as a gem** — a hard readability failure at this size. Agent-drawn heart reads as a heart. |

**Refinement of the going-in hypothesis.** We expected "procedural good at tiles/icons/UI, bad at
characters." The blind test sharpened it: procedural is excellent at **tiles/textures** but weak at **all
small discrete objects** (icons and UI too, not just characters) — a 16×16 procedural heart/key/sword
doesn't carry enough intentional silhouette to read. The clean division is **procedural = surfaces,
agent-drawn = objects.**

### Does the thesis hold?

**YES — measured against the fixed pre-registered bar, not adjusted to it.**

The bar: *there exists a per-class backend assignment whose 11-asset sheet meets (1) 100% palette + 0 alpha,
(2) mean coherence ≥ 4/5 with no majority odd-one-out, (3) ≥ 10/11 blind 1× ID.*

The **procedural-tiles + agent-drawn-sprites** assignment (Set A) hit **100% palette / 0 alpha / 5-of-5
coherence / none odd-one-out / 11-of-11 identified** — every clause, with margin, and a blind judge
independently called it a single artist's work. Crucially, that set **mixes two backends** and the judge
still saw perfect unity, which is the real load-bearing claim: *a written style contract (locked palette +
uniform outline + shading/anchor rules) constrains independent free generators hard enough that their
combined output reads as one coherent game.* The all-procedural set (3/5, three misreads) shows the bar is
discriminating, not a rubber stamp — it can fail, and one backend did.

**Architectural consequence:** proceed as designed. The generator plugin boundary (dec-0009) is
vindicated — different backends per asset class, unified by the contract + the asset gate, is not just
viable but preferred. Phase 1 builds the real asset gate and promotes these two throwaway backends into
maintained implementations.

### Secondary finding — base tiles must not carry a baked bevel

The uniform top-left bevel that helps *coherence* also makes each base tile a self-contained lit square,
so tiles do not seam-match (seam score 30) and the mock-scene ground shows visible per-tile cell borders.
**Consequence (DECISIONS dec-0012):** terrain in the real pipeline is generated as *material* tiles and
assembled into seamless terrain via **TilePipe2 autotiling / LDtk auto-layer rules** at compile time — the
generator produces the material, the compiler produces the tileability. Bevel-as-coherence-lever stays for
discrete objects (outline + light direction), not for tiling surfaces.

