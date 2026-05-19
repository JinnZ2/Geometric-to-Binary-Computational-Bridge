"""
constraint_gate.py  (fabrication/voice/)

energy_english constraint gate. Lightweight in-tree subset of
the constraints documented at
github.com/JinnZ2/JinnZ2/tree/main/energy_english -- just enough
to refuse noun-first / closure-verb / morality-collapse phrasing
before the bridge dispatcher sees the request.

Rules applied in order:

  R1  reject closure verbs ("fix", "solve", "finish") without an
      explicit constraint (until / below / above / within / ...)
  R2  reject morality verbs ("should", "must", "ought") applied
      to system behavior -> ask for observable
  R3  reject identity collapse ("X is a Y") unless paired with a
      conditional ("under", "when", "at", "if", "given") that
      turns identity into observable behavior
  R4  require at least one substrate or coupler token
  R5  require a physics-grade verb to route on

Returns:
  {"accepted": True,  "verb": ..., "substrate": ..., "coupler": ...,
   "tokens": [...]}
  {"accepted": False, "rule": <code>, "suggestion": <str>}

License: CC0. Stdlib only.
"""
import re


SUBSTRATES = {"acoustic", "fluidic", "electrical", "mechanical",
              "thermal", "magnetic"}
COUPLERS   = {"piezo", "speaker", "heater", "transformer",
              "friction", "solenoid"}
PHYSICS_VERBS = {"measure", "predict", "emit", "verify", "compare",
                 "drive", "release", "log", "sweep", "capture",
                 "baseline", "list", "show", "summary",
                 "build", "lower", "fit", "extract", "regress"}

CLOSURE_VERBS   = {"fix", "solve", "finish", "complete", "perfect"}
MORALITY_VERBS  = {"should", "must", "ought", "deserves"}
IDENTITY_TOKENS = ("is a", "are a", "is the", "are the")
CONDITIONAL_WORDS = {"under", "when", "at", "if", "given"}


def gate(utterance):
    text = utterance.strip().lower()
    if not text:
        return {"accepted": False, "rule": "R0_empty",
                "suggestion": "say what you want to measure or build"}

    tokens = re.findall(r"[a-z0-9_]+", text)
    tset = set(tokens)

    # R1: closure verbs without explicit constraint
    for v in CLOSURE_VERBS:
        if v in tset and not any(w in tset for w in
                                 ("until", "below", "above",
                                  "within", "while", "during")):
            return {"accepted": False, "rule": "R1_closure",
                    "suggestion": (f"replace '{v}' with what RATE you "
                                   "want to change. e.g. 'measure τ "
                                   f"until 5τ' instead of '{v} the τ "
                                   "test'")}

    # R2: morality verbs on system behavior
    for v in MORALITY_VERBS:
        if v in tset:
            return {"accepted": False, "rule": "R2_morality",
                    "suggestion": (f"replace '{v}' with an observable. "
                                   "e.g. 'expect ΔT < 5 K' instead of "
                                   f"'{v} have ΔT < 5 K'")}

    # R3: identity collapse -- only fire if no conditional follows
    for phrase in IDENTITY_TOKENS:
        if phrase in text:
            tail = text.split(phrase, 1)[1]
            window = tail.split()[:6]
            if not any(c in window for c in CONDITIONAL_WORDS):
                return {"accepted": False, "rule": "R3_identity",
                        "suggestion": (f"replace '{phrase}' with "
                                       "'behaves as X under Y' -- what "
                                       "condition makes the behavior "
                                       "visible?")}

    # R4: require substrate or coupler token
    substrate = next((s for s in SUBSTRATES if s in tset), None)
    coupler   = next((c for c in COUPLERS   if c in tset), None)
    if not substrate and not coupler:
        return {"accepted": False, "rule": "R4_no_substrate",
                "suggestion": ("name a substrate ("
                               + ", ".join(sorted(SUBSTRATES))
                               + ") or coupler ("
                               + ", ".join(sorted(COUPLERS)) + ")")}

    # R5: require a physics verb to route on
    verb = next((v for v in PHYSICS_VERBS if v in tset), None)
    if verb is None:
        return {"accepted": False, "rule": "R5_no_verb",
                "suggestion": ("name a physics verb ("
                               + ", ".join(sorted(PHYSICS_VERBS))
                               + ")")}

    return {
        "accepted":  True,
        "verb":      verb,
        "substrate": substrate,
        "coupler":   coupler,
        "tokens":    tokens,
    }
