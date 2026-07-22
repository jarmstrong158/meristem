"""Provenance sidecar. Every accepted asset carries one so the user can produce
accurate Steam / itch.io AI disclosures. Written next to the asset as
`<asset>.prov.json`."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Provenance:
    backend: str                      # "procedural" | "agent-drawn" | "diffusion" | "imported" | ...
    contract_name: str = ""
    contract_hash: str = ""
    model: Optional[str] = None       # None for non-model backends
    model_version: Optional[str] = None
    prompt: Optional[str] = None
    seed: Optional[int] = None
    human_edited: bool = False
    gate_version: str = ""
    source_sha256: Optional[str] = None   # hash of the pre-gate input image bytes
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        return asdict(self)

    def write_sidecar(self, asset_path: str | Path) -> Path:
        p = Path(asset_path)
        sidecar = p.with_name(p.name + ".prov.json")
        sidecar.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return sidecar

    @staticmethod
    def sha256_of_file(path: str | Path) -> str:
        return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()
