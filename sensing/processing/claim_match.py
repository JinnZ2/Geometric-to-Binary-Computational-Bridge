"""
claim_match — sensing-side wrapper around bridges.claim_evidence.

Pre-loads:

* the shipped repo-root ``CLAIM_TABLE.json`` + ``.claims`` differential-law
  catalogue, and
* the default :class:`~bridges.claim_evidence.MeasurementVocabulary`,

so a sensing node can call::

    from sensing.processing.claim_match import (
        load_repo_claims, verify_obs_file,
    )

without knowing where the catalogue lives.

This is the file the deployment scripts and the per-PR CI gate
import. The pure verifier in :mod:`bridges.claim_evidence` stays
self-contained.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import CLAIM_SCHEMA as cs

from bridges.claim_evidence import (
    BulkVerificationReport,
    MeasurementVocabulary,
    VerificationResult,
    default_vocabulary,
    find_applicable_claims,
    verify_primitive_against_claim,
    verify_primitives_bulk,
)
from sensing.processing.primitives_encoder import (
    Primitive,
    read_obs,
)


# ----------------------------------------------------------------------
# Repo-root paths
# ----------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve_repo_path(name: str, override: Optional[Path]) -> Path:
    if override is not None:
        return Path(override)
    return _REPO_ROOT / name


# ----------------------------------------------------------------------
# Loaders
# ----------------------------------------------------------------------

def load_repo_claims(
    claims_path: Optional[Path] = None,
    table_path: Optional[Path] = None,
) -> List[dict]:
    """
    Load the shipped ``.claims`` + ``CLAIM_TABLE.json`` and return a
    list of CLAIM_SCHEMA dicts. Defaults to the repo-root files; pass
    explicit paths to test against a fork or a snapshot.
    """
    cp = _resolve_repo_path(".claims", claims_path)
    return cs.read_claims(cp)


# ----------------------------------------------------------------------
# Single-Primitive helpers
# ----------------------------------------------------------------------

def claim_for(
    primitive: Primitive,
    claims: Optional[Sequence[dict]] = None,
) -> Optional[dict]:
    """
    Find the Claim dict matching ``primitive.claim_ref``.

    Returns ``None`` if the Primitive has no ``claim_ref`` or the ref
    is not in the supplied claim list (defaults to the repo-root list).
    """
    if primitive.claim_ref is None:
        return None
    catalog = list(claims) if claims is not None else load_repo_claims()
    for c in catalog:
        if str(c.get("id", "")) == primitive.claim_ref:
            return c
    return None


def verify_primitive(
    primitive: Primitive,
    claims: Optional[Sequence[dict]] = None,
    vocabulary: Optional[MeasurementVocabulary] = None,
    *,
    require_bounds_overlap: bool = False,
) -> VerificationResult:
    """
    Verify a single Primitive against the shipped (or supplied) claim
    catalogue using the default measurement vocabulary.
    """
    claim = claim_for(primitive, claims)
    if claim is None:
        ref = primitive.claim_ref or "<none>"
        if primitive.claim_ref is None:
            reason = "primitive has no claim_ref"
        else:
            reason = f"claim_ref={ref!r} not present in shipped catalogue"
        return VerificationResult(ok=False, reasons=(reason,))
    return verify_primitive_against_claim(
        primitive,
        claim,
        vocabulary or default_vocabulary(),
        require_bounds_overlap=require_bounds_overlap,
    )


# ----------------------------------------------------------------------
# Bulk + .obs file
# ----------------------------------------------------------------------

def verify_obs_file(
    obs_path: Path,
    claims: Optional[Sequence[dict]] = None,
    vocabulary: Optional[MeasurementVocabulary] = None,
    *,
    require_bounds_overlap: bool = False,
) -> BulkVerificationReport:
    """
    Read a ``.obs`` file from disk and verify every Primitive in it.

    Used by the per-PR CI gate to assert that every shipped sample
    ``.obs`` file backs claims that exist in the shipped table.
    """
    primitives = read_obs(obs_path)
    catalog = list(claims) if claims is not None else load_repo_claims()
    return verify_primitives_bulk(
        primitives, catalog,
        vocabulary or default_vocabulary(),
        require_bounds_overlap=require_bounds_overlap,
    )


def suggest_claims(
    primitive: Primitive,
    claims: Optional[Sequence[dict]] = None,
    vocabulary: Optional[MeasurementVocabulary] = None,
) -> List[str]:
    """
    Return claim ids whose ``meas`` set overlaps the Primitive's
    measurement vocabulary. Useful for tagging unattributed
    Primitives during deployment.
    """
    catalog = list(claims) if claims is not None else load_repo_claims()
    return find_applicable_claims(
        primitive, catalog,
        vocabulary or default_vocabulary(),
    )


__all__ = [
    "claim_for",
    "load_repo_claims",
    "verify_primitive",
    "verify_obs_file",
    "suggest_claims",
]
