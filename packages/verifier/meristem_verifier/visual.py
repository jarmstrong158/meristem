"""Visual loop: capture a real rendered frame of the running game (windowed — the
real GL renderer, since --headless cannot render, dec-0007). The captured PNG is
then critiqued against the spec by a vision model (see cli / docs)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from .runner import _install_harness


def capture_frame(project_dir: str | Path, godot_bin: str, timeout: int = 120) -> Optional[Path]:
    proj = Path(project_dir)
    vdir = _install_harness(proj, "capture.gd", "capture.tscn")
    cap = vdir / "capture.png"
    if cap.exists():
        cap.unlink()
    # import headless first (fast), then run WINDOWED to actually render
    subprocess.run([godot_bin, "--headless", "--path", str(proj), "--import"],
                   capture_output=True, text=True, timeout=timeout)
    subprocess.run([godot_bin, "--path", str(proj), "res://verifier/capture.tscn",
                    "--quit-after", "180"], capture_output=True, text=True, timeout=timeout)
    return cap if cap.exists() else None
