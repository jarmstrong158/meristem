# DECISIONS

Architectural decisions for Meristem, newest concerns first within Phase groups.
Every entry records the problem, the choice, the rejected alternatives, and the tradeoff.
These are the expensive ones to relitigate — Phase 0 especially.

---

## Phase 0 — Viability, environment, licensing

### dec-0001 — Spec-driven pipeline: one manifest is the single source of truth
**Problem:** "AI writes game files and hopes" produces drift — assets, levels, and data that don't agree with each other or with intent.
**Decision:** a single schema-validated project manifest is canonical. Every downstream artifact (sprites, tilesets, levels, gear tables, Godot scenes) is a *deterministic projection* of it. Output is a real Godot 4 project on the user's disk that they own and can hand-edit.
**Rejected:** (a) hosted runtime — violates ownership + zero-cost constraints; (b) freeform LLM codegen of mechanics — unbounded, unverifiable. Mechanics are instead *parameters over a fixed archetype library* (see Phase 2 plan).
**Tradeoff:** less "anything goes" flexibility in exchange for coherence, verifiability, and true user ownership.

### dec-0002 — Local-diffusion generator backend CUT for v1 (licensing dead-end)
**Problem:** the spec permits a local-diffusion backend *only if a permissively-licensed pixel-art model exists*. The GPU exists (RTX 5070 Ti, 16 GB, CUDA 12.8 ready) but the model does not.
**Decision:** cut the diffusion backend from v1. The bake-off runs only the two clean backends (procedural, agent-drawn).
**Evidence (verified 2026-07-22, see docs/licenses.md):**
- Base SDXL/SD1.5 are commercial-output-safe (OpenRAIL claims no rights over generated images) but are *base* models — weak at 16px pixel art without a LoRA — and ride non-OSI licenses whose behavioral restrictions travel with redistribution.
- The pixel-art LoRAs that would make them good are exactly where commercial safety breaks: Civitai per-model toggles frequently forbid selling generated images or paid hosting, and terms differ across mirrors.
**Rejected:** (a) ship base SDXL as default — mediocre output + non-OSI license clashes with the project's own MIT/open posture; (b) ship a community pixel LoRA — fails commercial-output test per-model.
**Tradeoff:** we lose "type a prompt, get a sprite." We keep a 100%-clean, deterministic, zero-license-risk asset path. The bake-off will tell us whether we even miss it. Reversible: the plugin boundary (dec-0009) lets diffusion be added later.

### dec-0003 — The CC0-LoRA path (deferred option, the only clean route to a diffusion backend)
**Problem:** if we ever want generative sprites that are *commercially shippable*, dec-0002 says no existing model qualifies.
**Decision:** record — but do not build in v1 — the one route that would: train a pixel-art LoRA on **genuinely open training data we own or that is CC0**. Two sub-options:
  1. Train on public-domain / CC0 pixel-art corpora only.
  2. **Bootstrap on our own output** — the procedural + agent-drawn backends produce assets *we* own outright; a LoRA trained on a large enough set of them would inherit that clean provenance.
**Rejected for v1:** any path depending on scraped or unclearable community art.
**Tradeoff:** meaningful effort (dataset curation + training) for a feature the bake-off may prove unnecessary. Kept as a documented option so it isn't reinvented from scratch, and so the provenance argument (option 2 depends on the clean backends existing first) is captured now. Depends on: dec-0009 (plugin boundary), Phase 1 backends shipping.

### dec-0004 — Sprite editor integration: Pixelorama (MIT) primary; LibreSprite arm's-length only
**Problem:** LibreSprite is GPL-2.0 — the only copyleft dependency in the set. Linking/embedding its code would force our MIT tooling to become GPL.
**Decision:** primary in-toolchain sprite editor is **Pixelorama (MIT)**. LibreSprite stays optional, user-installed, and invoked strictly as a **separate process** (launch app/CLI, exchange files on disk — "mere aggregation", GPL does not propagate). Never link its code; never ship a modified LibreSprite as part of a combined work.
**Rejected:** LibreSprite as primary/integrated — introduces GPL propagation risk for no benefit Pixelorama doesn't already provide.
**Tradeoff:** none material — Pixelorama covers the need and is MIT.

### dec-0005 — Attribution: one aggregated THIRD_PARTY_LICENSES + in-game licenses screen
**Problem:** Godot (MIT notice in shipped games), Pillow (HPND), numpy/scipy (BSD-3) each require notice retention.
**Decision:** the compiler emits a single aggregated `THIRD_PARTY_LICENSES` file into generated projects and wires an in-game licenses screen; this satisfies all bundled-notice requirements at once. Every generated *asset* additionally carries a provenance sidecar (backend, model+version, prompt, seed, style-contract hash, timestamp, human-edited flag) so the user can produce accurate Steam/itch AI disclosures.
**Tradeoff:** none.

### dec-0006 — Locked default palette: PICO-8 (CC0)
**Problem:** the style contract needs a locked 16-color palette with an unambiguous license.
**Decision:** default = **PICO-8 palette**, the only candidate with an explicit written grant (Lexaloffle FAQ: palette + font under CC-0, no attribution). Endesga-32 and Sweetie-16 remain selectable but are flagged "no formal license" (rely on colors-not-copyrightable).
**Rejected:** Endesga-32 / Sweetie-16 as default — no affirmative grant, weaker legal footing for a commercial tool.
**Tradeoff:** PICO-8's 16 colors are a specific aesthetic; users can swap palettes, but the *default* is the safest.

### dec-0007 — Headless rendering on Windows: offscreen viewport capture, not `--headless`, no Xvfb
**Problem:** the spec assumed Xvfb for headless screenshots. Xvfb is Linux-only and absent; Godot's `--headless` uses dummy drivers that don't render, so it cannot screenshot on any OS.
**Decision:** Phase 4's **assertion loop** uses true `--headless` (state/physics, no pixels). The **visual loop** runs Godot with a real offscreen/hidden window and captures via the in-engine viewport API (`get_viewport().get_texture().get_image().save_png()`) driven by a harness script. A ~20-min offscreen-capture probe is the first task of Phase 4.
**Rejected:** `--headless` screenshots (impossible); Xvfb (not applicable on Windows).
**Tradeoff:** slightly more harness machinery than a naive `--headless` screenshot would have been — but that naive path never worked. RTX card makes offscreen rendering trivial.

### dec-0008 — LDtk over Tiled: the model writes semantic integers, LDtk rules paint tiles
**Problem:** letting an LLM write raw tile IDs is a reliable source of broken maps.
**Decision:** the compiler emits LDtk projects with IntGrid layers; the model/spec only ever writes **semantic integers** (0=empty, 1=ground, 2=water…) and LDtk's auto-layer rules paint the actual tileset. This is the specific reason LDtk was chosen over Tiled.
**Tradeoff:** depends on LDtk (MIT, free) and godot-ldtk-importer (MIT) at Phase 3; LDtk must be installed then.

### dec-0009 — Generator plugin boundary from day one: `generate(spec, style_contract) -> Image`
**Problem:** backends will change (procedural, agent-drawn, later maybe diffusion or a paid API).
**Decision:** a single generator interface `generate(spec, style_contract) -> Image`. The Phase 0 backends are the first implementations. A paid-API or future CC0-LoRA backend must be addable later **without touching the asset gate**. The asset gate normalizes/validates output regardless of source.
**Tradeoff:** a small upfront abstraction; explicitly the *only* generator abstraction allowed (the "fourth abstraction layer, stop and ask" rule applies).

### dec-0011 — The style-contract thesis HOLDS; per-class backend assignment = surfaces→procedural, objects→agent-drawn
**Problem:** the whole project rests on whether a written style contract can make independent free generators produce one coherent game (dec-0010's experiment).
**Decision:** thesis confirmed against the pre-registered bar. Ship both throwaway backends into Phase 1 as maintained implementations, assigned by class: **terrain tiles/textures → procedural** (deterministic, instant, ~0-token, texture is its strength); **all discrete objects (character, enemy, item icons, UI) → agent-drawn** (hand-authored, view-refine loop).
**Evidence (docs/research/00-bakeoff.md):** a *blind* judge (no labels, no answer key) rated the mixed procedural-tiles + agent-drawn-sprites set **5/5 "one artist", 0 odd-one-out, 11/11 identified at 1×**, and rated the all-procedural set only 3/5 with three misreads (procedural heart→"gem", sword→"fishing rod", key→"seahorse"). Both backends were 100% palette-adherent, 0 semi-alpha, byte-deterministic.
**Refined hypothesis:** procedural is weak not just at characters but at *all* small discrete objects — 16×16 procedural icons/UI lack intentional silhouette. Clean division: **procedural = surfaces, agent-drawn = objects.**
**Rejected:** all-procedural (fails coherence + readability bar); all-agent-drawn (wasteful — procedural tiles are free/instant and judged equally coherent).
**Tradeoff:** two backends to maintain instead of one — accepted, and exactly what the dec-0009 plugin boundary was built for. The blind 5/5 on a *mixed-backend* set is the load-bearing result: the contract, not a single generator, carries coherence.

### dec-0012 — Base terrain tiles are generated as material, made tileable by the compiler (not a baked bevel)
**Problem:** the uniform bevel that lifts *object* coherence makes base tiles self-contained lit squares that don't seam-match (seam score 30; visible per-tile borders in the mock scene).
**Decision:** the generator emits terrain as flat *material* tiles; **tileability is produced at compile time via TilePipe2 autotiling / LDtk auto-layer rules** (dec-0008 already routes tiles through LDtk). The bevel/outline-as-coherence device is retained for discrete objects only.
**Rejected:** baking bevels/edges into base tiles — breaks seamless tiling and fights the autotiler.
**Tradeoff:** none — this is how autotiling pipelines are meant to work; the bake-off just made the reason concrete.

### dec-0010 — Bake-off rubric tightened and pre-registered before running
**Problem:** a vibe-based rubric lets us rationalize whatever result we get. The bake-off's whole job is to falsify (or not) the style-contract thesis.
**Decision:** the Phase 0c rubric is quantified, blind-judged where subjective, and its pass/fail bar is written down *before* generation (see docs/research/00-bakeoff.md, "Pre-registered rubric"). The thesis has an explicit failure condition; if it fails, the response is a different architecture, not more code.
**Tradeoff:** more setup before the fun part — deliberately, because this is the load-bearing experiment.
