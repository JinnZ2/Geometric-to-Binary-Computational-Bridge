"""dispatcher.py -- v1 symbolic/affinity routing.

LANG_PROFILE[lang][Shape.X] -> [0.0, 1.0] fitness score for runner
`lang` on workload axis X. Dispatcher v1 consults this table to rank
candidate runners for a Problem after tagging it with Shape values.

Stubs (0.5 across the board) are placeholders for languages whose
runners exist but whose profiles haven't been characterized yet.
Tune as benchmarks come in.

See dispatcher_v2_energetic.py for the parallel substrate-as-
potential-well routing.
"""
from __future__ import annotations
from enum import Enum


class Shape(Enum):
    BITWISE       = "bitwise"
    BIGNUM        = "bignum"
    SYMBOLIC      = "symbolic"
    SEARCH        = "search"
    NUMERIC_TIGHT = "numeric_tight"
    RELATIONAL    = "relational"
    PARALLEL      = "parallel"
    METAPROG      = "metaprog"
    IO_BOUND      = "io_bound"


_STUB = {s: 0.5 for s in Shape}


LANG_PROFILE: dict[str, dict[Shape, float]] = {
    # --- baseline stubs (replace with measured profiles) ---
    "python": dict(_STUB),
    "c":      dict(_STUB),
    "rust":   dict(_STUB),
    "sql":    dict(_STUB),
    "bash":   dict(_STUB),

    # --- characterized profiles ---
    "cobol": {
        Shape.BITWISE:       0.40,
        Shape.BIGNUM:        0.50,
        Shape.SYMBOLIC:      0.10,
        Shape.SEARCH:        0.45,
        Shape.NUMERIC_TIGHT: 0.75,    # decades of compiler tuning for batch
        Shape.RELATIONAL:    0.60,
        Shape.PARALLEL:      0.25,
        Shape.METAPROG:      0.10,
        Shape.IO_BOUND:      0.70,
    },
    "lisp": {
        Shape.BITWISE:       0.55,
        Shape.BIGNUM:        0.90,
        Shape.SYMBOLIC:      0.98,    # this is what Lisp IS
        Shape.SEARCH:        0.90,
        Shape.NUMERIC_TIGHT: 0.70,
        Shape.RELATIONAL:    0.75,
        Shape.PARALLEL:      0.50,
        Shape.METAPROG:      0.98,    # code-as-data -- STRENGTH
        Shape.IO_BOUND:      0.50,
    },
    "julia": {
        Shape.BITWISE:       0.75,
        Shape.BIGNUM:        0.80,
        Shape.SYMBOLIC:      0.55,
        Shape.SEARCH:        0.65,
        Shape.NUMERIC_TIGHT: 0.92,    # JIT-compiled vectorized -- STRENGTH
        Shape.RELATIONAL:    0.45,
        Shape.PARALLEL:      0.85,
        Shape.METAPROG:      0.75,
        Shape.IO_BOUND:      0.55,
    },
    "fortran": {
        Shape.BITWISE:       0.70,
        Shape.BIGNUM:        0.20,
        Shape.SYMBOLIC:      0.05,
        Shape.SEARCH:        0.60,
        Shape.NUMERIC_TIGHT: 0.95,    # dense numeric -- STRENGTH
        Shape.RELATIONAL:    0.20,
        Shape.PARALLEL:      0.85,
        Shape.METAPROG:      0.10,
        Shape.IO_BOUND:      0.40,
    },
    "go": {
        Shape.BITWISE:       0.80,
        Shape.BIGNUM:        0.60,
        Shape.SYMBOLIC:      0.30,
        Shape.SEARCH:        0.70,
        Shape.NUMERIC_TIGHT: 0.80,
        Shape.RELATIONAL:    0.40,
        Shape.PARALLEL:      0.95,    # goroutines -- STRENGTH
        Shape.METAPROG:      0.25,
        Shape.IO_BOUND:      0.85,
    },
    "perl": {
        Shape.BITWISE:       0.40,
        Shape.BIGNUM:        0.65,
        Shape.SYMBOLIC:      0.55,
        Shape.SEARCH:        0.50,
        Shape.NUMERIC_TIGHT: 0.25,    # interpreted, slow numeric
        Shape.RELATIONAL:    0.55,
        Shape.PARALLEL:      0.30,
        Shape.METAPROG:      0.60,
        Shape.IO_BOUND:      0.80,
    },
    "node": {
        Shape.BITWISE:       0.55,
        Shape.BIGNUM:        0.75,
        Shape.SYMBOLIC:      0.45,
        Shape.SEARCH:        0.65,
        Shape.NUMERIC_TIGHT: 0.70,    # V8 JIT
        Shape.RELATIONAL:    0.45,
        Shape.PARALLEL:      0.60,
        Shape.METAPROG:      0.55,
        Shape.IO_BOUND:      0.95,    # event loop -- STRENGTH
    },
    "awk": {
        Shape.BITWISE:       0.35,
        Shape.BIGNUM:        0.30,
        Shape.SYMBOLIC:      0.40,
        Shape.SEARCH:        0.40,
        Shape.NUMERIC_TIGHT: 0.55,    # mawk/gawk inner loop is C
        Shape.RELATIONAL:    0.65,    # associative arrays native
        Shape.PARALLEL:      0.15,
        Shape.METAPROG:      0.30,
        Shape.IO_BOUND:      0.85,
    },
}
