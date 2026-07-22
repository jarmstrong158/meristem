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

### dec-0013 — Spec store: two-layer validation, one validated write, no raw write-anything
**Problem:** a manifest that is the single source of truth must never hold an invalid or internally-inconsistent state, but JSON Schema alone can't express cross-domain references.
**Decision:** validation is two layers. (1) **Schema at the write boundary** — `set_domain(domain, value)` is the *only* mutation, and it validates the whole domain against that domain's Draft-2020-12 schema and **rejects** (never coerces) on failure. (2) **Cross-references at `validate_all`** — drop tables → enemies/items, entity `behavior_archetype` → mechanics, world connections → regions, narrative faction → factions. There is no raw write-anything tool; every accepted mutation is versioned and recorded in history with provenance.
**Also:** mechanics are **parameters over a fixed archetype library** (`platformer_controller`/`top_down_controller`/`turn_based_combat`), typed per-kind via JSON-Schema `if/then` — never freeform code (follows dec-0001).
**Rejected:** (a) a single mega-schema with `$ref`s across domains — ref-resolution complexity, and it still can't do existence checks like "this id exists in another array"; (b) coercing/auto-fixing invalid writes — hides authoring errors, violates "reject, don't coerce"; (c) field-level patch tools — a partial write can't be validated as a coherent domain.
**Tradeoff:** callers must submit a whole valid domain, not a one-field poke. Accepted deliberately: it keeps every stored state a fully-validated one.

### dec-0025 — Archetype animation: frame functions on the registry, palette-safe transforms, generic actor pipeline
**Problem:** only the humanoid animated (a bespoke walk cycle wired straight into the character path). Enemies and pickups were static, and there was no general way for an archetype to declare motion or for the compiler to turn frames into a Godot animation.
**Decision:** animation is a property of the **archetype**, not a special case. `Archetype.frames` (already on the registry) now carries a frame function for the animated ones — `blob` squash-and-stretch, `ghost` float-bob, `quadruped` breathing head-bob, `pickup` coin-spin (a frame fn may return `None` to opt a config out, e.g. a heart doesn't spin). Frames are built two ways: a **param knob** on the builder when motion is non-rigid (`blob` `squash`, `quadruped` `head_dy`), or a **palette-safe transform** of the static sprite when it's rigid (`sprite.translate` for the ghost bob, `sprite.squeeze_h` NEAREST-scale for the coin spin — both colour- and alpha-exact so the gate still passes). **Frame 0 always equals the static build**, so the idle PNG and the animation's first frame are the same pixels. The compiler emits frames generically (`emit_frames`, `skip0` references the already-written idle rather than duplicating it) for characters (`walk`), enemies (`anim`), and the HUD coin (`spin`); `scenes.py` builds a `SpriteFrames` + `AnimatedSprite2D` (autoplay) when an actor has >1 frame, else a static `Sprite2D`.
**Evidence:** all 16 anim frames gate; the compiled slice's blob idles, coin spins, player walks; imports + runs in Godot 4.6 with no SCRIPT ERROR (env-gated smoke test passes); 116 tests green.
**Rejected:** per-entity bespoke animation code (doesn't scale — the whole point of the archetype library); baking motion into new colours/alpha (would fail the gate); GIF/spritesheet atlases (Godot `SpriteFrames` is the native, hand-editable form and keeps one-PNG-per-frame provenance).
**Refines:** dec-0022/0023 (archetype library + spec-addressability) — animation rides the same registry, so a manifest that picks an archetype gets its motion for free.
**Tradeoff:** rigid transforms (bob/spin) can't express squash — that's why non-rigid motion stays a builder knob; two mechanisms, chosen by whether the motion deforms the silhouette.

### dec-0024 — Quadruped construction: two overlapping bipeds, not four coplanar posts
**Problem:** a naive side-view quadruped renders as a **table** — a body loaf on four identical vertical legs with one hole between them reads as furniture, not an animal. The first `build_quadruped` did exactly this (filled leg mass + single gap + a cast-shadow bar fusing the paws into a floor line).
**Decision:** codify the depth trick (docs/research/03-quadruped.md, verified against 32px side-view pixel fauna — researched, not recalled): draw the beast as **two overlapping bipeds**. The **far pair** is `shadow`-shaded, offset 2–4px, and paws sit **1px higher** (row 27 vs 28) so it recedes; the **near pair** is `base` on the ground line. Legs are **thin (2px) with three transparent gaps** (outer-left, belly, outer-right); **front legs vertical, back legs Z-bent** (the haunch). Body is a horizontal loaf with a `highlight` withers line and a `shadow` tucked belly; head juts on a short neck with a muzzle wedge, a **single-pixel eye** (a block reads as the mouth-blob bug), and two upright ears. No bottom cast-shadow bar — it re-fuses the paws.
**Evidence:** rebuilt build_quadruped renders as an unmistakable side-view beast at 1×/2×/3× (four legs separate with two open belly gaps, near pair forward/lit, far pair dark/high); gate-passes at 4 colours; all 47 generator+compiler tests green.
**Refines:** dec-0022 (archetype library) and dec-0021 (sprite standard — this is that standard applied to the hardest silhouette). **Reinforces:** the gate checks conformance, not quality — it passes a table; only eye-judgment at 1×/2×/3× catches it.
**Tradeoff:** the build is colour-parametric today; proportion/appendage knobs (wolf/boar/cat/dog, research §6) are future work over the same skeleton.

### dec-0023 — Sprites are spec-addressable: entities/items declare `sprite: {archetype, config}`
**Problem:** the archetype library (dec-0022) existed as parametric recipes but a *manifest couldn't reach it* — the generator dispatched by hardcoded `(class, name)`, so a spec entity named `ghost` or an item `greatsword` wouldn't resolve. The bestiary/armory was built but not data-driven.
**Decision:** the connector is a **sprite descriptor** on the spec. Entities and items declare `sprite: {archetype, config}` (schema-validated, `archetype` an enum: humanoid/blob/ghost/weapon/consumable/pickup/tile; `config` a free object). The generator exposes an **archetype registry** (`build_archetype`, `archetype_class`, `archetype_frames`, `known_archetypes`) mapping archetype → builder + canvas class + optional animation frames. The compiler dispatches **by archetype**, gates against the archetype's class, and names files by class-prefix + entity/item **id** (stable across archetypes). A ghost enemy, a greatsword, a blue mana bottle: each is now a spec change, not code.
**Evidence:** all 7 archetypes dispatch through the registry (correct class/size, gate-pass, humanoid animates); the slice migrated to descriptors and still compiles/runs; a test flips the enemy to `ghost` in the spec and the compiler builds it (provenance backend = "ghost"). Provenance `backend` now records the **archetype** an asset was built from.
**Rejected:** hardcoded name dispatch (doesn't scale to a bestiary); a plain sprite-name string (can't carry per-instance config like colour/kind/size).
**Connects:** dec-0022 (archetype library) ↔ dec-0013 (schema-enforced manifest) ↔ Phase-3 compiler. **Follow-ups:** the game-interview/skills authoring sprite descriptors; per-instance materials wired from entity data; more archetypes registered as they're built.

### dec-0022 — Sprites are "parameters over a fixed archetype library"; humanoids use the LPC layered pattern
**Problem:** hand-coding a builder per sprite name doesn't scale, and I was re-deriving construction ad-hoc each time ("there are easier/better ways to make a slime"). A survey of the ecosystem (verified) found **no MCP or dataset** that encodes "how to build a fantasy sprite" in a free + commercial-safe + deterministic way — only editor-driver MCPs (Aseprite/Pixelorama, execute-only), diffusion MCPs (non-deterministic, licence-fraught, already cut dec-0002), and one paid/cloud generator (PixelLab). The knowledge layer is ours to author.
**Decision:** the generator's knowledge lives in a **hand-authored parametric archetype/recipe library** — the *same* "parameters over a fixed archetype library" principle we chose for mechanics (dec-0001), now for sprites. Each archetype (humanoid, blob, quadruped, weapon, consumable, container, tile) encodes the *good* way to build that class once, parametrised by materials + features; a specific creature is params on an archetype, not new code. **Humanoids adopt the LPC modular-layered pattern** (`humanoid.py`, first archetype): one shared **skeleton** (`Pose` per animation frame) + **z-ordered layers** (base body → pants → shirt → hair → face → future gear) that all register to it, so **animation is inherited by every layer** and a **per-character palette is just a different `config`** (proven: a recolour = same code, different config). Replaces the monolithic `build_hero` + grid-surgery walk with `build_humanoid` / `humanoid_walk`.
**Evidence / grounding (verified sources):** the LPC **Universal LPC Spritesheet Generator** JSON layer/z-index/animation schema is the best worked example of this pattern — **study it, don't ship its pixels** (art is CC-BY-SA 3.0 / GPL-3.0: copyleft + mandatory attribution). Ground shippable output on **CC0 only (Kenney.nl)**; Spriters Resource / RPG-Maker RTP / Oryx = study-only or paid. Image-gen MCPs (local MIT FLUX/SD, e.g. DiffuGen) are an optional **offline moodboard**, never the deterministic output path.
**Rejected:** shipping LPC/Spriters pixels (licence); a paid/cloud/non-deterministic sprite-gen MCP (PixelLab); diffusion for output (dec-0002); continuing per-name hand-coded builders.
**Follow-ups:** turn the remaining per-name builders (slime, sword, potion…) into parametric archetypes (`blob`, `weapon`, `consumable`, `container`); LPC-style gear/weapon/hat layers + more body/hair options; 4-direction; blink/idle secondary motion; a manifest `sprite` schema (archetype + config) so entities pick an archetype + palette.

### dec-0021 — One sprite-construction standard for ALL assets (the project's core: standardizing how sprites are made)
**Problem:** dec-0020 fixed the *character* with hue-shifted ramps, but the point of Meristem is to **standardize** sprite creation — so every asset type should be built the same way, not one-off per sprite.
**Decision:** a single construction standard, applied to **every** generated sprite (tiles, character, enemy, item icons, UI):
  1. build from **named materials**; each auto-derives a **3-shade hue-shifted ramp** (shadow cool / base / highlight warm) via `shading.Ramp`;
  2. **one light direction** (top-left) — objects shade directionally; *tiles* use the ramp for **texture** (speckle/ripple), not a directional bevel, so they stay tileable (dec-0012);
  3. **selective outline** (a material's dark shade, not pure black);
  4. a **colour budget** (≤15, SNES/GBA convention).
Implemented via a shared `sprite.Canvas` toolkit; `procedural` builds algorithmic tiles, `agent-drawn` builds coordinate objects, **both** through the same standard. The old index-grid/PICO-8 string-block sprites are removed. The asset gate treats **all sprite classes as free-palette** (colour budget) by default; the locked-palette check is retired for generated sprites (kept as an opt-in via `free_classes`).
**Coherence** now comes entirely from the **shared construction rules** (materials → ramps → one light → outline → resolution), not a shared palette — the whole 11-asset set renders as one cohesive game (verified: contact sheet + mock scene + in-game).
**Supersedes:** dec-0006 for all generated sprites (PICO-8 locked palette). The Phase-0 coherence *thesis* still holds — it's just now carried by the construction standard rather than a fixed palette.
**Follow-ups (the "then push quality on all" step):** idle animations for every sprite (character blink, slime bob, coin spin), more material shades/volume, per-character palettes (`build_hero(materials=...)` already supports it).

### dec-0020 — Characters use per-material hue-shifted palettes (Vanguard way); gate gains a free-palette mode. Supersedes dec-0006 for characters.
**Problem:** a reviewer flagged the hair as still wrong. Root cause found by reading the user's *own* Vanguard sprite generator + style guide: good character shading needs **3 hue-shifted shades per material** (shadow shifts cool, highlight shifts warm), derived with `_shadow`/`_hilight` on free-form colors. **PICO-8's locked 16 colors have no brown or skin ramp**, so the substitutes read as wrong colors (orange "highlight" = orange hat; dark_purple "shadow" = magenta). No amount of pixel-nudging fixes a missing ramp.
**Decision (user chose "Vanguard way"):** characters are generated in **free-form RGB with per-material ramps** — `shading.py` (`shadow`/`highlight`/`Ramp`, ported from the Vanguard style guide) derives each material's shadow (cool) + highlight (warm) from one base color. `build_hero` now emits RGBA with directional light (top-left) and shared shades to stay within a **15-colour budget** (SNES/GBA convention). The **asset gate gains a per-class palette mode**: `free_palette` classes (default `character`, `enemy`) are validated against the colour budget + hard-alpha + canvas — **not** subset-of-locked-palette; tiles/icons/UI stay on the locked PICO-8 palette. Coherence for characters comes from **shared light + shading rules + resolution + outline** — how real JRPGs cohere (FF6/Golden Sun don't share one palette).
**Evidence:** the user's `party_overworld_sprite_generator.gd` (hue-shifted `hair_dk`/`hair_lt`, tapered hair + hairline cast shadow) and `sprite_style_guide.md` (15 colours, 3 hue-shifted shades/material, top-left light, sel-out). With real ramps the hero's hair is three actual browns (81,65,31 / 112,68,40 / 153,94,53) and reads as hair; verified at 1×/2× and in-game.
**Supersedes:** dec-0006 (PICO-8 locked palette) *for free-palette classes*. PICO-8 remains the default for flat locked-palette assets; the Phase-0 coherence thesis still holds there.
**Tradeoff / follow-ups:** two palette models now coexist. `build_hero` takes a `materials` dict → per-character palettes are a step away. The enemy/NPC/icon sprites are still index-grid PICO-8 and haven't had the hue-shifted treatment; deciding whether *all* sprites move to free ramps is open.

### dec-0019 — Character sprite rebuilt to a researched low-res spec (coordinate-based, not string grids)
**Problem:** a reviewer flagged the hero's face as broken — a 2×2 black blob dead-center that read as a giant mouth between the eyes. The sprite had no facial construction; "passes the gate" (palette-valid) said nothing about whether it looked like a face. This is the core challenge of the whole project.
**Decision:** replace the hand-authored character string-grid with `build_hero(contract)`, which places pixels by **explicit coordinate** from a researched spec (`docs/research/02-character-sprites.md`): big head (~1/3), eyes as **1×2 dark dots at cols 13 & 18 with 4px of skin between them** (no center blob, no nose), a 1px mouth *2 rows below* the eyes, shaped hair with a shade, selective outline, one light direction. Verified by rendering at 1×/2× and on a pixel grid and iterating — judged by eye, not just the gate.
**Evidence:** grounded in Slynyrd, Saint11/MiniBoss, Maglione's eye-spacing rules, and real sprite sheets (FF6 16×24, Chrono Trigger, Stardew 16×32, Pokémon) — all of which build the face around 2 well-spaced eye marks and omit/minimize the mouth and nose at this size.
**Rejected:** string-grid authoring (too error-prone for precise pixel placement — it's how the blob got in); over-detailing the tiny face.
**Broader point (why it matters):** the asset gate enforces *conformance* (palette, alpha, canvas), not *quality*. Coherent, readable sprites are a human-judged, reference-grounded craft — the gate can't replace looking at the pixels. The `build_hero` fix flows into the walk cycle automatically (dec-0018 derives frames from this idle grid).
**Follow-ups:** blink frame, per-character palettes/silhouettes, and the same rigor for the enemy/NPC sprites.

### dec-0018 — Character animation via a `generate_frames` boundary; walk = principled 4-frame cycle
**Problem:** the definition of done needs "one character with idle **and walk**." A first attempt just shifted the lower third of the sprite sideways — which reads as a lean/shear, not a walk (rejected in review).
**Decision:** add `Generator.generate_frames(spec, contract) -> list[Image]` (default: one frame) as the animation boundary. The agent-drawn character walk is a **4-frame front-facing RPG cycle** — step-left → stand → step-right → stand — built from animation principles after research (`docs/research/01-walk-cycle.md`): the idle is the tall neutral, **step frames are 1px shorter** (torso dips onto the planted foot) with the *opposite* foot lifted, feet otherwise planted. Vertical bob + alternating foot-plant, never a lateral slide. The compiler emits a Godot `SpriteFrames` (`idle`/`walk`) + an `AnimatedSprite2D`, and the controller plays `walk` when moving, `idle` at rest.
**Evidence:** grounded in Final Boss Blues (front RPG cycle), the RPG Maker 3-frame convention, and Williams' four key poses (sources in the research doc). Frames rendered and eyeballed against a ground line to confirm foot-plant + bob before shipping; each frame passes the asset gate; the animated slice runs headless (exit 0) and the assertion loop still measures move speed 80.0 = spec.
**Rejected:** the naive lateral-shift "walk" (no foot plant, no bob, both legs moving together — a lean).
**Polish added since:** arm swing in opposition (hands shift 1px on step frames, verified not to corrupt face/torso) and **cadence tied to move speed** (`AnimatedSprite2D.speed_scale = velocity / MOVE_SPEED`, clamped) so feet don't skate. **Still deferred:** a passing pose distinct from idle, 8-direction variants.

### dec-0017 — MCP-Apps UI (SEP-1865 Final) with a mandatory structured fallback
**Problem:** Phase 5 wants inline UI panels (spec inspector, etc.). SEP-1865 was a moving target in training data.
**Decision:** implement against the **Final** SEP-1865 extension (verified 2026-01-26): a spec-inspector panel served as a `ui://meristem/spec-inspector.html` **resource** with mimeType **`text/html;profile=mcp-app`**; the `inspect_manifest` tool links it via `_meta.ui.resourceUri` (plus the legacy flat `ui/resourceUri` for host back-comfort). The tool **always returns the same data as `structuredContent`**, so hosts that don't render MCP-Apps still get a useful result — the fallback is a complement, not an afterthought. The panel uses the raw `postMessage` JSON-RPC bridge (no SDK dependency); it receives data via `ui/notifications/tool-result`.
**Evidence:** `mcp 1.27.0`'s `FastMCP.resource(mime_type=..., meta=...)` and `FastMCP.tool(meta=...)` are exactly the primitives SEP-1865 needs — no extra dependency; matches the official `ext-apps` Python examples.
**Rejected:** the community `mcp-ui` PyPI port (defaults to superseded MCP-UI content types, not the `mcp-app` profile); older mimeType strings (`text/html+mcp`, `text/html+skybridge`); embedding UI inline in tool results (spec requires predeclared `ui://` resources).
**Tradeoff:** panels only render in hosts advertising the `io.modelcontextprotocol/ui` extension — hence the always-on structured fallback. More panels (sprite contact-sheet approve/reject, palette editor, world graph) are follow-ups; the pattern is proven with the inspector.

### dec-0016 — Phase 4 verifier: both loops work; dec-0007 offscreen capture CONFIRMED
**Problem:** "it compiled and ran" is not "it is correct." The slice needed machine verification against its spec.
**Decision + result:** two loops, both free, both proven on the slice.
- **Assertion loop** (headless): derive assertions from the manifest, drive the compiled game under true `--headless` (physics runs, no renderer), measure. *`move_speed` measured 80.0 = spec.*
- **Visual loop** (windowed): capture a real rendered frame and critique against spec-derived expectations. **dec-0007 is now CONFIRMED** — Godot's `--headless` can't render, but running windowed and calling `get_viewport().get_texture().get_image().save_png()` produces a valid frame on this Windows box (no Xvfb). The capture of the running slice showed a coherent game.
**Finding (the visual loop earning its keep):** the capture revealed the **slime enemy placed on the water pond** — a placement bug no physics assertion catches. Follow-up: drive entity placement from the spec and keep enemies off impassable tiles (part of the dec-0015 "levels in the manifest" work).
**Tradeoff:** the vision *verdict* is produced by the orchestrating model against the printed expectations checklist; the package produces the capture + checklist, not the judgment. Accepted — keeps the package free and model-agnostic.

### dec-0014 — LDtk emission: resolved Tiles layer + IntGrid semantics, not auto-layer rules
**Problem:** dec-0008 routes tiles through LDtk (the model writes semantic ints, not tile IDs). How should the *compiler* emit the `.ldtk`?
**Decision:** the compiler emits a **resolved Tiles layer** — explicit `gridTiles` it computes deterministically from the semantic grid — paired with an **IntGrid layer** carrying the semantic values. It does **not** emit auto-layer rules.
**Evidence (verified 2026-07-22 against ldtk.io/json v1.5.3 + godot-ldtk-importer 2.0.1 README):** the importer reads *baked* tiles, not the rule engine, so auto-rules must be pre-baked into `autoLayerTiles` anyway; authoring correct `autoRuleGroups`/`pattern` structures is fiddly and version-churny (`tileIds`→`tileRectsIds` in 1.5.0) for zero benefit in a generated pipeline. Emitting `.ldtk` with `jsonVersion "1.5.3"`, `externalLevels:false`, uid-linked tileset/layer/level.
**Honors dec-0008:** the *LLM* still never writes tile IDs — the spec carries semantic ints (preserved in the IntGrid layer); the deterministic compiler resolves them to tiles. The `.ldtk` remains user-editable in the LDtk app.
**Rejected:** auto-layer rules (fiddly, must pre-bake regardless); Tiled (dec-0008).
**Tradeoff:** if a user hand-edits the level in LDtk, re-compiling from the manifest would overwrite it — acceptable until level layouts live in the manifest (a future `levels` domain; today the slice synthesizes the layout in the compiler).

### dec-0015 — Vertical slice runs via a runtime ground builder; godot-ldtk-importer is the documented round-trip
**Problem:** running the generated project *through* LDtk requires vendoring the godot-ldtk-importer addon and relying on its import hooks — heavy and fragile to verify for a first slice.
**Decision:** the slice ships a tiny `world.gd` that builds the ground at runtime from a compiler-emitted `grove_01.grid.json` (Sprite2D per cell), so the project **runs in stock Godot 4.6 with zero addons** — verified: `--headless --import` then `--quit-after 5` both exit 0, no SCRIPT ERROR. The `.ldtk` is still emitted as the canonical, LDtk-editable level. The `godot-ldtk-importer` round-trip (edit `.ldtk` → reimport → `TileMapLayer`) is the documented production path, to be vendored after the slice.
**Rejected:** vendoring the importer for the slice (harder to verify now); a native Godot `TileSet`/`TileMapLayer` (its `.tscn` cell binary format is as fiddly as `.ldtk`).
**Tradeoff:** the level grid has two projections (`.ldtk` gridTiles + runtime `grid.json`), both from the *one* compiler-resolved grid, so they can't desync within a compile. Flagged follow-up: vendor the importer + move level layouts into the manifest so the `.ldtk` becomes the single runtime source.

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
