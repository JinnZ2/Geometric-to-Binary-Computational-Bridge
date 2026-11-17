"""Lossless reference routing, not linguistic validation or codebook semantics."""

from collections import Counter
from copy import deepcopy
import hashlib
import json


_COLLECTIONS = ("place_structures", "evidentials")
_TEXT_FIELDS = ("english", "class", "source_url", "retrieved", "mapping_reason")
_MAPPING_STATUSES = ("PROPOSED", "OBSERVED", "DIFFERS", "VOID")


def _digest(value):
    def check(item):
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise ValueError("JSON object keys must be strings")
            for child in item.values():
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)
        elif item is not None and not isinstance(item, (str, int, float, bool)):
            raise ValueError("reference must contain JSON-compatible content")

    check(value)
    try:
        encoded = json.dumps(value, sort_keys=True, ensure_ascii=True,
                             allow_nan=False, separators=(",", ":")).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise ValueError("reference must contain finite JSON-compatible content") from exc
    return hashlib.sha256(encoded).hexdigest()


def _integer(value, minimum):
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _source_view(source, collection):
    if not isinstance(source, dict) or collection not in _COLLECTIONS:
        raise ValueError("source must be an object in a known collection")
    for field in _TEXT_FIELDS:
        if not isinstance(source.get(field), str) or not source[field].strip():
            raise ValueError(f"source {field} must be nonempty text")
    alternatives = source.get("alternatives")
    if not isinstance(alternatives, list) or any(not isinstance(x, str) for x in alternatives):
        raise ValueError("alternatives must be a list of strings")
    for field, kind in (("recalled_form", str), ("in_user_list", bool)):
        if field in source and not isinstance(source[field], kind):
            raise ValueError(f"source {field} has an invalid type")
    if source.get("mapping_status") not in _MAPPING_STATUSES:
        raise ValueError("unsupported recorded mapping_status")
    if "gismu" not in source or "place_structure_verbatim" not in source:
        raise ValueError("source must explicitly record identifier and structure, including nulls")
    identifier, structure = source["gismu"], source["place_structure_verbatim"]
    status = source.get("structure_status")
    if status == "VOID" and identifier is None and structure is None:
        lexical = "LEXICAL_VOID"
    elif status == "OBSERVED" and all(isinstance(x, str) and x.strip()
                                       for x in (identifier, structure)):
        lexical = "PRESENT"
    else:
        raise ValueError("structure_status and recorded identifier/structure disagree")
    source_class = source["class"]
    if (collection == "evidentials") != (source_class == "evidential"):
        raise ValueError("evidential class and source collection disagree")
    role = "evidential" if collection == "evidentials" else (
        "recall_check" if source_class == "recall_check" else "mapping")
    return identifier, role, lexical


def normalize_reference(data):
    """Return distinct rows; ids hash role/source plus a one-based duplicate occurrence.

    Source indexes are zero-based. Recorded gismu is only an identifier. Status
    checks concern the supplied schema, not the truth of its linguistic wording.
    """
    if not isinstance(data, dict) or set(data) != set(_COLLECTIONS):
        raise ValueError("reference must contain place_structures and evidentials arrays")
    rows, occurrences = [], Counter()
    for collection in _COLLECTIONS:
        if not isinstance(data[collection], list):
            raise ValueError(f"{collection} must be an array")
        for index, source in enumerate(data[collection]):
            identifier, role, lexical = _source_view(source, collection)
            digest = _digest({"role": role, "source": source})
            occurrences[digest] += 1
            rows.append({"row_id": f"{role}:{digest}:{occurrences[digest]}",
                         "identifier": identifier, "english": source["english"],
                         "role": role, "lexical_status": lexical,
                         "source_collection": collection, "source_index": index,
                         "source": deepcopy(source)})
    return rows


def _check_rows(rows):
    if not isinstance(rows, list):
        raise ValueError("rows must be a normalized list")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("normalized row must be an object")
        identifier, role, lexical = _source_view(row.get("source"), row.get("source_collection"))
        if (row.get("identifier"), row.get("role"), row.get("lexical_status"), row.get("english")) != (
                identifier, role, lexical, row["source"]["english"]):
            raise ValueError("normalized metadata disagrees with source")
        if not _integer(row.get("source_index"), 0):
            raise ValueError("source_index must be a nonnegative integer")
        prefix = f"{role}:{_digest({'role': role, 'source': row['source']})}:"
        row_id = row.get("row_id")
        suffix = row_id[len(prefix):] if isinstance(row_id, str) and row_id.startswith(prefix) else ""
        if (not suffix.isascii() or not suffix.isdecimal() or int(suffix) < 1
                or str(int(suffix)) != suffix):
            raise ValueError("row_id must identify its role/source and positive occurrence")


def find_rows(rows, identifier=None, english=None, role=None):
    """Return deep-copied exact matches without collapsing identifiers or occurrences.

    None disables a filter; select lexical voids by their English label or status.
    """
    _check_rows(rows)
    if any(value is not None and not isinstance(value, str) for value in (identifier, english, role)):
        raise ValueError("filters must be text or None")
    if role is not None and role not in ("mapping", "recall_check", "evidential"):
        raise ValueError("unknown role filter")
    return deepcopy([row for row in rows if all(value is None or row[field] == value
                    for field, value in (("identifier", identifier), ("english", english),
                                         ("role", role)))])


def annotate_trace(trace, rows, assignments=None, evidential_row_id=None):
    """Copy a trace and add semantic_status/semantic_row_id/semantic_row per step.

    Top-level evidential is a separate normalized row (or None).
    semantic_provenance records version, normalized-reference SHA-256, explicit
    assignments and evidential_row_id. Neither routing nor hashes certify truth.
    Only level, numerical_status and code_index are required on numerical steps;
    numerical transitions remain core's responsibility. Reserved output collisions
    are rejected instead of erasing previously supplied annotations.
    """
    _check_rows(rows)
    by_id = {row["row_id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("row ids must be unique")
    if not isinstance(trace, dict) or not isinstance(trace.get("steps"), list):
        raise ValueError("trace must be an object with a steps array")
    if any(key in trace for key in ("semantic_provenance", "evidential")):
        raise ValueError("trace already contains reserved semantic output fields")
    assignments = {} if assignments is None else assignments
    if not isinstance(assignments, dict):
        raise ValueError("assignments must be a dictionary")

    def resolve(row_id, role):
        if not isinstance(row_id, str) or row_id not in by_id or by_id[row_id]["role"] != role:
            raise ValueError(f"assignment must identify one known {role} row")
        return by_id[row_id]

    for key, row_id in assignments.items():
        if (not isinstance(key, tuple) or len(key) != 2 or not _integer(key[0], 1)
                or not _integer(key[1], 0)):
            raise ValueError("assignment keys must be (positive level, nonnegative code_index)")
        resolve(row_id, "mapping")
    evidential = None if evidential_row_id is None else resolve(evidential_row_id, "evidential")
    result = deepcopy(trace)
    for step in result["steps"]:
        if not isinstance(step, dict) or not _integer(step.get("level"), 1):
            raise ValueError("each step must record a positive integer level")
        if "code_index" not in step:
            raise ValueError("each step must explicitly record code_index")
        if any(key in step for key in ("semantic_status", "semantic_row_id", "semantic_row")):
            raise ValueError("step already contains reserved semantic output fields")
        status, index = step.get("numerical_status"), step["code_index"]
        if status == "REJECTED" and index is None:
            row, semantic_status = None, "NOT_APPLICABLE"
        elif status == "ACCEPTED" and _integer(index, 0):
            row_id = assignments.get((step["level"], index))
            row = by_id[row_id] if row_id is not None else None
            semantic_status = row["lexical_status"] if row is not None else "UNMAPPED"
        else:
            raise ValueError("numerical_status and code_index disagree")
        step.update(semantic_status=semantic_status,
                    semantic_row_id=row["row_id"] if row is not None else None,
                    semantic_row=deepcopy(row))
    result["evidential"] = deepcopy(evidential)
    result["semantic_provenance"] = {
        "version": "experiment-bridge/v1", "reference_sha256": _digest(rows),
        "assignments": [{"level": key[0], "code_index": key[1], "row_id": row_id}
                        for key, row_id in sorted(assignments.items())],
        "evidential_row_id": evidential_row_id,
    }
    return result
