"""
eigenmodes.py  (fabrication/)

Predict eigenmodes from a SubstrateIR for ACOUSTIC topology.

For cheap-fab geometries (≤ ~8 coupled stages), every IR is a
1-D chain:  ground -- C -- L -- C -- L -- ... -- ground (or open).
Mode frequencies are eigenvalues of M⁻¹·K, solved by Jacobi
rotations on a normalized matrix (stdlib, no numpy).

Q prediction is left None unless an explicit damping element
is present -- the verifier reads predicted Q only for diagnostic
context, not for verdict.

Limitations (flagged in claim_back_modes.failure):
  - lumped-element regime only (ka < ~0.3)
  - mode degeneracy on symmetric geometries not resolved
  - higher-order pipe modes show up as unmatched peaks at verify time

License: CC0. Stdlib only.
"""
import math


def _build_lc_system(ir):
    """
    Walk IR.elements to build a 1-D chain representation:
      Cs = list of compliances (store_effort)
      Ls = list of inertances  (store_flow)
    Dissipators contribute to Q later; ignored for f_i prediction.
    """
    Cs, Ls = [], []
    for el in ir.elements:
        if el.kind == "store_effort":
            Cs.append(el.parameter)
        elif el.kind == "store_flow":
            Ls.append(el.parameter)
    return Cs, Ls


def _jacobi_eigvals(A, tol=1e-10, max_iter=200):
    """Classic Jacobi eigenvalue algorithm. Symmetric A."""
    n = len(A)
    A = [row[:] for row in A]
    for _ in range(max_iter):
        # find largest off-diagonal
        p, q, mx = 0, 1, 0.0
        for i in range(n):
            for j in range(i+1, n):
                if abs(A[i][j]) > mx:
                    mx, p, q = abs(A[i][j]), i, j
        if mx < tol:
            break
        app, aqq, apq = A[p][p], A[q][q], A[p][q]
        if abs(apq) < 1e-30:
            break
        theta = (aqq - app) / (2*apq)
        t = (math.copysign(1.0, theta) /
             (abs(theta) + math.sqrt(1 + theta*theta)))
        c = 1.0 / math.sqrt(1 + t*t)
        s = t * c
        for i in range(n):
            aip = A[i][p]
            aiq = A[i][q]
            A[i][p] = c*aip - s*aiq
            A[i][q] = s*aip + c*aiq
        for j in range(n):
            apj = A[p][j]
            aqj = A[q][j]
            A[p][j] = c*apj - s*aqj
            A[q][j] = s*apj + c*aqj
        A[p][q] = A[q][p] = 0.0
    return [A[i][i] for i in range(n)]


def _eigvals_1d_chain(Cs, Ls):
    """
    For a 1-D chain of alternating C (to ground) and L (series),
    natural frequencies come from the generalized eigenproblem
        K · Φ = ω² M · Φ
    K from 1/C (tridiagonal stiffness), M from L (diagonal mass).
    Reduced to standard form via A = M^{-1/2} K M^{-1/2}.
    """
    if not Cs or not Ls:
        return []
    n = min(len(Cs), len(Ls))
    K = [[0.0]*n for _ in range(n)]
    M = [[0.0]*n for _ in range(n)]
    for i in range(n):
        K[i][i] = 1.0 / Cs[i] + (1.0 / Cs[i+1] if i+1 < len(Cs) else 0.0)
        if i > 0:
            K[i][i-1] = -1.0 / Cs[i]
            K[i-1][i] = -1.0 / Cs[i]
        M[i][i] = Ls[i]
    Mhalf_inv = [1.0 / math.sqrt(M[i][i]) for i in range(n)]
    A = [[K[i][j] * Mhalf_inv[i] * Mhalf_inv[j]
          for j in range(n)] for i in range(n)]
    eigs = _jacobi_eigvals(A)
    freqs = []
    for lam in eigs:
        if lam > 0:
            freqs.append(math.sqrt(lam) / (2*math.pi))
    freqs.sort()
    return freqs


def predict_eigenmodes(ir):
    """
    Returns ordered list of dicts:
      [{"f": Hz, "mode_index": n, "kind": "lumped"}, ...]
    """
    Cs, Ls = _build_lc_system(ir)
    freqs = _eigvals_1d_chain(Cs, Ls)
    return [{"f": f, "mode_index": i, "kind": "lumped"}
            for i, f in enumerate(freqs)]
