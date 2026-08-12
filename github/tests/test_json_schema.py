#!/usr/bin/env python3
"""
tests/test_json_schema.py
earth-systems-physics
CC0 — No Rights Reserved

Tests for JSON schema validation of Claim payloads.
"""

import json
import pytest
from claim_playground.json_schema import (
    validate_claim_json,
    validate_claim_json_string,
    ValidationError,
)

VALID_CLAIM_JSON = {
    "name": "Test Claim",
    "domain": "test",
    "description": "A test claim for schema validation",
    "tags": ["test", "validation"],
    "couplings": [],
    "related_assumptions": [],
    "version": {
        "version_number": 0,
        "statement": "Test statement for schema validation",
        "mathematical_form": None,
        "domain": "test",
        "scope_valid": ["meso"],
        "ontology_assumed": "process",
        "geometry_assumed": "network",
        "green_range": {"efficiency": 0.9},
        "yellow_range": {"efficiency": 0.6},
        "red_threshold": {"efficiency": 0.3},
    },
}


def test_validate_claim_json_valid():
    """A fully populated valid claim should pass without raising."""
    validate_claim_json(VALID_CLAIM_JSON)


def test_validate_claim_json_missing_required_version():
    """Missing the required 'version' field should raise ValidationError."""
    bad = {"name": "Test Claim"}
    with pytest.raises(ValidationError) as exc_info:
        validate_claim_json(bad)
    assert "missing required field 'version'" in str(exc_info.value)


def test_validate_claim_json_missing_required_statement():
    """Missing 'statement' inside version should raise."""
    bad = {
        "name": "Test",
        "version": {
            "scope_valid": ["meso"],
            "ontology_assumed": "process",
            "geometry_assumed": "network",
        },
    }
    with pytest.raises(ValidationError) as exc_info:
        validate_claim_json(bad)
    assert "missing required field 'statement'" in str(exc_info.value)


def test_validate_claim_json_invalid_scope():
    """An invalid scope value should raise ValidationError."""
    bad = {
        "name": "Test",
        "version": {
            "statement": "x",
            "scope_valid": ["invalid_scope"],
            "ontology_assumed": "process",
            "geometry_assumed": "network",
        },
    }
    with pytest.raises(ValidationError) as exc_info:
        validate_claim_json(bad)
    assert "not in enum" in str(exc_info.value)


def test_validate_claim_json_invalid_ontology():
    """An invalid ontology value should raise ValidationError."""
    bad = {
        "name": "Test",
        "version": {
            "statement": "x",
            "scope_valid": ["meso"],
            "ontology_assumed": "dualism",
            "geometry_assumed": "network",
        },
    }
    with pytest.raises(ValidationError) as exc_info:
        validate_claim_json(bad)
    assert "not in enum" in str(exc_info.value)


def test_validate_claim_json_invalid_geometry():
    """An invalid geometry value should raise ValidationError."""
    bad = {
        "name": "Test",
        "version": {
            "statement": "x",
            "scope_valid": ["meso"],
            "ontology_assumed": "process",
            "geometry_assumed": "cartesian",
        },
    }
    with pytest.raises(ValidationError) as exc_info:
        validate_claim_json(bad)
    assert "not in enum" in str(exc_info.value)


def test_validate_claim_json_string_valid():
    """A valid JSON string should parse and validate successfully."""
    raw = json.dumps(VALID_CLAIM_JSON)
    result = validate_claim_json_string(raw)
    assert result["name"] == "Test Claim"
    assert result["version"]["statement"] == "Test statement for schema validation"


def test_validate_claim_json_string_malformed():
    """Malformed JSON should raise ValidationError with a clear message."""
    with pytest.raises(ValidationError) as exc_info:
        validate_claim_json_string("not json at all")
    assert "Invalid JSON" in str(exc_info.value)


def test_validate_claim_json_string_not_object():
    """JSON that is not an object (e.g., a bare string) should raise."""
    with pytest.raises(ValidationError) as exc_info:
        validate_claim_json_string('"just a string"')
    assert "Root JSON value must be an object" in str(exc_info.value)


def test_validate_claim_json_empty_scope_array():
    """Empty scope_valid array should fail minItems check."""
    bad = {
        "name": "Test",
        "version": {
            "statement": "x",
            "scope_valid": [],
            "ontology_assumed": "process",
            "geometry_assumed": "network",
        },
    }
    with pytest.raises(ValidationError) as exc_info:
        validate_claim_json(bad)
    assert "minItems" in str(exc_info.value).lower() or "length" in str(exc_info.value).lower()
