# pytest adds this dir to sys.path, making `meristem_spec_store` importable in tests.
"""Also put the sibling generators package on sys.path.

`meristem-generators` is a declared dependency of the spec store (dec-0036): the
cross-reference layer resolves sprite descriptors and level-legend tiles against the
live generator catalog, and the schema/registry drift test compares the sprite
`archetype` enum to it. Without this, running `pytest packages/spec-store` on its own
took the import-failure path and quietly skipped those checks — the exact failure
mode dec-0036 exists to prevent.
"""
import sys
from pathlib import Path

_generators = Path(__file__).parent.parent / "generators"
if _generators.is_dir():
    sys.path.insert(0, str(_generators))
