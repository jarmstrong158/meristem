"""MCP server for the spec store.

Exposes read tools, a single validated write (per-domain, schema-enforced — there is
NO raw write-anything tool), a diff tool, and validate_all. State persists to a
manifest JSON file (env MERISTEM_MANIFEST, default ./meristem.manifest.json).

The tool handlers are plain functions on `SpecService` so they can be unit-tested
without an MCP runtime; `build_server()` wires them into FastMCP.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .schemas import DOMAINS
from .store import SpecStore, SpecValidationError


class SpecService:
    """Transport-agnostic handlers. One instance backs the MCP server."""

    def __init__(self, manifest_path: str | Path):
        self.path = Path(manifest_path)
        self.store = SpecStore.load(self.path) if self.path.exists() else SpecStore()

    def _persist(self) -> None:
        self.store.save(self.path)

    # ---- reads ----
    def list_domains(self) -> dict:
        return {"known": DOMAINS, "present": sorted(self.store.domains)}

    def get_domain(self, domain: str) -> dict:
        if domain not in DOMAINS:
            return {"error": f"unknown domain {domain!r}", "known": DOMAINS}
        return {"domain": domain, "value": self.store.get(domain)}

    def get_manifest(self) -> dict:
        return {"version": self.store.version, "domains": self.store.get_all()}

    # ---- the only mutation: validated, per-domain ----
    def set_domain(self, domain: str, value: dict, actor: str = "agent", reason: str = "") -> dict:
        try:
            self.store.set_domain(domain, value, {"actor": actor, "reason": reason})
        except SpecValidationError as e:
            return {"accepted": False, "domain": e.domain, "errors": e.errors}
        except KeyError as e:
            return {"accepted": False, "errors": [str(e)]}
        self._persist()
        return {"accepted": True, "domain": domain, "version": self.store.version}

    # ---- diff + whole-manifest validation ----
    def diff_domain(self, domain: str, candidate: dict) -> dict:
        return self.store.diff_domain(domain, candidate)

    def validate_all(self) -> dict:
        return self.store.validate_all().to_dict()


def default_manifest_path() -> Path:
    return Path(os.environ.get("MERISTEM_MANIFEST", "meristem.manifest.json"))


def build_server(service: Optional[SpecService] = None):
    from mcp.server.fastmcp import FastMCP  # imported lazily so the lib works without mcp

    svc = service or SpecService(default_manifest_path())
    mcp = FastMCP("meristem-spec-store")

    @mcp.tool(description="List known and currently-present manifest domains.")
    def list_domains() -> dict:
        return svc.list_domains()

    @mcp.tool(description="Read one manifest domain's current value.")
    def get_domain(domain: str) -> dict:
        return svc.get_domain(domain)

    @mcp.tool(description="Read the whole manifest (all domains + version).")
    def get_manifest() -> dict:
        return svc.get_manifest()

    @mcp.tool(description="Set a whole domain. Rejected (not coerced) if it fails that domain's schema. "
                          "This is the only write; there is no raw write-anything tool.")
    def set_domain(domain: str, value: dict, actor: str = "agent", reason: str = "") -> dict:
        return svc.set_domain(domain, value, actor, reason)

    @mcp.tool(description="Diff a candidate value for a domain against the stored value.")
    def diff_domain(domain: str, candidate: dict) -> dict:
        return svc.diff_domain(domain, candidate)

    @mcp.tool(description="Validate the whole manifest: per-domain schemas + cross-references.")
    def validate_all() -> dict:
        return svc.validate_all()

    return mcp


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
