# Adversarial pass — plan and trust boundary

Note 2026-11-17: user requested adversarial testing, audit of possible breakages, and fixes to explore. This is a finite software robustness experiment, not a security certification or an empirical linguistic study.

## Preservation

The existing v1 modules, tests, contract and saved execution remain unchanged. Candidate fixes live separately in `../v1_1/`. Probe scripts compare the retained v1 with the candidate. Cases that fail, accept unexpectedly, or hit a scope limit are recorded rather than erased. Prior raw inputs and received specimens are not attacked in place.

## Test boundaries

The pass probes finite numerical inputs and traces; semantic reference and annotation structures; strict JSON envelopes; and safe local run directories. Handwritten and generated adversarial inputs are ILLUSTRATIVE software test fixtures. Pathological iteration runs under hard subprocess deadlines or bounded stand-ins, never deliberately exhausts the host.

A caller may supply corrupted JSON, traces, code indices, duplicated records, inconsistent metadata, deeply nested content, or extreme finite numbers. Actual codebook identity needs a separately supplied trusted codebook. Semantic identity needs a separately supplied trusted reference and assignment. Internally recomputable hashes are integrity bookkeeping, not authentication.

## Finding dispositions

A **REPRODUCED_BREAKAGE** requires observed old-version behavior that violates its declared contract or creates an operational error. A **CANDIDATE_FIX** requires a rerunnable case and a new regression gate, not merely a proposed patch. **EXPECTED_REJECTION** is successful defensive behavior. **TRUST_LIMIT** and **REPRESENTATION_LIMIT** remain visible; they are not silently relabelled bugs or proofs of truth.

Resource and depth limits deliberately narrow the candidate API. They are documented compatibility changes, not guarantees against malicious Python objects, OS races, hostile subprocesses or every combination of allowed workload sizes. Tests do not establish a cryptographic signer, sandbox, immutable ledger, real neural model, or physical coupling.

## Required evidence

Each domain keeps its probe script, machine-readable old/new results, and a scoped report with refuters. The parent will run cross-module checks, the existing v1 suites, preservation tests and a real COBOL integration before summarizing the candidate. Passing tests support only their stated checks; unresolved risks remain named.
