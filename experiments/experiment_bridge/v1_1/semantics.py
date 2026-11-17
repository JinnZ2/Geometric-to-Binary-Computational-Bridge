"""Lossless bounded reference routing, not linguistic truth or authentication."""

from collections import Counter
from copy import deepcopy
import hashlib
import json
import math


_COLLECTIONS = ("place_structures", "evidentials")
_TEXT_FIELDS = ("english", "class", "source_url", "retrieved", "mapping_reason")
_MAPPING_STATUSES = ("PROPOSED", "OBSERVED", "DIFFERS", "VOID")
SEMANTIC_VERSION = "experiment-bridge/v1.1"
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 100_000
MAX_JSON_STRING_CHARS = 65_536
MAX_JSON_TEXT_CHARS = 1_000_000
MAX_JSON_INTEGER_BITS = 1_024
MAX_REFERENCE_ROWS = 4_096
MAX_ROW_OCCURRENCE = MAX_REFERENCE_ROWS
SEMANTIC_STEP_FIELDS = ("semantic_status", "semantic_row_id", "semantic_row")
SEMANTIC_TOP_FIELDS = ("semantic_provenance", "evidential")


def _check_json(value):
    """Iteratively bound expanded JSON, counting repeated aliases and object keys.

    Root depth is zero; keys count as nodes and text. Only active-path aliases
    are cycles. These software policy limits are not empirical dataset limits.
    """
    stack, active, nodes, text = [(value, 0, False)], set(), 0, 0
    while stack:
        item, depth, leaving = stack.pop()
        if leaving:
            active.remove(id(item))
            continue
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            raise ValueError("JSON node/depth limit exceeded")
        if isinstance(item, (dict, list)):
            if id(item) in active:
                raise ValueError("cyclic JSON content is not supported")
            if len(item) > MAX_JSON_NODES - nodes:
                raise ValueError("JSON node limit exceeded")
            active.add(id(item))
            stack.append((item, depth, True))
            if isinstance(item, dict):
                for key in item:
                    if not isinstance(key, str):
                        raise ValueError("JSON object keys must be strings")
                    if len(key) > MAX_JSON_STRING_CHARS:
                        raise ValueError("JSON string limit exceeded")
                    nodes += 1
                    text += len(key)
                children = item.values()
            else:
                children = item
            stack.extend((child, depth + 1, False) for child in children)
        elif isinstance(item, str):
            if len(item) > MAX_JSON_STRING_CHARS:
                raise ValueError("JSON string limit exceeded")
            text += len(item)
        elif isinstance(item, bool) or item is None:
            pass
        elif isinstance(item, int):
            if item.bit_length() > MAX_JSON_INTEGER_BITS:
                raise ValueError("JSON integer bit limit exceeded")
        elif isinstance(item, float):
            if not math.isfinite(item):
                raise ValueError("JSON numbers must be finite")
        else:
            raise ValueError("content must be JSON-compatible")
        if nodes > MAX_JSON_NODES or text > MAX_JSON_TEXT_CHARS:
            raise ValueError("JSON node/text limit exceeded")


def _digest(value):
    _check_json(value)
    try:
        encoded = json.dumps(value, sort_keys=True, ensure_ascii=True,
                             allow_nan=False, separators=(",", ":")).encode("ascii")
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("content must be finite bounded JSON-compatible content") from exc
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
    """Copy bounded sources; ids hash role/source and one-based duplicate occurrence.

    Source indexes are zero-based. Unknown JSON fields remain untouched. Neither
    identifiers, source wording nor hashes certify linguistic truth or origin.
    """
    if not isinstance(data, dict) or set(data) != set(_COLLECTIONS):
        raise ValueError("reference must contain place_structures and evidentials arrays")
    _check_json(data)
    if any(not isinstance(data[key], list) for key in _COLLECTIONS):
        raise ValueError("reference collections must be arrays")
    if sum(len(data[key]) for key in _COLLECTIONS) > MAX_REFERENCE_ROWS:
        raise ValueError("reference row limit exceeded")
    rows, occurrences = [], Counter()
    for collection in _COLLECTIONS:
        for index, source in enumerate(data[collection]):
            identifier, role, lexical = _source_view(source, collection)
            digest = _digest({"role": role, "source": source})
            occurrences[digest] += 1
            rows.append({"row_id": f"{role}:{digest}:{occurrences[digest]}",
                         "identifier": identifier, "english": source["english"],
                         "role": role, "lexical_status": lexical,
                         "source_collection": collection, "source_index": index,
                         "source": deepcopy(source)})
    _check_json(rows)
    return rows


def _check_rows(rows):
    if not isinstance(rows, list) or len(rows) > MAX_REFERENCE_ROWS:
        raise ValueError("rows must be a bounded normalized list")
    _check_json(rows)
    ids, positions, groups = set(), set(), {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("normalized row must be an object")
        identifier, role, lexical = _source_view(row.get("source"), row.get("source_collection"))
        if (row.get("identifier"), row.get("role"), row.get("lexical_status"), row.get("english")) != (
                identifier, role, lexical, row["source"]["english"]):
            raise ValueError("normalized metadata disagrees with source")
        index = row.get("source_index")
        if not _integer(index, 0) or index >= MAX_REFERENCE_ROWS:
            raise ValueError("source_index must be a bounded nonnegative integer")
        prefix = f"{role}:{_digest({'role': role, 'source': row['source']})}:"
        row_id = row.get("row_id")
        suffix = row_id[len(prefix):] if isinstance(row_id, str) and row_id.startswith(prefix) else ""
        # Bound text before int conversion; no dependence on Python's digit cap.
        if (not suffix or len(suffix) > len(str(MAX_ROW_OCCURRENCE))
                or not suffix.isascii() or not suffix.isdecimal() or suffix[0] == "0"):
            raise ValueError("row_id must identify its role/source and bounded positive occurrence")
        occurrence = int(suffix)
        if occurrence > MAX_ROW_OCCURRENCE or occurrence > index + 1:
            raise ValueError("row occurrence is impossible for source_index")
        position = (row["source_collection"], index)
        if row_id in ids or position in positions:
            raise ValueError("row ids and source collection/index positions must be unique")
        ids.add(row_id)
        positions.add(position)
        groups.setdefault(prefix, []).append((index, occurrence))
    # Subsets may omit occurrences and input order is irrelevant. Supplied
    # duplicate metadata must still admit a possible original source ordering.
    for group in groups.values():
        ordered = sorted(group)
        for (i, occurrence), (j, later) in zip(ordered, ordered[1:]):
            if not 0 < later - occurrence <= j - i:
                raise ValueError("duplicate occurrence order disagrees with source positions")


def find_rows(rows, identifier=None, english=None, role=None):
    """Deep-copy exact matches; subsets/reordering retain source indexes and ids."""
    _check_rows(rows)
    if any(value is not None and not isinstance(value, str) for value in (identifier, english, role)):
        raise ValueError("filters must be text or None")
    if role is not None and role not in ("mapping", "recall_check", "evidential"):
        raise ValueError("unknown role filter")
    return deepcopy([row for row in rows if all(value is None or row[field] == value
                    for field, value in (("identifier", identifier), ("english", english),
                                         ("role", role)))])


def annotate_trace(trace, rows, assignments=None, evidential_row_id=None):
    """Copy bounded JSON trace and add explicit semantic routing, never certify truth.

    Only level, numerical_status and code_index are required on numerical steps;
    numerical transitions remain core's responsibility. Reserved output collisions
    are rejected. Assignments may include unused numerical codes/levels.
    """
    _check_rows(rows)
    by_id = {row["row_id"]: row for row in rows}
    if not isinstance(trace, dict) or not isinstance(trace.get("steps"), list):
        raise ValueError("trace must be an object with a steps array")
    _check_json(trace)
    if any(key in trace for key in SEMANTIC_TOP_FIELDS):
        raise ValueError("trace already contains reserved semantic output fields")
    assignments = {} if assignments is None else assignments
    if not isinstance(assignments, dict) or len(assignments) > MAX_JSON_NODES:
        raise ValueError("assignments must be a bounded dictionary")

    def resolve(row_id, role):
        if not isinstance(row_id, str) or row_id not in by_id or by_id[row_id]["role"] != role:
            raise ValueError(f"assignment must identify one known {role} row")
        return by_id[row_id]

    for key, row_id in assignments.items():
        if (not isinstance(key, tuple) or len(key) != 2 or not _integer(key[0], 1)
                or not _integer(key[1], 0) or any(x.bit_length() > MAX_JSON_INTEGER_BITS for x in key)):
            raise ValueError("assignment keys must be (bounded positive level, nonnegative code_index)")
        resolve(row_id, "mapping")
    evidential = None if evidential_row_id is None else resolve(evidential_row_id, "evidential")
    result = deepcopy(trace)
    for step in result["steps"]:
        if not isinstance(step, dict) or not _integer(step.get("level"), 1):
            raise ValueError("each step must record a positive integer level")
        if "code_index" not in step:
            raise ValueError("each step must explicitly record code_index")
        if any(key in step for key in SEMANTIC_STEP_FIELDS):
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
        "version": SEMANTIC_VERSION, "reference_sha256": _digest(rows),
        "assignments": [{"level": key[0], "code_index": key[1], "row_id": row_id}
                        for key, row_id in sorted(assignments.items())],
        "evidential_row_id": evidential_row_id,
    }
    return result


def validate_annotation(annotated_trace, rows, assignments=None, evidential_row_id=None):
    """Return errors comparing annotations to EXTERNALLY trusted routing inputs.

    Never infer rows/assignments/evidential selection from payload provenance.
    None assignments means an empty trusted map. This is consumer consistency,
    not authentication, semantic truth, numeric checking or checkpoint binding.
    Reuses the producer's routing rules; it is not an independent implementation
    of those rules. All inputs are unmodified; malformed inputs return errors.
    """
    try:
        _check_json(annotated_trace)
        if not isinstance(annotated_trace, dict) or not isinstance(annotated_trace.get("steps"), list):
            raise ValueError("annotated trace must be an object with a steps array")
        base = {key: value for key, value in annotated_trace.items() if key not in SEMANTIC_TOP_FIELDS}
        base["steps"] = []
        for step in annotated_trace["steps"]:
            if not isinstance(step, dict):
                raise ValueError("annotated step must be an object")
            base["steps"].append({key: value for key, value in step.items()
                                  if key not in SEMANTIC_STEP_FIELDS})
        expected = annotate_trace(base, rows, assignments, evidential_row_id)
        errors = []
        for key in SEMANTIC_TOP_FIELDS:
            if key not in annotated_trace or _digest(annotated_trace[key]) != _digest(expected[key]):
                errors.append(f"{key} disagrees with trusted routing inputs")
        for index, (supplied, wanted) in enumerate(zip(annotated_trace["steps"], expected["steps"])):
            for key in SEMANTIC_STEP_FIELDS:
                if key not in supplied or _digest(supplied[key]) != _digest(wanted[key]):
                    errors.append(f"steps[{index}].{key} disagrees with trusted routing inputs")
        return errors
    except ValueError as exc:
        return [f"invalid semantic input: {exc}"]
