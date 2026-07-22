"""Meristem verifier: two free loops that gate on more than a clean compile.

- assertion loop: drive the compiled project headlessly, check spec-derived
  assertions (move speed, etc.) — state/physics, no pixels.
- visual loop: capture a real rendered frame (windowed) and critique it against
  the spec with a vision model.
"""
from .assertions import derive_assertions
from .runner import run_assertions
from .visual import capture_frame

__all__ = ["derive_assertions", "run_assertions", "capture_frame"]
