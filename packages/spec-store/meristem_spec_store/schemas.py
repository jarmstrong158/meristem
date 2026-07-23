"""Locate and load the JSON Schemas, one Draft 2020-12 validator per domain."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

# manifest domains -> schema filename stem (files use hyphens)
DOMAINS = [
    "project", "style_contract", "narrative", "entities",
    "items", "mechanics", "economy", "world", "levels",
]


def _schema_filename(domain: str) -> str:
    return f"{domain.replace('_', '-')}.schema.json"


def find_schema_dir(start: Path | None = None) -> Path:
    """Walk up from here (or `start`) to the repo's schemas/ directory."""
    here = (start or Path(__file__)).resolve()
    for parent in [here, *here.parents]:
        cand = parent / "schemas" / "project.schema.json"
        if cand.exists():
            return cand.parent
    raise FileNotFoundError("could not locate the schemas/ directory")


@lru_cache(maxsize=1)
def load_validators() -> dict[str, Draft202012Validator]:
    sdir = find_schema_dir()
    validators: dict[str, Draft202012Validator] = {}
    for domain in DOMAINS:
        path = sdir / _schema_filename(domain)
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validators[domain] = Draft202012Validator(schema)
    return validators


def validator_for(domain: str) -> Draft202012Validator:
    v = load_validators()
    if domain not in v:
        raise KeyError(f"unknown domain {domain!r}; known: {DOMAINS}")
    return v[domain]
