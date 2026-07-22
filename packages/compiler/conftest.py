"""Put sibling packages on sys.path so tests run without editable installs."""
import sys
from pathlib import Path

_pkgs = Path(__file__).parent.parent
for name in ("asset-gate", "generators", "spec-store"):
    p = _pkgs / name
    if p.is_dir():
        sys.path.insert(0, str(p))
