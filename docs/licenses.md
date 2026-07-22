# Dependency license audit

*Audited 2026-07-22. Method: primary-source verification (official GitHub `LICENSE` files, official licensing pages, HuggingFace model cards). Tests applied to each: **(A)** free personal use, **(B)** free commercial use of the user's produced output, **(C)** redistribution of our MIT tooling that wraps/drives the dependency.*

## Summary verdict table

| Dependency | License (verified) | A: free personal | B: commercial output | C: redistribute wrapper | Notes |
|---|---|---|---|---|---|
| Godot Engine 4.x | MIT | ✅ | ✅ | ✅ | No royalty on shipped games. Engine MIT-notice must appear in *your* game (credits/licenses screen). |
| LDtk editor app | MIT | ✅ | ✅ | ✅ | Pay-what-you-want, MIT, free. |
| `.ldtk` format / JSON schema | Open JSON (schema in MIT repo; format not copyrightable) | ✅ | ✅ | ✅ | Reading/writing `.ldtk` is unrestricted. |
| LDtk haxe API/loader | MIT | ✅ | ✅ | ✅ | Same MIT repo. |
| godot-ldtk-importer | MIT | ✅ | ✅ | ✅ | © Andrew Gleeson 2023. |
| TilePipe2 | MIT | ✅ | ✅ | ✅ | © Aleksandr Bazhin 2020. |
| Pixelorama | MIT | ✅ | ✅ | ✅ | © Orama Interactive. |
| LibreSprite | **GPL-2.0** | ✅ | ✅ (art is yours) | ⚠️ **conditional** | Copyleft. Separate-process only; do NOT link its code. See RISKS. |
| Pillow | HPND / MIT-CMU | ✅ | ✅ | ✅ | Retain notice; no author name in advertising. |
| numpy | BSD-3-Clause | ✅ | ✅ | ✅ | Retain notice. |
| scipy | BSD-3-Clause | ✅ | ✅ | ✅ | Retain notice. |
| **PICO-8 palette** | **CC0 / public domain** | ✅ | ✅ | ✅ | Explicit CC0, no attribution. **Adopted default.** |
| Endesga-32 palette | No stated license (bare color list) | ✅ | ⚠️ likely | ✅ | No public-domain grant; creator ENDESGA. |
| Sweetie-16 palette | No stated license (bare color list) | ✅ | ⚠️ likely | ✅ | No stated terms; creator GrafxKid. |
| SD 1.5 / SDXL base | CreativeML OpenRAIL-(M/++M) | ✅ | ⚠️ outputs OK, use-restrictions attach | ⚠️ pass-through | Not OSI-"free". See RISKS. |
| Pixel-art LoRAs (Civitai/HF) | Varies — often non-commercial | ✅ | ❌/⚠️ per-model | ❌ often | Audit each. Many restrict commercial/paid-hosting. See RISKS. |

Legend: ✅ pass · ⚠️ pass with caveat · ❌ fail.

## Per-dependency findings

**Godot 4.x — MIT.** `LICENSE.txt` verified (raw.githubusercontent.com/godotengine/godot). Exported games carry no royalty/fee; only obligation is bundling Godot's MIT notice somewhere accessible in the game. Per official "complying with licenses" docs: free to release Godot projects under any license and to make commercial games.

**LDtk — MIT (all three layers).** `LICENSE` verified (github.com/deepnight/ldtk), MIT © 2020 Sébastien Benard – Deepnight Games. Editor app MIT/free; `.ldtk` is a documented JSON schema (ldtk.io/json) and a format is not copyrightable; haxe loader MIT. Reading/writing `.ldtk` in a commercial third-party tool is unrestricted.

**godot-ldtk-importer — MIT.** `LICENSE` verified (heygleeson/godot-ldtk-importer), MIT © 2023 Andrew Gleeson.

**TilePipe2 — MIT.** `LICENSE` verified (aleksandrbazhin/TilePipe), MIT © 2020. Pull the v2 release; license is repo-wide.

**Pixelorama — MIT.** `LICENSE` verified (Orama-Interactive/Pixelorama). Built on Godot (MIT) — no conflict.

**LibreSprite — GPL-2.0.** `README` + `LICENSE.txt` verified (LibreSprite/LibreSprite). Personal use fine; **your art is yours to sell** (GPL covers the program, not your output). Copyleft is triggered by *linking/incorporating its code*, **not** by invoking it as a separate process. See RISKS #1.

**Pillow — HPND / MIT-CMU.** `LICENSE` verified. Commercial OK; retain notice; no author name in advertising.

**numpy / scipy — BSD-3-Clause.** Both verified. Commercial OK; retain notice; no endorsement use of names.

**Palettes.** PICO-8: Lexaloffle FAQ states "The palette and font are both available under a CC-0 license" — public domain, no attribution. Endesga-32 (ENDESGA) and Sweetie-16 (GrafxKid): Lospec publishes no license text for either. A bare list of hex values is generally **not copyrightable** (below the authorship threshold), so all three are almost certainly embeddable — but only PICO-8 has an affirmative written grant. **Default = PICO-8.**

**Local pixel-art diffusion.** SDXL base card verified (huggingface.co/stabilityai/stable-diffusion-xl-base-1.0): CreativeML Open RAIL++-M. Outputs are commercial-safe — the license "claims no rights in the output you generate." But OpenRAIL is **not** OSI-approved and carries behavioral use-restrictions that travel with redistribution. Community pixel-art LoRAs (e.g. `nerijs/pixel-art-xl`) carry inconsistent terms across HF vs Civitai mirrors, and Civitai per-model toggles frequently forbid selling generated images or paid hosting.

## RISKS / FLAGS

1. **LibreSprite is the only copyleft dep (GPL-2.0).**
   - **SAFE:** invoke as a separate process (launch app/CLI, exchange files on disk) — mere aggregation, wrapper stays MIT. Bundling an *unmodified* binary alongside is OK if GPLv2 is honored for that binary and it stays a separate component.
   - **UNSAFE:** linking/importing its code, or shipping a *modified* LibreSprite as part of a combined work — makes the whole thing GPL.
   - **Decision:** primary editor = **Pixelorama (MIT)**; LibreSprite optional, user-installed, arm's-length only. (DECISIONS dec-0004.)

2. **Local pixel-art diffusion — the only place commercial-output safety genuinely fails for specific artifacts.**
   - Base SDXL/SD1.5 outputs are commercial-safe but ride non-OSI OpenRAIL licenses.
   - Community pixel-art LoRAs are the trap: inconsistent, often non-commercial or no-paid-hosting.
   - **Decision:** diffusion backend **cut for v1** (DECISIONS dec-0002). The only clean future route is a LoRA trained on genuinely open data — see the **CC0-LoRA path** (DECISIONS dec-0003).

3. **Endesga-32 / Sweetie-16 have no written license.** "Colors aren't copyrightable" is strong but is a legal inference, not a grant. **Mitigation:** default to PICO-8 (CC0). If the others are offered, flag the absence of a formal grant and credit ENDESGA / GrafxKid as courtesy.

4. **Attribution notices to bundle (not blockers):** Godot MIT notice in shipped games; Pillow (HPND) + numpy/scipy (BSD-3) notices retained in any redistribution of our tool. A single aggregated `THIRD_PARTY_LICENSES` file + an in-game licenses screen satisfies all. (DECISIONS dec-0005.)

**Bottom line:** everything except LibreSprite and the diffusion layer is cleanly MIT/BSD/HPND/CC0 and passes A/B/C outright. LibreSprite is usable at arm's length or replaced by Pixelorama. The diffusion layer is the only genuine commercial-output failure for specific artifacts, and is cut for v1.
