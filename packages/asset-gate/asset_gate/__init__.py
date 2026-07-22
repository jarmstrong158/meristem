"""Meristem asset gate.

Takes any image + a style contract and returns a normalized, game-ready asset —
or rejects it with a specific reason. Reject-and-report is a first-class outcome:
a gate that always says yes is not a gate.
"""
from .contract import StyleContract, load_contract
from .gate import GateResult, normalize, validate
from .provenance import Provenance

__version__ = "0.1.0"

__all__ = [
    "StyleContract",
    "load_contract",
    "GateResult",
    "normalize",
    "validate",
    "Provenance",
    "__version__",
]
