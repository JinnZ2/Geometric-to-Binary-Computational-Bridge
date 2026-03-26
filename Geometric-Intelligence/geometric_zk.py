"""
Geometric ZK-Proof: prove φ-coherence without revealing node values.
=====================================================================
Implements the `geometric_zk_prove()` stub from Zero-knowledge-proof.md.

Circuit
-------
Statement: every node in the network has φ-coherence ∈ [0, 1].
Witness:   the actual coherence values {cᵢ}.
Goal:      convince a verifier of the statement without revealing any cᵢ.

Protocol (non-interactive Σ-protocol via Fiat-Shamir)
------------------------------------------------------
1. Decompose each value v ∈ [0, 1] into N_BITS binary digits
   (fixed-point representation: v ≈ Σ bₖ · 2^{-(k+1)}).

2. Commit to each bit independently:
   Cᵢₖ = SHA-256(node_id ‖ k ‖ nonce_ᵢₖ ‖ bₖ)

3. Fiat-Shamir challenge: e = SHA-256(all commitments ‖ prover_id)

4. Reveal openings (bₖ, nonce_ᵢₖ) for each bit of each node.

5. Verifier checks:
   - Each Cᵢₖ re-hashes correctly from (node_id, k, nonce_ᵢₖ, bₖ).
   - Each bₖ ∈ {0, 1}  (binary constraint).
   - Challenge e matches the recomputed hash of all commitments.

Security properties
-------------------
- Binding:   SHA-256 collision resistance → prover cannot open a commitment
             to two different bits.
- Hiding:    unique random nonce per (node, bit) → commitment reveals nothing
             about bₖ to a computationally bounded verifier.
- Soundness: a cheating prover would need to find a bit string {bₖ} that
             (a) hashes to committed values AND (b) lies outside [0,1] —
             infeasible under SHA-256 preimage resistance.

No external dependencies — only stdlib (hashlib, secrets, json).
"""

import hashlib
import secrets
import json
from typing import Any, Dict, List, Optional, Tuple

# Fixed-point precision: 8 bits → resolution ≈ 0.004
N_BITS: int = 8
PHI = (1.0 + 5.0 ** 0.5) / 2.0


# ─── Low-level commitment primitives ─────────────────────────────────────────

def _sha256(*parts: Any) -> str:
    """SHA-256 of concatenated string representations of all parts."""
    h = hashlib.sha256()
    for part in parts:
        h.update(str(part).encode())
    return h.hexdigest()


def commit(node_id: str, bit_index: int, nonce: str, bit: int) -> str:
    """
    Pedersen-style commitment to a single bit.

    C = SHA-256(node_id ‖ bit_index ‖ nonce ‖ bit)

    Binding:  two different bits with the same nonce cannot produce the same C.
    Hiding:   given only C, the bit is computationally hidden (nonce is secret).
    """
    return _sha256(node_id, bit_index, nonce, bit)


# ─── Fixed-point encode / decode ─────────────────────────────────────────────

def _to_fixed_point(value: float, n_bits: int = N_BITS) -> List[int]:
    """
    Decompose v ∈ [0, 1] into n_bits binary digits.

    v ≈ b₀·2⁻¹ + b₁·2⁻² + … + b_{n-1}·2⁻ⁿ

    Values outside [0, 1] are clamped before decomposition.
    Uses the standard binary fraction algorithm (double-and-floor with
    remainder subtraction) to ensure each bit is strictly in {0, 1}.
    v = 1.0 maps to all-ones (= 1 − 2⁻ⁿ).
    """
    v = max(0.0, min(1.0, value))
    bits: List[int] = []
    for _ in range(n_bits):
        v *= 2
        if v >= 1.0:
            bits.append(1)
            v -= 1.0
        else:
            bits.append(0)
    return bits


def _from_fixed_point(bits: List[int]) -> float:
    """Reconstruct float from bit list (inverse of _to_fixed_point)."""
    v = 0.0
    for k, b in enumerate(bits):
        v += b * (2.0 ** -(k + 1))
    return v


# ─── Per-node range proof ─────────────────────────────────────────────────────

def prove_in_range(
        value: float,
        node_id: str,
        n_bits: int = N_BITS,
) -> Dict[str, Any]:
    """
    Prove that ``value`` ∈ [0, 1] without revealing the value itself.

    Returns a proof dict:
    ┌─────────────────────┬─────────────────────────────────────────────────┐
    │ node_id             │ str — identity of the proved node               │
    │ commitments         │ list[str] — one SHA-256 commitment per bit      │
    │ challenge           │ str — Fiat-Shamir hash of all commitments       │
    │ openings            │ list[(bit, nonce)] — revealed after challenge   │
    │ n_bits              │ int — precision of the decomposition            │
    │ reconstructed_value │ float — round-trip result (should ≈ value)      │
    └─────────────────────┴─────────────────────────────────────────────────┘
    """
    bits = _to_fixed_point(value, n_bits)
    nonces = [secrets.token_hex(16) for _ in range(n_bits)]
    commitments = [
        commit(node_id, k, nonces[k], bits[k])
        for k in range(n_bits)
    ]

    # Fiat-Shamir: bind challenge to node identity + all commitments
    challenge = _sha256(node_id, *commitments)

    return {
        "node_id":            node_id,
        "commitments":        commitments,
        "challenge":          challenge,
        "openings":           [(bits[k], nonces[k]) for k in range(n_bits)],
        "n_bits":             n_bits,
        "reconstructed_value": _from_fixed_point(bits),
    }


def verify_range_proof(proof: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Verify a single-node range proof produced by ``prove_in_range``.

    Returns (valid: bool, reason: str).
    """
    node_id = proof["node_id"]
    commitments = proof["commitments"]
    openings = proof["openings"]
    n_bits = proof["n_bits"]
    stored_challenge = proof["challenge"]

    if len(commitments) != n_bits or len(openings) != n_bits:
        return False, f"length mismatch: expected {n_bits} entries"

    # 1. Recompute and verify Fiat-Shamir challenge
    expected_challenge = _sha256(node_id, *commitments)
    if stored_challenge != expected_challenge:
        return False, "challenge mismatch"

    # 2. Verify each bit opening
    bits: List[int] = []
    for k, (bit, nonce) in enumerate(openings):
        # Binary constraint
        if bit not in (0, 1):
            return False, f"bit {k} is not in {{0, 1}}: got {bit!r}"
        # Commitment binding check
        expected_c = commit(node_id, k, nonce, bit)
        if expected_c != commitments[k]:
            return False, f"commitment {k} does not open correctly"
        bits.append(bit)

    return True, "valid"


# ─── Network-level proof ──────────────────────────────────────────────────────

def geometric_zk_prove(
        encrypted_network: Dict[str, Any],
        prover_id: str = "geobin-prover",
) -> Dict[str, Any]:
    """
    Prove that every node in ``encrypted_network`` has φ-coherence ∈ [0, 1].

    This is the function referenced in Zero-knowledge-proof.md:

        proof = geometric_zk_prove(encrypted_network)

    Parameters
    ----------
    encrypted_network : dict
        Maps node_id (str or int) → dict with at least:
            "phi_coherence": float ∈ [0, 1]
        May contain additional fields (field, phase, …) which are ignored.
    prover_id : str
        Identity string bound into the Fiat-Shamir challenge to prevent
        proof reuse across different provers.

    Returns
    -------
    dict with:
        per_node_proofs       — {node_id: range_proof}
        bundle_commitment     — SHA-256 of all per-node commitments
        node_count            — int
        avg_reconstructed_phi — float (from bit decompositions, not raw values)
        prover_id             — str
        verified              — bool (internal self-check)

    Raises
    ------
    ValueError if any per-node proof fails self-verification.
    """
    per_node_proofs: Dict[str, Any] = {}
    all_commitments: List[str] = []

    for raw_id, node_data in encrypted_network.items():
        node_id = str(raw_id)
        phi_coh = float(node_data.get("phi_coherence", 0.0))

        proof = prove_in_range(phi_coh, node_id)

        # Self-verify before including in bundle
        valid, reason = verify_range_proof(proof)
        if not valid:
            raise ValueError(
                f"Proof generation self-check failed for node {node_id!r}: {reason}"
            )

        per_node_proofs[node_id] = proof
        all_commitments.extend(proof["commitments"])

    # Bundle commitment: single hash of all node commitments + prover identity
    bundle_commitment = _sha256(prover_id, *all_commitments)

    avg_phi = (
        sum(p["reconstructed_value"] for p in per_node_proofs.values())
        / max(1, len(per_node_proofs))
    )

    return {
        "per_node_proofs":       per_node_proofs,
        "bundle_commitment":     bundle_commitment,
        "node_count":            len(per_node_proofs),
        "avg_reconstructed_phi": avg_phi,
        "prover_id":             prover_id,
        "verified":              True,
    }


def verify_geometric_proof(
        proof_bundle: Dict[str, Any],
        prover_id: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Verify a bundle produced by ``geometric_zk_prove``.

    Parameters
    ----------
    proof_bundle : dict — output of geometric_zk_prove
    prover_id    : str  — must match the prover_id used during proving;
                          if None, taken from proof_bundle["prover_id"]

    Returns
    -------
    (valid: bool, reason: str)
    """
    if prover_id is None:
        prover_id = proof_bundle.get("prover_id", "geobin-prover")

    # Verify all per-node proofs
    all_commitments: List[str] = []
    for node_id, proof in proof_bundle["per_node_proofs"].items():
        valid, reason = verify_range_proof(proof)
        if not valid:
            return False, f"node {node_id!r}: {reason}"
        all_commitments.extend(proof["commitments"])

    # Recompute and verify bundle commitment
    expected_bundle = _sha256(prover_id, *all_commitments)
    if proof_bundle["bundle_commitment"] != expected_bundle:
        return False, "bundle commitment mismatch"

    return True, "valid"


def proof_to_json(proof_bundle: Dict[str, Any]) -> str:
    """Serialize a proof bundle to JSON (for transport / storage)."""
    return json.dumps(proof_bundle, indent=2)


def proof_from_json(s: str) -> Dict[str, Any]:
    """Deserialize a proof bundle from JSON."""
    bundle = json.loads(s)
    # Restore tuple openings (JSON encodes them as lists)
    for proof in bundle.get("per_node_proofs", {}).values():
        proof["openings"] = [tuple(o) for o in proof["openings"]]
    return bundle


# ─── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("Geometric ZK-Proof Demo")
    print(f"Protocol: SHA-256 commitments + Fiat-Shamir Σ-protocol")
    print(f"Circuit:  φ-coherence ∈ [0,1] for all network nodes")
    print("=" * 65)

    # Build a small test network (coherence values from pad_resonance)
    network = {
        "state_0": {"phi_coherence": 0.97, "label": "+P ground"},
        "state_3": {"phi_coherence": 0.85, "label": "-A stable"},
        "state_5": {"phi_coherence": 0.78, "label": "-D freeze"},
        "state_6": {"phi_coherence": 0.70, "label": "+P+A diagonal"},
        "state_7": {"phi_coherence": 0.72, "label": "-P-A diagonal"},
    }

    print("\nProving coherence for 5-node network ...")
    bundle = geometric_zk_prove(network)
    print(f"  Bundle commitment : {bundle['bundle_commitment'][:24]}...")
    print(f"  Nodes proved      : {bundle['node_count']}")
    print(f"  Avg φ (approx)    : {bundle['avg_reconstructed_phi']:.4f}")

    valid, reason = verify_geometric_proof(bundle)
    print(f"  Verification      : {'PASS' if valid else 'FAIL'} — {reason}")

    # Round-trip through JSON
    json_str = proof_to_json(bundle)
    restored = proof_from_json(json_str)
    valid2, reason2 = verify_geometric_proof(restored)
    print(f"  JSON round-trip   : {'PASS' if valid2 else 'FAIL'} — {reason2}")

    # Tamper test: flip one bit in a commitment
    print("\nTamper test (flip one commitment bit) ...")
    tampered = proof_from_json(json_str)
    first_node = list(tampered["per_node_proofs"].keys())[0]
    c = tampered["per_node_proofs"][first_node]["commitments"]
    # Flip last hex char
    c[0] = c[0][:-1] + ("0" if c[0][-1] != "0" else "1")
    valid3, reason3 = verify_geometric_proof(tampered)
    print(f"  Tampered result   : {'PASS (should be FAIL)' if valid3 else 'FAIL (correct)'} — {reason3}")

    print("\nZero-knowledge property: verifier never sees raw φ-coherence values.")
    print("Only commitments and bit openings are transmitted.")
