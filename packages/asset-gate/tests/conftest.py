import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from asset_gate import load_contract
from asset_gate.contract import StyleContract

FIX = Path(__file__).parent / "fixtures" / "contract.json"


@pytest.fixture
def contract():
    return load_contract(FIX)


@pytest.fixture
def locked_contract():
    """Fixture contract with NO free-palette classes — every class is checked against
    the locked palette (for testing the locked-palette path)."""
    d = json.loads(FIX.read_text(encoding="utf-8"))
    d.setdefault("palette", {})["free_classes"] = []
    return StyleContract.from_dict(d)


@pytest.fixture
def make_rgba():
    def _make(w, h, fill=(0, 0, 0, 0)):
        arr = np.zeros((h, w, 4), dtype=np.uint8)
        arr[:] = fill
        return arr
    return _make


@pytest.fixture
def to_img():
    return lambda arr: Image.fromarray(arr.astype(np.uint8), "RGBA")
