"""The spec store: a versioned manifest with schema-enforced writes.

Writes that fail validation are REJECTED, not coerced. Every mutation is recorded
in history with provenance. There is no raw write-anything method — you set a whole
domain, and it is validated against that domain's schema before it is accepted."""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import schemas
from .crossref import cross_reference
from .diff import diff

MANIFEST_VERSION = 1

# Domains the manifest cannot be considered complete without: every downstream
# consumer dereferences these unconditionally (the compiler does domains["project"],
# domains["style_contract"], domains["entities"], and resolves the control scheme in
# domains["mechanics"]). validate_all used to iterate only the domains that were
# PRESENT, so an empty manifest validated ok=True and then blew up in the compiler
# with a bare KeyError: 'project'. Missing structure is a validation failure.
REQUIRED_DOMAINS = ("project", "style_contract", "entities", "mechanics")


class SpecValidationError(ValueError):
    def __init__(self, domain: str, errors: list[str]):
        self.domain = domain
        self.errors = errors
        super().__init__(f"{domain}: " + "; ".join(errors))


@dataclass
class ValidationReport:
    schema_errors: dict[str, list[str]] = field(default_factory=dict)
    crossref_errors: list[str] = field(default_factory=list)
    missing_domains: list[str] = field(default_factory=list)
    # Checks that could NOT run (e.g. an optional cross-check whose package is not
    # importable). These are not errors, but they are not passes either: a report is
    # only "fully green" when this is empty. Every surface that prints `ok` must also
    # print this, or a skipped check masquerades as a passed one.
    checks_skipped: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.schema_errors or self.crossref_errors or self.missing_domains)

    @property
    def complete(self) -> bool:
        """ok AND every check actually ran."""
        return self.ok and not self.checks_skipped

    def summary(self) -> str:
        if self.missing_domains:
            return ("manifest is incomplete: missing required domain(s) "
                    f"{', '.join(self.missing_domains)} "
                    f"(required: {', '.join(REQUIRED_DOMAINS)})")
        n = sum(len(v) for v in self.schema_errors.values()) + len(self.crossref_errors)
        head = "valid" if self.ok else f"invalid ({n} error{'s' if n != 1 else ''})"
        if self.checks_skipped:
            head += f" — {len(self.checks_skipped)} check(s) SKIPPED: " + "; ".join(self.checks_skipped)
        return head

    def to_dict(self) -> dict:
        return {"ok": self.ok, "complete": self.complete,
                "schema_errors": self.schema_errors,
                "crossref_errors": self.crossref_errors,
                "missing_domains": self.missing_domains,
                "checks_skipped": self.checks_skipped,
                "summary": self.summary()}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def validate_domain(domain: str, value: dict) -> list[str]:
    """Structural (schema) errors for one domain value; [] if valid."""
    validator = schemas.validator_for(domain)
    out = []
    for e in sorted(validator.iter_errors(value), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        out.append(f"{loc}: {e.message}")
    return out


class SpecStore:
    def __init__(self):
        self.domains: dict[str, dict] = {}
        self.history: list[dict] = []
        self.version: int = 0

    # ---- reads ----
    def get(self, domain: str) -> Optional[dict]:
        return copy.deepcopy(self.domains.get(domain))

    def get_all(self) -> dict:
        return copy.deepcopy(self.domains)

    # ---- validated write (the only mutation) ----
    def set_domain(self, domain: str, value: dict, provenance: Optional[dict] = None) -> None:
        if domain not in schemas.DOMAINS:
            raise KeyError(f"unknown domain {domain!r}; known: {schemas.DOMAINS}")
        errors = validate_domain(domain, value)
        if errors:
            raise SpecValidationError(domain, errors)  # reject, do not coerce
        before = self.domains.get(domain)
        self.domains[domain] = copy.deepcopy(value)
        self.version += 1
        self.history.append({
            "version": self.version,
            "domain": domain,
            "op": "set",
            "at": _now(),
            "provenance": provenance or {},
            "diff": diff(before or {}, value),
        })

    # ---- whole-manifest validation ----
    def validate_all(self) -> ValidationReport:
        report = ValidationReport()
        for domain, value in self.domains.items():
            errs = validate_domain(domain, value)
            if errs:
                report.schema_errors[domain] = errs
        # completeness: absent domains are never "validated" by iterating what's present
        report.missing_domains = [d for d in REQUIRED_DOMAINS
                                  if not self.domains.get(d)]
        report.crossref_errors, report.checks_skipped = cross_reference(self.domains)
        return report

    # ---- diff two arbitrary states ----
    @staticmethod
    def diff(old: dict, new: dict) -> dict:
        return diff(old, new)

    def diff_domain(self, domain: str, candidate: dict) -> dict:
        return diff(self.domains.get(domain, {}), candidate)

    # ---- persistence ----
    def to_dict(self) -> dict:
        return {
            "meristem_manifest_version": MANIFEST_VERSION,
            "version": self.version,
            "domains": self.domains,
            "history": self.history,
        }

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return p

    @classmethod
    def load(cls, path: str | Path) -> "SpecStore":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        store = cls()
        store.domains = data.get("domains", {})
        store.history = data.get("history", [])
        store.version = data.get("version", 0)
        return store
