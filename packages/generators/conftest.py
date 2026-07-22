"""Put the sibling asset-gate package on sys.path so the integration tests can
gate generated output. pytest already adds this dir (for meristem_generators)."""
import sys
from pathlib import Path

_asset_gate = Path(__file__).parent.parent / "asset-gate"
if _asset_gate.is_dir():
    sys.path.insert(0, str(_asset_gate))
