#!/usr/bin/env python3
"""
Autonomous Scientific Cognition Framework (ASCF) - Minimal Prototype
Discovers hidden physics (altitude-dependent gravity) through self-experimentation.

CC0 - No rights reserved.

READ THIS BEFORE QUOTING THE OUTPUT
-----------------------------------
This file is the prototype as drafted, with three instrumented honesty
checks added and nothing removed. It runs, and its headline claim -- "the
AI autonomously discovers the hidden variable" -- is weaker than it looks.
`audit.md` in this folder has the measurements. In short:

1. The hidden-variable search has exactly one candidate, `g_of_h`, and that
   candidate is the true generative model. The system is not searching a
   hypothesis space; it is being handed the answer and checking it. That is
   a real and useful capability -- model comparison by Bayes factor -- but
   it is not discovery, and `hvs_search` now says so in its docstring.
2. `structural_health` returned a hardcoded `alpha = 2.5`, so every run
   printed "Health: alpha=2.50 (OK)" regardless of state. That is the same
   defect class the AISS catalogue exists to catch, sitting inside the
   monitor meant to catch it. It is now computed, and returns None where it
   cannot be computed.
3. Anomaly detection fires at a rate set by the threshold rule, not by the
   data. See `audit.md` for the null-model test.

None of this makes the loop worthless. It makes it a *model-comparison*
loop rather than a *discovery* loop, and the distinction matters for what
can be claimed from it.
"""

import warnings

import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import genpareto

warnings.filterwarnings("ignore")

# ------------------------------------------------------------
# 1. Simulated World with Hidden Variable
# ------------------------------------------------------------
TRUE_GRAVITY_AT_SEA = 9.81
GRAVITY_GRADIENT = -0.003  # per meter of altitude (hidden)


def true_physics(theta_deg, v0, rng=None):
    """
    True world: range of a projectile on flat ground, where gravity varies
    with max altitude: g(h) = g0 + gradient * h_max. This introduces a
    small non-linearity, making the constant-g model wrong at high angles.
    """
    rng = rng or np.random
    theta = np.radians(theta_deg)
    g0 = TRUE_GRAVITY_AT_SEA
    v0y = v0 * np.sin(theta)
    h_max = (v0y ** 2) / (2 * g0)
    g_eff = g0 + GRAVITY_GRADIENT * h_max
    range_val = (v0 ** 2) * np.sin(2 * theta) / g_eff
    noise = rng.normal(0, 0.05 * range_val)
    return max(0, range_val + noise)


# ------------------------------------------------------------
# 2. Predictive Model (Claim)
# ------------------------------------------------------------
class PredictiveModel:
    """A claim about how range depends on launch angle and speed."""

    def __init__(self, name="constant_g"):
        self.name = name
        self.params = None
        self.n_samples_used = 0

    def predict(self, theta, v0):
        if self.params is None:
            return np.zeros_like(np.asarray(theta, dtype=float))
        if self.name == "constant_g":
            g = self.params[0]
            return (v0 ** 2) * np.sin(np.radians(2 * theta)) / g
        if self.name == "g_of_h":
            g0, grad = self.params
            v0y = v0 * np.sin(np.radians(theta))
            h_max = (v0y ** 2) / (2 * g0)
            g_eff = g0 + grad * h_max
            return (v0 ** 2) * np.sin(np.radians(2 * theta)) / g_eff
        raise ValueError(f"unknown model {self.name}")

    def fit(self, X, y):
        theta_arr, v0_arr = X[:, 0], X[:, 1]
        self.n_samples_used = len(y)
        if self.name == "constant_g":
            valid = y > 1e-3
            if not np.any(valid):
                return
            g_est = np.median(
                (v0_arr[valid] ** 2 * np.sin(np.radians(2 * theta_arr[valid])))
                / y[valid]
            )
            self.params = np.array([g_est])
        elif self.name == "g_of_h":
            def model(X, g0, grad):
                th, v = X[:, 0], X[:, 1]
                v0y = v * np.sin(np.radians(th))
                h_max = (v0y ** 2) / (2 * g0)
                return (v ** 2) * np.sin(np.radians(2 * th)) / (g0 + grad * h_max)

            popt, _ = curve_fit(model, X, y, p0=[9.8, 0.0], maxfev=5000)
            self.params = popt

    def description_length(self):
        n = max(10, self.n_samples_used)
        k = len(self.params) if self.params is not None else 1
        return k * np.log(n)


# ------------------------------------------------------------
# 3. Knowledge Base (Ensemble)
# ------------------------------------------------------------
class KnowledgeBase:
    def __init__(self):
        self.models = []
        self.weights = []

    def add_model(self, model, weight=0.1):
        self.models.append(model)
        self.weights.append(weight)
        total = sum(self.weights)
        self.weights = [w / total for w in self.weights]

    def predict_ensemble(self, theta, v0):
        preds = np.array([m.predict(theta, v0) for m in self.models], dtype=float)
        return (float(np.average(preds, weights=np.array(self.weights))),
                float(np.std(preds)))

    def best_model(self):
        idx = int(np.argmax(self.weights))
        return self.models[idx], self.weights[idx]

    def update_weights(self, data_X, data_y):
        sigma = max(np.std(data_y) * 0.5, 1e-6)
        log_liks = []
        for m in self.models:
            pred = m.predict(data_X[:, 0], data_X[:, 1])
            log_liks.append(-0.5 * np.sum(((data_y - pred) / sigma) ** 2))
        # Normalise in log space; the original exponentiated first, which
        # underflows to all-zeros within ~20 samples and silently reset the
        # ensemble to a uniform prior on every step after that.
        log_liks = np.array(log_liks)
        log_post = np.log(np.array(self.weights) + 1e-300) + log_liks
        log_post -= log_post.max()
        post = np.exp(log_post)
        self.weights = list(post / post.sum())


# ------------------------------------------------------------
# 4. Anomaly Detector with EVT
# ------------------------------------------------------------
class AnomalyDetector:
    def __init__(self, tail_frac=0.1):
        self.buffer = []
        self.tau = 5.0
        self.tail_frac = tail_frac

    def is_anomaly(self, log_prob):
        surprise = -log_prob
        self.buffer.append(surprise)
        if len(self.buffer) > 1000:
            self.buffer = self.buffer[-500:]
        if len(self.buffer) > 50:
            tail_thresh = np.quantile(self.buffer, 1 - self.tail_frac)
            exceed = [s - tail_thresh for s in self.buffer if s > tail_thresh]
            if len(exceed) > 5:
                try:
                    shape, loc, scale = genpareto.fit(exceed, floc=0)
                    self.tau = genpareto.isf(1 / 50, shape, loc=0,
                                             scale=scale) + tail_thresh
                except Exception:
                    pass
        return surprise > self.tau


# ------------------------------------------------------------
# 5. Hidden Variable Search (HVS)
# ------------------------------------------------------------
def hvs_search(current_model, data_history):
    """Compare the current model against ONE hardcoded alternative.

    NOT a hidden-variable search in the ASCF sense. The candidate `g_of_h`
    is the true generative model of `true_physics`, supplied by the author.
    There is no candidate library, no structural mutation, and no search:
    the routine fits one named alternative and accepts it on a Bayes factor.

    What this genuinely demonstrates: Bayesian model comparison with an MDL
    penalty correctly prefers the richer model once the data supports it,
    and correctly refuses it before that. What it does not demonstrate:
    autonomous discovery. Reporting the accepted model as "discovered"
    overstates it by the size of the hypothesis space, which here is one.
    """
    X_hist, y_hist = data_history
    if current_model.name != "constant_g":
        return None
    if len(y_hist) < 4:
        return None

    candidate = PredictiveModel(name="g_of_h")
    try:
        candidate.fit(X_hist, y_hist)
    except Exception:
        return None

    theta_arr, v0_arr = X_hist[:, 0], X_hist[:, 1]
    rss_old = np.sum((y_hist - current_model.predict(theta_arr, v0_arr)) ** 2)
    rss_new = np.sum((y_hist - candidate.predict(theta_arr, v0_arr)) ** 2)
    if rss_new <= 0 or rss_old <= 0:
        return None

    n = len(y_hist)
    log_bf = ((n / 2) * np.log(rss_old / rss_new)
              - (len(candidate.params) - len(current_model.params)) * np.log(n))
    return candidate if log_bf > np.log(10) else None


# ------------------------------------------------------------
# 6. Exploration Policy
# ------------------------------------------------------------
class ExplorationPolicy:
    def __init__(self, angle_range=(10, 80), speed_range=(5, 20), seed=0):
        self.angles = np.linspace(*angle_range, 8)
        self.speeds = np.linspace(*speed_range, 5)
        self.visited = set()
        self.rng = np.random.default_rng(seed)

    def choose_experiment(self, knowledge_base=None):
        """Grid sweep, then random. Note: this ignores knowledge_base entirely.

        The ASCF spec defines V(E) = EIG + lambda*Novelty - gamma*ERV. None
        of those three terms is computed here; the policy is a fixed sweep
        and the argument is accepted only to match the intended signature.
        Do not describe runs of this file as demonstrating an
        information-gain exploration policy.
        """
        for angle in self.angles:
            for speed in self.speeds:
                if (angle, speed) not in self.visited:
                    self.visited.add((angle, speed))
                    return angle, speed
        return (float(self.rng.uniform(20, 70)), float(self.rng.uniform(8, 18)))


# ------------------------------------------------------------
# 7. Structural Monitor
# ------------------------------------------------------------
def structural_health(knowledge_base, test_points=None):
    """Diversity check over the ensemble's predictions.

    The original returned a hardcoded `alpha = 2.5` and reported it as a
    measured power-law exponent, so every run printed a healthy score
    regardless of the ensemble's actual state. A monitor that cannot fail
    is not a monitor -- it is the D5 "false success metric" defect from the
    AISS catalogue, inside the module meant to detect it.

    `alpha` is now `None`: fitting a power law needs a reasoning graph this
    prototype does not build, and reporting None is the honest answer.
    `beta` is a real measurement -- the coefficient of variation of ensemble
    predictions across test inputs -- and it can fail.
    """
    if len(knowledge_base.models) < 2:
        return {"alpha": None, "beta": None, "healthy": None,
                "why": "single-model ensemble: no diversity to measure"}

    if test_points is None:
        test_points = [(a, s) for a in (30.0, 45.0, 60.0) for s in (10.0, 15.0)]

    spreads = []
    for theta, v0 in test_points:
        preds = np.array([m.predict(theta, v0) for m in knowledge_base.models],
                         dtype=float)
        mean = np.mean(np.abs(preds))
        if mean > 1e-9:
            spreads.append(float(np.std(preds) / mean))
    if not spreads:
        return {"alpha": None, "beta": None, "healthy": None,
                "why": "predictions degenerate"}

    beta = float(np.mean(spreads))
    healthy = beta > 1e-3
    return {"alpha": None, "beta": beta, "healthy": healthy,
            "why": "alpha needs a reasoning graph this prototype does not build"}


# ------------------------------------------------------------
# 8. Main Autonomous Loop
# ------------------------------------------------------------
def main(steps=30, seed=42, verbose=True):
    rng = np.random.default_rng(seed)
    kb = KnowledgeBase()
    init = PredictiveModel(name="constant_g")
    init.params = np.array([9.8])
    kb.add_model(init, weight=1.0)

    detector = AnomalyDetector()
    explorer = ExplorationPolicy(seed=seed)
    history_X = np.empty((0, 2))
    history_y = np.empty(0)
    anomalies = 0
    accepted_step = None

    if verbose:
        print("=== ASCF Autonomous Discovery Loop ===\n")

    for step in range(steps):
        theta, v0 = explorer.choose_experiment(kb)
        actual = true_physics(theta, v0, rng=rng)

        mean, spread = kb.predict_ensemble(theta, v0)
        sigma = max(spread, 0.1)
        log_prob = (-0.5 * ((actual - mean) / sigma) ** 2
                    - np.log(sigma * np.sqrt(2 * np.pi)))

        history_X = np.vstack([history_X, [[theta, v0]]])
        history_y = np.append(history_y, actual)

        for m in kb.models:
            m.fit(history_X, history_y)
        kb.update_weights(history_X, history_y)

        anomaly = detector.is_anomaly(log_prob)
        best, _ = kb.best_model()

        if verbose:
            print(f"Step {step + 1:2d} | th={theta:4.1f} v0={v0:4.1f} | "
                  f"range {actual:5.2f} (pred {mean:5.2f}+-{sigma:4.2f}) | "
                  f"surprise {-log_prob:5.2f} | tau {detector.tau:5.2f} | "
                  f"{best.name}")

        if anomaly:
            anomalies += 1
            new_model = hvs_search(best, (history_X, history_y))
            if new_model is not None and not any(
                    m.name == "g_of_h" for m in kb.models):
                kb.add_model(new_model, weight=0.3)
                accepted_step = step + 1
                if verbose:
                    print(f"        ANOMALY -> accepted g_of_h "
                          f"{np.round(new_model.params, 4)} "
                          f"(one candidate, supplied not discovered)")

        health = structural_health(kb)
        if verbose and health["beta"] is not None:
            print(f"        diversity beta={health['beta']:.4f} "
                  f"healthy={health['healthy']}  alpha={health['alpha']}")

    best_final, w_final = kb.best_model()
    if verbose:
        print("\n=== Run complete ===")
        print(f"Best model: {best_final.name} (weight {w_final:.3f})")
        print(f"Anomalies: {anomalies}/{steps}   "
              f"g_of_h accepted at step: {accepted_step}")
        if best_final.name == "g_of_h":
            g0, grad = best_final.params
            print(f"  g0       = {g0:.4f}   (true {TRUE_GRAVITY_AT_SEA})")
            print(f"  gradient = {grad:.5f}   (true {GRAVITY_GRADIENT})")
        else:
            print(f"  constant g = {best_final.params[0]:.4f}")

    return {"best": best_final.name, "params": best_final.params,
            "anomalies": anomalies, "accepted_step": accepted_step,
            "steps": steps}


if __name__ == "__main__":
    main()
