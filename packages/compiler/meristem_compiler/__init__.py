"""Meristem compiler: deterministic spec -> Godot 4 project. No LLM in this path.

The manifest is the single source of truth; this package projects it into a Godot
project on disk (project.godot, input map, scenes/scripts from templates, generated
+ gated assets, and an LDtk level). Idempotent; honors user-owned regions."""
from .godot_project import write_project_godot, input_map_for
from .compile import compile_project, CompileError

__all__ = ["write_project_godot", "input_map_for", "compile_project", "CompileError"]
