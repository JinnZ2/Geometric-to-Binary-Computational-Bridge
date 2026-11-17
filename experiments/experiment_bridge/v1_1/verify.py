"""Composed consumer gate; external contexts are trust inputs, not truth proofs.

A valid EB01 hash alone does not validate numerical or semantic claims. This
helper returns a decoded payload only after both separately supplied contexts
match it. It does not authenticate the person supplying those contexts.
"""
from .core import validate_trace
from .semantics import validate_annotation
from .wire import decode_record


def checked_decode(record, levels, rows, assignments=None, evidential_row_id=None):
    """Return a decoded trace envelope only after explicit context checks.

    `levels` must be the caller's codebooks, not values trusted from the payload.
    `rows` and `assignments` must likewise come from the caller's selected
    reference/policy. A malicious caller controlling all those inputs can still
    construct a consistently false account. No semantic truth is certified.
    No independent target/measurement is supplied here: another internally
    consistent target can pass. This is not sensor or encoder attestation.
    """
    if levels is None or rows is None:
        raise ValueError("External levels and reference rows are required")
    payload = decode_record(record)
    trace = payload.get("trace")
    if not isinstance(trace, dict):
        raise ValueError("Envelope must contain a trace object")
    errors = validate_trace(trace, levels)
    if errors:
        raise ValueError("Numerical validation failed: " + "; ".join(errors))
    errors = validate_annotation(trace, rows, assignments, evidential_row_id)
    if errors:
        raise ValueError("Annotation validation failed: " + "; ".join(errors))
    return payload
