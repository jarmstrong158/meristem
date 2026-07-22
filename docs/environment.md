# Environment audit

*Machine: home PC (Windows 11 Home, 10.0.26200). Audited 2026-07-22. Nothing was installed during the audit — probe-only.*

## Present and verified

| Tool | Version | Path / note |
|---|---|---|
| Python | 3.12.10 | `C:\Users\jarms\AppData\Local\Programs\Python\Python312\python.exe` |
| pip | 25.0.1 | |
| Pillow | 12.1.1 | asset-gate core dependency |
| numpy | 2.4.2 | |
| PyTorch | 2.10.0+cu128 | CUDA build |
| torchvision | 0.25.0+cu128 | |
| Node | 24.14.0 | for MCP servers (Phase 2/5) |
| npm | 11.12.1 | |
| GPU | NVIDIA RTX 5070 Ti, 16 GB (15.92 GiB) | CUDA 12.8, compute capability 12.0 (Blackwell), driver 591.86 |
| `torch.cuda.is_available()` | `True` | device_count 1 |
| Godot | 4.6.stable.official.89cea1439 | `C:\Users\jarms\repos\Godot_v4.6-stable_win64.exe` — `--headless --version` works |
| ffmpeg | present | `…\ffmpegio\ffmpeg-downloader\…\ffmpeg.exe` |
| **Pixelorama** | 1.1.10 (Godot 4.6.2) | `C:\Users\jarms\repos\Pixelorama\Pixelorama-Windows-64bit\Pixelorama.exe` — free/MIT pixel editor for the hand-edit path (dec-0004) |
| ollama, llama.cpp | repos present | local **LLM** inference (not image diffusion) |

## Missing — and the free way to get each

| Missing | Needed for | Free fix | Priority |
|---|---|---|---|
| **LDtk** | Phase 3 compiler (semantic-integer → rule-based tile painting) | ldtk.io / GitHub `deepnight/ldtk` releases (MIT, pay-what-you-want) | **Required before Phase 3** |
| diffusers, transformers, accelerate, safetensors | *only* a local-diffusion backend | `pip install` | **Not needed** — diffusion backend cut (see DECISIONS dec-0002) |
| scipy | optional k-means in asset-gate | `pip install scipy` (numpy-only k-means also viable) | Minor / optional |
| ImageMagick | nothing required | Pillow covers all raster ops | Skip |

## Flags

### Headless screenshots on Windows (Phase 4 visual loop) — architectural, verified not recalled
The bootstrap prompt assumed **Xvfb**. Xvfb is a **Linux** virtual framebuffer; it is not present and **not applicable on Windows**. More importantly, Godot's `--headless` mode uses **dummy display + rendering drivers that do not actually render** — you cannot capture a screenshot from `--headless` on any OS.

- **Assertion loop (Phase 4a)** — state injection / physics checks, no pixels → works under true `--headless`. ✅
- **Visual loop (Phase 4b)** — needs a real GPU rendering context. The free Windows path: run Godot with a real (offscreen/hidden) window and capture via the in-engine viewport API
  (`get_viewport().get_texture().get_image().save_png()`), driven by a harness script — **not** `--headless`.

**Action:** a ~20-minute probe (render one frame offscreen → save PNG on *this* box) is scheduled as the first task of Phase 4, before the verifier is designed around it. The RTX card makes offscreen rendering trivial; this changes harness design, not viability. See DECISIONS dec-0007.

## Verdict
Viable, no blockers. Only **LDtk** is a hard must-install (free) and only at Phase 3. The GPU/CUDA stack is fully ready but unused, because the diffusion backend was cut on licensing grounds (dec-0002), not capability grounds.
