"""Planted-semantics test of code-path -> predicate assignment. Co-authored. CC0.

SYNTHETIC ONLY. The "concepts" are draws from the generator declared below and
the "embeddings" are constructed vectors. Nothing here was measured on a neural
model, and no number here is a finding about an NCM checkpoint or about Lojban.
What it tests is the assignment METHOD: given a truth that was planted, does
majority assignment on a train split recover it on a held-out split, against
its nulls, and does it say so when it cannot.

Targets RESEARCH_GAPS.md "Semantic assignment" (NOT_STUDIED). That gap asks for
an identified checkpoint; this does not supply one, and the gap's state is not
changed by this file.

  python -m experiments.experiment_bridge.sim.planted --output-dir NEW_DIR
  python -m experiments.experiment_bridge.sim.planted --small --output-dir NEW_DIR
  python -m experiments.experiment_bridge.sim.planted --selftest

Stdlib only; Python 3.10. Every random draw comes from a seed recorded in the
results. The run writes only into the directory it is given, which must be new
or empty.

1 GROUND TRUTH (declared generator)
    concept     one predicate of the reference + one filler for each of two slots
    predicates  PREDICATES below: rows of raw/lojban_wordslot_reference.json
                whose structure is OBSERVED there. The file is read, never
                written, and its sha256 is checked against raw/manifest.json.
    void class  VOID_WORD ("efficient"): a row the reference marks VOID (no
                Lojban word). It gets a signature like any class; a code path
                assigned to it is a LEXICAL_VOID, not a predicate.
    embedding   D = 12 coordinates
                  0..5   predicate signature: a seeded Gaussian direction,
                         length PRED_AMP
                  6..8   slot x1 filler, one-hot x SLOT1_AMP
                  9..11  slot x2 filler, one-hot x SLOT2_AMP
                  + Gaussian noise, standard deviation sigma, on every coordinate
    The amplitudes are a design choice: predicate > slot x1 > slot x2. A
    different choice gives a different level structure; see LIMITS.

2 ENCODE  the v1.1 kernel (v1_1/core.py: make_level, calibrate_thresholds,
    walk, validate_trace), 4 levels x 16 codes. v1.1 has no trainer, so the
    codebooks are trained here by k-means on the train split (residuals
    ungated, as in the received toy); thresholds by v1.1's gated calibration
    at REJECT_FRACTION, on train only.

3 ASSIGN  train only. Key = the first DEPTH codes of a sample's path
    (PRIMARY_DEPTH is declared before any run; the other depths are reported
    beside it). Rule = majority label among train samples on that key; ties
    go to the label that sorts first.

8 STATES, one per held-out sample, in this order
    REJECTED      the kernel rejected the sample at a level inside the key
    UNMAPPED      its key was never seen in train
    LEXICAL_VOID  its key is assigned to the void class
    ACCEPTED      its key is assigned to a predicate
  REJECTED and UNMAPPED are abstentions. "strict" accuracy counts them wrong;
  "covered" accuracy leaves them out. The falsifier uses strict.

4 BASELINES
    permuted labels   train labels shuffled, assignment redone, held-out
                      scored against the true labels; N_PERMUTATIONS times
    majority label    one answer for every sample: what a code with no
                      information would give
    random codebook   untrained Gaussian codebooks, same kernel and rule. A
                      partition of any kind can carry signal, so this is a
                      comparison, not a null.

5 SLOTS  per level: mutual information (bits) between that level's code and
    the predicate, and between it and each slot filler, on held-out, beside
    the mean and maximum of the same quantity under shuffles (finite-sample
    bias). A target counts as carried by a level only when its MI is above
    every shuffle; holds_most is null when none is.

6 PLANTED FAULT  FAULT_TWIN = (a, b): b is generated with a's signature. The
    two cannot be told apart from the embedding. A key is CONFUSED when the
    runner-up label holds at least CONFUSED_SHARE of its train samples; a
    pair is confused when CONFUSED keys naming both hold at least half of the
    pair's train samples. A control run without the fault is made beside it.

7 SWEEP  sigma over SIGMAS. "beats the null" = strict accuracy above every
    permuted-label accuracy.

FALSIFIER  at the lowest sigma the assignment does not beat the permuted null
    -> verdict METHOD_FAILS. --selftest shows that this verdict can fire (an
    assigner fed shuffled labels) and that the fault reads as confused.

LIMITS
    The generator was written by the same hands as the test, so success shows
    the method can recover a structure of this declared kind, not that real
    embeddings have it. The level-versus-slot reading follows from the chosen
    amplitudes. One master seed per run; the committed run is one seed.
"""
import argparse
import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path

from ..v1_1.core import calibrate_thresholds, make_level, validate_trace, walk

SIM_VERSION = "experiment-bridge/sim-planted-1"
BENCH = Path(__file__).resolve().parents[1]
REFERENCE = BENCH / "raw" / "lojban_wordslot_reference.json"
MANIFEST = BENCH / "raw" / "manifest.json"

PREDICATES = ("snura", "jibni", "zmadu", "mleca", "xamgu", "glare", "ckape", "mapti")
VOID_WORD = "efficient"
VOID_LABEL = "VOID:" + VOID_WORD
FAULT_TWIN = ("zmadu", "mleca")           # mleca is generated with zmadu's signature
FILLERS = 3
PRED_DIMS, D = 6, 12
PRED_AMP, SLOT1_AMP, SLOT2_AMP = 4.0, 1.5, 0.75
LEVELS, CODES = 4, 16
KMEANS_ITERS = 12
REJECT_FRACTION = 0.02
PRIMARY_DEPTH = 1
CONFUSED_SHARE = 0.25
N_PERMUTATIONS = 100
MI_SHUFFLES = 20
SIGMAS = (0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
N_TRAIN, N_HELD = 600, 300
SMALL = {"n_train": 240, "n_held": 120, "sigmas": (0.1, 1.0, 8.0)}
STATES = ("ACCEPTED", "REJECTED", "UNMAPPED", "LEXICAL_VOID")
VALIDATED_TRACES = 10                     # traces re-checked by validate_trace per encode


def sha(obj):
    data = json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("ascii")).hexdigest()


def rng(seed, purpose, *more):
    """One generator per purpose, derived from the master seed and recorded."""
    return random.Random(f"{seed}|{purpose}|" + "|".join(str(m) for m in more))


# ---------------------------------------------------------------- reference

def read_reference():
    """The reference, read only. Raises ValueError if it is not the received
    file or does not hold the rows the generator declares."""
    raw = REFERENCE.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    listed = [f["sha256"] for f in json.loads(MANIFEST.read_text())["files"]
              if f["path"] == "raw/lojban_wordslot_reference.json"]
    if listed != [digest]:
        raise ValueError("the reference is not the file raw/manifest.json records")
    rows = json.loads(raw)["place_structures"]
    observed = {r["gismu"] for r in rows if r["structure_status"] == "OBSERVED"}
    missing = [p for p in PREDICATES if p not in observed]
    if missing:
        raise ValueError(f"not OBSERVED predicates of the reference: {missing}")
    void = [r for r in rows if r["english"] == VOID_WORD]
    if len(void) != 1 or void[0]["structure_status"] != "VOID" or void[0]["gismu"] is not None:
        raise ValueError(f"{VOID_WORD!r} is not a VOID row of the reference")
    return {"path": "raw/lojban_wordslot_reference.json", "sha256": digest,
            "predicates": list(PREDICATES), "void_word": VOID_WORD}


# ---------------------------------------------------------------- generator

def signatures(seed, fault):
    """{label: predicate signature}. With the fault, the twin shares one."""
    out = {}
    for label in PREDICATES + (VOID_LABEL,):
        g = rng(seed, "signature", label)
        v = [g.gauss(0, 1) for _ in range(PRED_DIMS)]
        norm = math.sqrt(sum(x * x for x in v))
        out[label] = [PRED_AMP * x / norm for x in v]
    if fault:
        out[FAULT_TWIN[1]] = list(out[FAULT_TWIN[0]])
    return out


def truth_table(seed, n_train, n_held):
    """The planted concepts. Independent of sigma and of the fault."""
    g = rng(seed, "concepts")
    labels = PREDICATES + (VOID_LABEL,)
    rows = []
    for i in range(n_train + n_held):
        rows.append({"id": i, "split": "train" if i < n_train else "held_out",
                     "label": labels[g.randrange(len(labels))],
                     "x1": g.randrange(FILLERS), "x2": g.randrange(FILLERS)})
    return rows


def embed(rows, sigs, sigma, seed):
    g = rng(seed, "noise", sigma)
    out = []
    for r in rows:
        v = list(sigs[r["label"]]) + [0.0] * (D - PRED_DIMS)
        v[PRED_DIMS + r["x1"]] = SLOT1_AMP
        v[PRED_DIMS + FILLERS + r["x2"]] = SLOT2_AMP
        out.append([x + g.gauss(0, sigma) for x in v])
    return out


# ---------------------------------------------------------------- codebooks

def _d2(a, b):
    return sum((x - y) * (x - y) for x, y in zip(a, b))


def _nearest(v, book):
    best, at = None, 0
    for i, c in enumerate(book):
        d = _d2(v, c)
        if best is None or d < best:
            best, at = d, i
    return at


def kmeans(data, k, g):
    centres = [list(data[i]) for i in g.sample(range(len(data)), k)]
    for _ in range(KMEANS_ITERS):
        sums = [[0.0] * len(data[0]) for _ in range(k)]
        counts = [0] * k
        for v in data:
            i = _nearest(v, centres)
            counts[i] += 1
            s = sums[i]
            for j, x in enumerate(v):
                s[j] += x
        for i in range(k):
            if counts[i]:                         # an empty cell keeps its centre
                centres[i] = [x / counts[i] for x in sums[i]]
    return centres


def trained_books(train, seed, sigma):
    books, residual = [], [list(v) for v in train]
    for level in range(LEVELS):
        book = kmeans(residual, CODES, rng(seed, "kmeans", sigma, level))
        books.append(book)
        residual = [[x - y for x, y in zip(v, book[_nearest(v, book)])] for v in residual]
    return books


def random_books(train, seed, sigma):
    """Untrained: Gaussian codes at the scale of the residual they will meet."""
    books, residual = [], [list(v) for v in train]
    for level in range(LEVELS):
        g = rng(seed, "random-codebook", sigma, level)
        scale = math.sqrt(sum(x * x for v in residual for x in v) / (len(residual) * D))
        book = [[g.gauss(0, scale) for _ in range(D)] for _ in range(CODES)]
        books.append(book)
        residual = [[x - y for x, y in zip(v, book[_nearest(v, book)])] for v in residual]
    return books


def encode(vectors, train, books):
    """Code paths from the v1.1 kernel. A rejected level is None."""
    thresholds = calibrate_thresholds(train, books, REJECT_FRACTION, gated=True)
    levels = [make_level(b, t, label="SYNTHETIC planted-semantics sim")
              for b, t in zip(books, thresholds)]
    paths, checked = [], 0
    for i, v in enumerate(vectors):
        trace = walk(v, levels)
        if i < VALIDATED_TRACES:
            errors = validate_trace(trace, levels)
            if errors:
                raise ValueError(f"v1.1 trace validation failed: {errors[0]}")
            checked += 1
        paths.append(tuple(s["code_index"] for s in trace["steps"]))
    return paths, {"thresholds_squared": list(thresholds), "traces_validated": checked,
                   "codebook_sha256": [lv.codebook_sha256 for lv in levels]}


# ---------------------------------------------------------------- assignment

def assign(paths, labels, depth):
    """Majority rule on train. Returns {key: {label, count, share, runner_up,
    runner_up_share, quality}}. Keys holding a rejection are not assigned."""
    cells = {}
    for p, lab in zip(paths, labels):
        key = p[:depth]
        if None not in key:
            cells.setdefault(key, Counter())[lab] += 1
    out = {}
    for key, c in cells.items():
        ranked = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
        n = sum(c.values())
        second = ranked[1] if len(ranked) > 1 else (None, 0)
        out[key] = {"label": ranked[0][0], "count": n, "share": ranked[0][1] / n,
                    "runner_up": second[0], "runner_up_share": second[1] / n,
                    "quality": "CONFUSED" if second[1] / n >= CONFUSED_SHARE else "CLEAN"}
    return out


def read_out(paths, mapping, depth):
    """One (state, assigned label or None, key quality or None) per sample."""
    out = []
    for p in paths:
        key = p[:depth]
        if None in key:
            out.append(("REJECTED", None, None))
        elif key not in mapping:
            out.append(("UNMAPPED", None, None))
        else:
            m = mapping[key]
            out.append(("LEXICAL_VOID" if m["label"] == VOID_LABEL else "ACCEPTED",
                        m["label"], m["quality"]))
    return out


def score(reads, labels):
    n = len(reads)
    covered = [(r, lab) for r, lab in zip(reads, labels) if r[1] is not None]
    right = sum(1 for r, lab in covered if r[1] == lab)
    return {"n": n, "strict_accuracy": right / n,
            "covered_accuracy": right / len(covered) if covered else None,
            "coverage": len(covered) / n,
            "states": {s: sum(1 for r in reads if r[0] == s) for s in STATES}}


def strict(train_paths, train_labels, held_paths, held_labels, depth):
    reads = read_out(held_paths, assign(train_paths, train_labels, depth), depth)
    return sum(1 for r, lab in zip(reads, held_labels) if r[1] == lab) / len(reads)


def permuted_null(train_paths, train_labels, held_paths, held_labels, depth, g, n):
    out = []
    for _ in range(n):
        shuffled = list(train_labels)
        g.shuffle(shuffled)
        out.append(strict(train_paths, shuffled, held_paths, held_labels, depth))
    return out


def confused_pairs(mapping, train_labels):
    """Label pairs whose CONFUSED keys hold at least half of the pair's train samples."""
    held, total = Counter(), Counter(train_labels)
    for m in mapping.values():
        if m["quality"] == "CONFUSED":
            pair = tuple(sorted((m["label"], m["runner_up"])))
            held[pair] += round((m["share"] + m["runner_up_share"]) * m["count"])
    return [{"pair": list(p), "train_samples_on_confused_keys": k,
             "train_samples_of_pair": total[p[0]] + total[p[1]]}
            for p, k in sorted(held.items()) if 2 * k >= total[p[0]] + total[p[1]]]


def per_label(reads, labels):
    out = {}
    for lab in sorted(set(labels)):
        mine = [r for r, t in zip(reads, labels) if t == lab]
        got = Counter(r[1] if r[1] is not None else r[0] for r in mine)
        out[lab] = {"n": len(mine), "recall_strict": got[lab] / len(mine) if mine else None,
                    "read_as": dict(sorted(got.items()))}
    return out


# ---------------------------------------------------------------- slots

def mutual_information(xs, ys):
    n = len(xs)
    cx, cy, cxy = Counter(xs), Counter(ys), Counter(zip(xs, ys))
    return sum(c / n * math.log2(c * n / (cx[x] * cy[y])) for (x, y), c in cxy.items())


def level_information(paths, rows, g):
    """Per level: MI of that level's code with the predicate and each slot."""
    targets = {"predicate": [r["label"] for r in rows], "slot_x1": [r["x1"] for r in rows],
               "slot_x2": [r["x2"] for r in rows]}
    out = []
    for level in range(LEVELS):
        codes = ["R" if p[level] is None else p[level] for p in paths]
        row = {"level": level + 1}
        for name, ys in targets.items():
            shuffled = []
            for _ in range(MI_SHUFFLES):
                perm = list(ys)
                g.shuffle(perm)
                shuffled.append(mutual_information(codes, perm))
            row[name] = {"mi_bits": mutual_information(codes, ys),
                         "shuffled_mean_bits": sum(shuffled) / len(shuffled),
                         "shuffled_max_bits": max(shuffled)}
        # only a target whose MI is above every shuffle counts as carried
        above = [t for t in targets if row[t]["mi_bits"] > row[t]["shuffled_max_bits"]]
        row["above_shuffle"] = above
        row["holds_most"] = max(above, key=lambda t: row[t]["mi_bits"]
                                - row[t]["shuffled_mean_bits"]) if above else None
        out.append(row)
    return out


# ---------------------------------------------------------------- one cell

def run_sigma(seed, sigma, rows, n_train, fault, label_source=None):
    """One noise level. label_source: None, or "shuffled" for the broken
    assigner of the selftest (the train labels it is given are shuffled)."""
    sigs = signatures(seed, fault)
    vectors = embed(rows, sigs, sigma, seed)
    train, held = vectors[:n_train], vectors[n_train:]
    labels = [r["label"] for r in rows]
    train_labels, held_labels = labels[:n_train], labels[n_train:]
    if label_source == "shuffled":
        train_labels = list(train_labels)
        rng(seed, "broken-assigner", sigma).shuffle(train_labels)
    books = trained_books(train, seed, sigma)
    paths, enc = encode(vectors, train, books)
    tp, hp = paths[:n_train], paths[n_train:]

    depths = {}
    for depth in range(1, LEVELS + 1):
        mapping = assign(tp, train_labels, depth)
        depths[str(depth)] = dict(score(read_out(hp, mapping, depth), held_labels),
                                  keys_assigned=len(mapping))
    mapping = assign(tp, train_labels, PRIMARY_DEPTH)
    reads = read_out(hp, mapping, PRIMARY_DEPTH)
    primary = score(reads, held_labels)
    null = permuted_null(tp, train_labels, hp, held_labels, PRIMARY_DEPTH,
                         rng(seed, "permuted-labels", sigma), N_PERMUTATIONS)
    majority = Counter(train_labels).most_common(1)[0][0]
    rpaths, _ = encode(vectors, train, random_books(train, seed, sigma))
    random_strict = strict(rpaths[:n_train], train_labels, rpaths[n_train:], held_labels,
                           PRIMARY_DEPTH)
    observed = primary["strict_accuracy"]
    cell = {
        "sigma": sigma, "fault": fault, "embeddings_sha256": sha(vectors),
        "encode": enc, "primary_depth": PRIMARY_DEPTH, "primary": primary,
        "by_depth": depths,
        "permuted_null": {"n": len(null), "mean": sum(null) / len(null), "max": max(null),
                          "p_value": (1 + sum(1 for x in null if x >= observed))
                          / (1 + len(null))},
        "beats_permuted_null": observed > max(null),
        "majority_label_baseline": {
            "label": majority,
            "strict_accuracy": sum(1 for t in held_labels if t == majority) / len(held_labels)},
        "random_codebook_baseline": {"strict_accuracy": random_strict},
        "keys": {"CLEAN": sum(1 for m in mapping.values() if m["quality"] == "CLEAN"),
                 "CONFUSED": sum(1 for m in mapping.values() if m["quality"] == "CONFUSED")},
        "confused_pairs": confused_pairs(mapping, train_labels),
        "per_label": per_label(reads, held_labels),
        "level_information": level_information(hp, rows[n_train:],
                                               rng(seed, "mi-shuffles", sigma)),
    }
    samples = [{"id": r["id"], "truth": r["label"], "path": list(p), "state": rd[0],
                "assigned": rd[1], "key_quality": rd[2], "correct": rd[1] == r["label"]}
               for r, p, rd in zip(rows[n_train:], hp, reads)]
    return cell, samples


def verdict(cells):
    """The falsifier, read at the lowest sigma of a sweep."""
    low = min(cells, key=lambda c: c["sigma"])
    fails = not low["beats_permuted_null"]
    stops = [c["sigma"] for c in sorted(cells, key=lambda c: c["sigma"])
             if not c["beats_permuted_null"]]
    return {"falsifier": "strict accuracy at the lowest sigma is not above every "
                         "permuted-label accuracy",
            "lowest_sigma": low["sigma"], "strict_accuracy": low["primary"]["strict_accuracy"],
            "permuted_null_max": low["permuted_null"]["max"],
            "verdict": "METHOD_FAILS" if fails else "NOT_FALSIFIED_ON_THIS_GENERATOR",
            "first_sigma_not_beating_null": stops[0] if stops else None,
            "sigmas_not_beating_null": stops}


# ---------------------------------------------------------------- the run

def run(seed=0, small=False):
    n_train = SMALL["n_train"] if small else N_TRAIN
    n_held = SMALL["n_held"] if small else N_HELD
    sigmas = SMALL["sigmas"] if small else SIGMAS
    reference = read_reference()
    rows = truth_table(seed, n_train, n_held)
    truth = {"generator": SIM_VERSION, "seed": seed, "n_train": n_train, "n_held": n_held,
             "labels": list(PREDICATES) + [VOID_LABEL], "fillers_per_slot": FILLERS,
             "rows": rows}
    faulted, control, states = [], [], {}
    for sigma in sigmas:
        cell, samples = run_sigma(seed, sigma, rows, n_train, fault=True)
        faulted.append(cell)
        states[str(sigma)] = samples
        control.append(run_sigma(seed, sigma, rows, n_train, fault=False)[0])
    results = {
        "version": SIM_VERSION, "scope": "SYNTHETIC ONLY: a planted generator, no neural "
                                         "model, no claim about an NCM checkpoint",
        "status": "PROPOSED", "seed": seed, "small": small,
        "seeds_derived": "random.Random(f'{seed}|{purpose}|...'); purposes: signature, "
                         "concepts, noise, kmeans, random-codebook, permuted-labels, "
                         "mi-shuffles, broken-assigner",
        "parameters": {"predicates": list(PREDICATES), "void_label": VOID_LABEL,
                       "fault_twin": list(FAULT_TWIN), "dimension": D,
                       "amplitudes": {"predicate": PRED_AMP, "slot_x1": SLOT1_AMP,
                                      "slot_x2": SLOT2_AMP},
                       "levels": LEVELS, "codes": CODES, "kmeans_iters": KMEANS_ITERS,
                       "reject_fraction": REJECT_FRACTION, "primary_depth": PRIMARY_DEPTH,
                       "confused_share": CONFUSED_SHARE, "n_permutations": N_PERMUTATIONS,
                       "mi_shuffles": MI_SHUFFLES, "sigmas": list(sigmas),
                       "n_train": n_train, "n_held": n_held},
        "reference": reference, "truth_table_sha256": sha(truth),
        "with_fault": {"cells": faulted, "falsifier": verdict(faulted)},
        "control_without_fault": {"cells": control, "falsifier": verdict(control)},
        "fault_reading": fault_reading(faulted, control),
        "human_interest": None, "ai_interest": None,
    }
    return truth, results, states


def fault_reading(faulted, control):
    """Does the planted twin read as confused, and only where it was planted."""
    twin = sorted(FAULT_TWIN)
    low_f = min(faulted, key=lambda c: c["sigma"])
    low_c = min(control, key=lambda c: c["sigma"])
    in_f = any(p["pair"] == twin for p in low_f["confused_pairs"])
    in_c = any(p["pair"] == twin for p in low_c["confused_pairs"])
    return {"twin": twin, "at_sigma": low_f["sigma"],
            "with_fault_confused_pairs": [p["pair"] for p in low_f["confused_pairs"]],
            "control_confused_pairs": [p["pair"] for p in low_c["confused_pairs"]],
            "twin_recall_with_fault": {t: low_f["per_label"][t]["recall_strict"] for t in twin},
            "twin_recall_control": {t: low_c["per_label"][t]["recall_strict"] for t in twin},
            "reads_as_confused": in_f and not in_c,
            "reading": "CONFUSED where planted, clean in the control" if in_f and not in_c
            else "the twin did not read as confused" if not in_f
            else "the control reads as confused too"}


def write_run(output_dir, truth, results, states):
    out = Path(output_dir)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError("choose a new or empty output directory")
    out.mkdir(parents=True, exist_ok=True)
    for name, payload in (("truth_table.json", truth), ("states.json", states),
                          ("results.json", results)):
        (out / name).write_text(json.dumps(payload, indent=1, ensure_ascii=True,
                                           allow_nan=False) + "\n", encoding="ascii")


def summary_lines(results):
    lines = [f"{results['version']}  seed {results['seed']}  {results['scope']}",
             "sigma   strict  covered coverage  null_max  majority  random_cb  beats  "
             "ACC  REJ  UNM  VOID"]
    for c in results["with_fault"]["cells"]:
        p, s = c["primary"], c["primary"]["states"]
        cov = "   -  " if p["covered_accuracy"] is None else f"{p['covered_accuracy']:.3f} "
        lines.append(
            f"{c['sigma']:<6}  {p['strict_accuracy']:.3f}   {cov}  {p['coverage']:.3f}    "
            f"{c['permuted_null']['max']:.3f}     "
            f"{c['majority_label_baseline']['strict_accuracy']:.3f}     "
            f"{c['random_codebook_baseline']['strict_accuracy']:.3f}     "
            f"{'yes' if c['beats_permuted_null'] else 'NO '}   "
            f"{s['ACCEPTED']:>3}  {s['REJECTED']:>3}  {s['UNMAPPED']:>3}  {s['LEXICAL_VOID']:>3}")
    f = results["with_fault"]["falsifier"]
    lines.append(f"falsifier: {f['verdict']}; first sigma not beating the null: "
                 f"{f['first_sigma_not_beating_null']}")
    lines.append(f"planted twin {results['fault_reading']['twin']}: "
                 f"{results['fault_reading']['reading']}")
    return lines


def selftest():
    """Planted faults: each check must come out the way it is stated."""
    checks = []
    rows = truth_table(0, SMALL["n_train"], SMALL["n_held"])
    good, _ = run_sigma(0, 0.1, rows, SMALL["n_train"], fault=True)
    ctrl, _ = run_sigma(0, 0.1, rows, SMALL["n_train"], fault=False)
    broken, _ = run_sigma(0, 0.1, rows, SMALL["n_train"], fault=True, label_source="shuffled")
    twin = sorted(FAULT_TWIN)
    checks.append(("the assignment beats the permuted null at low noise",
                   verdict([good])["verdict"] == "NOT_FALSIFIED_ON_THIS_GENERATOR"))
    checks.append(("a broken assigner (shuffled train labels) makes the falsifier fire",
                   verdict([broken])["verdict"] == "METHOD_FAILS"))
    checks.append(("the planted twin reads as confused",
                   any(p["pair"] == twin for p in good["confused_pairs"])))
    checks.append(("without the fault the twin is two clean mappings",
                   not ctrl["confused_pairs"]
                   and all(ctrl["per_label"][t]["recall_strict"] > 0.9 for t in twin)))
    checks.append(("with the fault the twin is not two clean mappings",
                   min(good["per_label"][t]["recall_strict"] for t in twin) < 0.75))
    for name, ok in checks:
        print(("PASS  " if ok else "FAIL  ") + name)
    print(f"checks: {len(checks)}   failed: {sum(1 for _, ok in checks if not ok)}")
    return 0 if all(ok for _, ok in checks) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="planted-semantics test (synthetic only)")
    parser.add_argument("--output-dir", type=Path, help="new or empty directory")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--small", action="store_true", help="fewer samples and sigmas")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.output_dir is None:
        parser.error("--output-dir is required (or --selftest)")
    truth, results, states = run(args.seed, args.small)
    write_run(args.output_dir, truth, results, states)
    print("\n".join(summary_lines(results)))
    print("written ->", args.output_dir)
    return 1 if results["with_fault"]["falsifier"]["verdict"] == "METHOD_FAILS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
