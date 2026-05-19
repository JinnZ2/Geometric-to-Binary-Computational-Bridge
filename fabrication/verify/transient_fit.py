"""
transient_fit.py  (fabrication/verify/)

Minimal nonlinear least squares for two step-response shapes.
Stdlib only. Uses Gauss-Newton with numerical Jacobian. Robust
enough for clean step data with 5-10% noise.

  fit_first_order(t, y) -> {"A","tau","b","r2","ssr"}
                           y(t) = A·(1 - exp(-t/τ)) + b

  fit_second_order(t, y) -> {"A","wn","zeta","b","r2","ssr"}
                            underdamped 2nd-order step response

License: CC0. Stdlib only.
"""
import math


def _gauss_newton(residual_fn, params, max_iter=50, tol=1e-9,
                  clamp=None):
    """residual_fn(params) -> list of residuals.
    Numerical Jacobian by central differences.
    `clamp(params) -> params` optional callback applied after each
    step so the optimizer can't wander outside valid parameter
    regions (e.g. ζ ∈ (0,1), ωn > 0). Without it, GN can walk into
    a region where the residual clamps the physics but the gradient
    drops to zero, and the optimizer gets stuck."""
    params = list(params)
    if clamp:
        params = clamp(params)
    for _ in range(max_iter):
        r = residual_fn(params)
        J = _jacobian(residual_fn, params, r)
        # solve normal equations (J^T J) dp = -J^T r
        n = len(params)
        JTJ = [[sum(J[k][i]*J[k][j] for k in range(len(r)))
                for j in range(n)] for i in range(n)]
        JTr = [sum(J[k][i]*r[k] for k in range(len(r))) for i in range(n)]
        dp = _solve_linear(JTJ, [-x for x in JTr])
        if dp is None:
            break
        params = [params[i] + dp[i] for i in range(n)]
        if clamp:
            params = clamp(params)
        if max(abs(x) for x in dp) < tol:
            break
    return params, _ssr(residual_fn(params))


def _jacobian(fn, p, r0, h=1e-6):
    J = [[0.0]*len(p) for _ in range(len(r0))]
    for i in range(len(p)):
        pp = list(p)
        pp[i] += h
        rp = fn(pp)
        for k in range(len(rp)):
            J[k][i] = (rp[k] - r0[k]) / h
    return J


def _solve_linear(A, b):
    """Gauss elimination on n×n with partial pivoting."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for i in range(n):
        piv = max(range(i, n), key=lambda r: abs(M[r][i]))
        M[i], M[piv] = M[piv], M[i]
        if abs(M[i][i]) < 1e-14:
            return None
        for j in range(i+1, n):
            f = M[j][i] / M[i][i]
            for k in range(i, n+1):
                M[j][k] -= f * M[i][k]
    x = [0.0] * n
    for i in range(n-1, -1, -1):
        s = M[i][n] - sum(M[i][j]*x[j] for j in range(i+1, n))
        x[i] = s / M[i][i]
    return x


def _ssr(residuals):
    return sum(r*r for r in residuals)


# ----- first-order: y(t) = A·(1 - exp(-t/τ)) + b -------------------

def fit_first_order(t, y):
    A0 = y[-1] - y[0]
    b0 = y[0]
    tau0 = max((t[-1] - t[0]) / 5.0, 1e-6)

    def resid(p):
        A, tau, b = p
        if tau <= 0:
            tau = 1e-9
        return [A*(1 - math.exp(-t[i]/tau)) + b - y[i]
                for i in range(len(t))]

    params, ssr = _gauss_newton(resid, [A0, tau0, b0])
    A, tau, b = params
    ymean = sum(y)/len(y)
    sst = sum((v - ymean)**2 for v in y)
    r2 = 1.0 - ssr/sst if sst > 0 else 1.0
    return {"A": A, "tau": tau, "b": b, "r2": r2, "ssr": ssr}


# ----- second-order: underdamped step response ---------------------
# y(t) = A·(1 - exp(-ζωn t)·(cos(ωd t) + (ζ/√(1-ζ²))sin(ωd t))) + b
# ωd = ωn √(1-ζ²)

def fit_second_order(t, y):
    A0 = y[-1] - y[0]
    b0 = y[0]
    # Better wn initial guess: for an underdamped step response,
    # the GLOBAL maximum is the first overshoot peak (subsequent
    # oscillations decay). t_peak ≈ π/ωd ≈ π/ωn for small ζ.
    # First-local-max-above-threshold gets fooled by noise wiggles
    # on the rising edge -- argmax doesn't.
    asymptote = b0 + A0
    i_peak = max(range(len(y)), key=lambda i: y[i])
    t_peak = t[i_peak]
    if y[i_peak] > asymptote + 0.05*abs(A0) and t_peak > 0:
        wn0 = math.pi / t_peak
    else:
        # no significant overshoot -> half-rise heuristic
        half = b0 + 0.5*A0
        i_half = next((i for i, v in enumerate(y) if v >= half),
                      len(t)//4)
        t_half = t[i_half] if i_half < len(t) else (t[-1]/2)
        wn0 = 1.7 / max(t_half, 1e-6)
    # ζ from observed overshoot ratio
    peak = max(y)
    overshoot = (peak - asymptote)/A0 if A0 > 0 else 0.0
    if overshoot > 0:
        z0 = max(0.05, -math.log(overshoot) /
                 math.sqrt(math.pi**2 + math.log(overshoot)**2))
    else:
        z0 = 0.7

    def resid(p):
        A, wn, zeta, b = p
        wd = wn*math.sqrt(1 - zeta**2)
        out = []
        for i in range(len(t)):
            tt = t[i]
            envelope = math.exp(-zeta*wn*tt)
            osc = (math.cos(wd*tt) +
                   (zeta/math.sqrt(1-zeta**2))*math.sin(wd*tt))
            out.append(A*(1 - envelope*osc) + b - y[i])
        return out

    def clamp(p):
        A, wn, zeta, b = p
        if wn <= 1e-6:
            wn = 1e-6
        if zeta <= 0.01:
            zeta = 0.01
        if zeta >= 0.99:
            zeta = 0.99
        return [A, wn, zeta, b]

    params, ssr = _gauss_newton(resid, [A0, wn0, z0, b0], clamp=clamp)
    A, wn, zeta, b = params
    ymean = sum(y)/len(y)
    sst = sum((v - ymean)**2 for v in y)
    r2 = 1.0 - ssr/sst if sst > 0 else 1.0
    return {"A": A, "wn": wn, "zeta": zeta, "b": b, "r2": r2, "ssr": ssr}
