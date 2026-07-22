"""Meristem spec store: a versioned, schema-enforced project manifest.

The single source of truth every downstream artifact projects from. Writes that fail
validation are rejected, not coerced; cross-references are enforced across domains.
"""
from .schemas import DOMAINS
from .store import SpecStore, SpecValidationError, ValidationReport, validate_domain
from .crossref import cross_reference_errors
from .diff import diff
from .scaffold import strawman, scaffold_store

__all__ = [
    "SpecStore", "SpecValidationError", "ValidationReport",
    "validate_domain", "cross_reference_errors", "diff", "DOMAINS",
    "strawman", "scaffold_store",
]
