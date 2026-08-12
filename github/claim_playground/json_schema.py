#!/usr/bin/env python3
"""
claim_playground/json_schema.py
earth-systems-physics
CC0 — No Rights Reserved

JSON Schema validation for Claim payloads.
Validates incoming JSON against the Claim dataclass structure before
hydration into Claim / ClaimVersion objects.
"""

import json
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Schema definition (as a Python dict for portability — no external deps)
# ---------------------------------------------------------------------------

CLAIM_VERSION_SCHEMA = {
    "type": "object",
    "required": ["statement", "scope_valid", "ontology_assumed", "geometry_assumed"],
    "properties": {
        "version_number": {"type": "integer", "minimum": 0},
        "statement": {"type": "string", "minLength": 1},
        "mathematical_form": {"type": ["string", "null"]},
        "domain": {"type": "string"},
        "scope_valid": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["micro", "meso", "macro", "cosmic", "contextual"]
            },
            "minItems": 1,
        },
        "ontology_assumed": {
            "type": "string",
            "enum": ["substance", "relational", "process", "field", "pre_linguistic", "institutional", "unspecified"]
        },
        "geometry_assumed": {
            "type": "string",
            "enum": ["euclidean", "riemannian", "fractal", "network", "field", "pre_linguistic", "relational", "unspecified"]
        },
        "green_range": {"type": "object"},
        "yellow_range": {"type": "object"},
        "red_threshold": {"type": "object"},
    },
}

CLAIM_SCHEMA = {
    "type": "object",
    "required": ["name", "version"],
    "properties": {
        "id": {"type": ["string", "null"]},
        "name": {"type": "string", "minLength": 1},
        "domain": {"type": "string"},
        "description": {"type": "string"},
        "tags": {
            "type": "array",
            "items": {"type": "string"},
        },
        "couplings": {
            "type": "array",
            "items": {"type": "string"},
        },
        "related_assumptions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "version": CLAIM_VERSION_SCHEMA,
    },
}


class ValidationError(Exception):
    """Raised when a JSON payload fails schema validation."""
    pass


def _validate_type(value: Any, expected: str, path: str) -> List[str]:
    """Validate a single value against an expected JSON Schema type."""
    errors = []
    if expected == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: expected string, got {type(value).__name__}")
    elif expected == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{path}: expected integer, got {type(value).__name__}")
    elif expected == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object, got {type(value).__name__}")
    elif expected == "array":
        if not isinstance(value, list):
            errors.append(f"{path}: expected array, got {type(value).__name__}")
    elif expected == "null":
        if value is not None:
            errors.append(f"{path}: expected null, got {type(value).__name__}")
    return errors


def _validate_value(value: Any, schema: Dict[str, Any], path: str = "") -> List[str]:
    """Recursively validate a value against a schema fragment."""
    errors = []

    # Handle union types (e.g., ["string", "null"])
    if isinstance(schema.get("type"), list):
        type_errors = []
        for t in schema["type"]:
            sub_schema = {**schema, "type": t}
            sub_errors = _validate_value(value, sub_schema, path)
            if not sub_errors:
                type_errors = []
                break
            type_errors.extend(sub_errors)
        errors.extend(type_errors)
        return errors

    # Primitive type check
    if "type" in schema:
        errors.extend(_validate_type(value, schema["type"], path))
        if errors:
            return errors

    # String constraints
    if schema.get("type") == "string" and isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: string length < {schema['minLength']}")
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{path}: value '{value}' not in enum {schema['enum']}")

    # Integer constraints
    if schema.get("type") == "integer" and isinstance(value, int):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: value {value} < minimum {schema['minimum']}")

    # Object properties
    if schema.get("type") == "object" and isinstance(value, dict):
        # Check required fields
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required field '{req}'")
        # Validate properties
        for key, prop_schema in schema.get("properties", {}).items():
            if key in value:
                errors.extend(_validate_value(value[key], prop_schema, f"{path}.{key}"))

    # Array items
    if schema.get("type") == "array" and isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: array length {len(value)} < minItems {schema['minItems']}")
        item_schema = schema.get("items", {})
        for i, item in enumerate(value):
            errors.extend(_validate_value(item, item_schema, f"{path}[{i}]"))

    return errors


def validate_claim_json(data: Dict[str, Any]) -> None:
    """
    Validate a JSON payload against the Claim schema.

    Raises:
        ValidationError: If the payload is invalid.
    """
    errors = _validate_value(data, CLAIM_SCHEMA, "root")
    if errors:
        raise ValidationError("Schema validation failed: " + "; ".join(errors))


def validate_claim_json_string(raw: str) -> Dict[str, Any]:
    """
    Parse and validate a JSON string payload.

    Returns:
        The parsed dict if valid.

    Raises:
        ValidationError: If JSON is malformed or fails schema validation.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {e}")

    if not isinstance(data, dict):
        raise ValidationError("Root JSON value must be an object")

    validate_claim_json(data)
    return data
