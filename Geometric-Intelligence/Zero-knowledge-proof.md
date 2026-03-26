# Zero-Knowledge Proof — Geometric Network Coherence

## Implementation

See `Geometric-Intelligence/geometric_zk.py` for the full implementation.
The original stub (`generate_trojan_proof`) is superseded by the two proof
modes below.

---

## Mode 1 — SHA-256 commitments (fast, honest-verifier ZK)

```python
from Geometric_Intelligence.geometric_zk import (
    prove_in_range, verify_range_proof,
    geometric_zk_prove, verify_geometric_proof,
    proof_to_json, proof_from_json,
)

# Per-node range proof
proof  = prove_in_range(0.97, node_id="state_0")
valid, reason = verify_range_proof(proof)

# Full network proof
network = {"node_0": {"phi_coherence": 0.97}, ...}
bundle = geometric_zk_prove(network)
valid, reason = verify_geometric_proof(bundle)

# JSON round-trip (for transport / storage)
json_str = proof_to_json(bundle)
restored = proof_from_json(json_str)
```

**Protocol**: 8-bit fixed-point decomposition + Fiat-Shamir Σ-protocol
(SHA-256 commitments).

**Security**: Computationally hiding (SHA-256 preimage resistance) and
computationally binding (SHA-256 collision resistance). Openings reveal
individual bits — honest-verifier ZK only.

---

## Mode 2 — Schnorr-Pedersen (full discrete-log ZK)

```python
from Geometric_Intelligence.geometric_zk import (
    prove_in_range_schnorr, verify_range_proof_schnorr,
    geometric_zk_prove_schnorr, verify_geometric_proof_schnorr,
    pedersen_commit, _get_dl_params,
)

# Per-node range proof (ZK against unbounded verifier)
proof  = prove_in_range_schnorr(0.97, node_id="state_0")
valid, reason = verify_range_proof_schnorr(proof)

# Full network proof
bundle = geometric_zk_prove_schnorr(network)
valid, reason = verify_geometric_proof_schnorr(bundle)
```

**Protocol**: Pedersen commitments (C = G^b · H^r mod p) over a
256-bit safe prime group + CDS disjunctive Schnorr OR proof per bit
(Cramer–Damgård–Schoenmakers 1994).

**Security**:
- *Information-theoretically hiding*: verifier learns nothing about bit values
  even with unbounded computation.
- *Computationally binding*: opening two values for the same commitment
  requires computing log_G(H), assumed hard (discrete log problem).
- *Sound*: a cheating prover would need to forge a Schnorr transcript,
  infeasible under the discrete log assumption.

**Performance**: first call ~10–100 ms (256-bit safe prime generation,
cached); subsequent calls ~5–50 ms per node.

---

## Circuit

**Statement**: every node in `encrypted_network` has φ-coherence ∈ [0, 1].

**Witness**: the actual coherence values {cᵢ}.

**Goal**: convince a verifier of the statement without revealing any cᵢ.

The circuit uses an 8-bit fixed-point decomposition of each value into bits
{b₀, …, b₇} and proves each bit ∈ {0, 1} via an OR proof, without
revealing which value each bit takes.

---

## Integration with TrojanEngine

The proof replaces the original pseudocode stub:

```python
# Original stub (Zero-knowledge-proof.md):
def generate_trojan_proof(encrypted_network):
    proof = geometric_zk_prove(encrypted_network)   # SHA-256 mode (fast)
    # or:
    proof = geometric_zk_prove_schnorr(encrypted_network)  # full DL ZK
    return proof
```

The proof bundle is JSON-serializable and can be transmitted to any verifier
without revealing the underlying φ-coherence values of the network nodes.
