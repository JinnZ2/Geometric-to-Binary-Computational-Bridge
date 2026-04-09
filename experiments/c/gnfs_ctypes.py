"""
gnfs_ctypes.py — Python ctypes wrapper for libgeometric_nfs
============================================================
Drop-in accelerator for experiments/geometric_nfs.py.

Usage:
    from experiments.c.gnfs_ctypes import CAccelerator

    accel = CAccelerator()          # loads libgeometric_nfs.so
    if accel.available:
        ctx = accel.create_context(N, factor_base)
        candidates = accel.sieve_block(ctx, start_a, block_size, slack)
        for idx in candidates:
            rel = accel.trial_divide(ctx, start_a + idx)
            ...
        deps = accel.geometric_search(packed_states, n_relations, n_octahedra)
        accel.free_context(ctx)

If the shared library isn't found (not compiled), accel.available == False
and the Python NFS falls back to the pure-Python path automatically.
"""

import ctypes
import ctypes.util
import os
import sys
import math
from pathlib import Path
from typing import List, Optional, Tuple, Dict


def _find_library() -> Optional[ctypes.CDLL]:
    """Locate and load libgeometric_nfs.so/.dylib."""
    here = Path(__file__).parent

    # Try platform-specific names
    candidates = [
        here / "libgeometric_nfs.so",
        here / "libgeometric_nfs.dylib",
    ]

    for path in candidates:
        if path.exists():
            try:
                return ctypes.CDLL(str(path))
            except OSError:
                continue

    return None


class CAccelerator:
    """
    Thin ctypes bridge to the C geometric NFS library.

    All methods mirror the C API but accept/return Python types.
    If the library isn't available, .available is False and callers
    should fall back to pure Python.
    """

    def __init__(self):
        self._lib = _find_library()
        if self._lib is None:
            self.available = False
            return

        self.available = True
        self._setup_prototypes()

    # ── ctypes prototype declarations ──

    def _setup_prototypes(self):
        L = self._lib

        # sieve_context_create
        L.sieve_context_create.argtypes = [
            ctypes.c_uint64,                             # N
            ctypes.POINTER(ctypes.c_uint32),             # factor_base
            ctypes.c_uint32,                             # n_primes
        ]
        L.sieve_context_create.restype = ctypes.c_void_p

        # sieve_context_free
        L.sieve_context_free.argtypes = [ctypes.c_void_p]
        L.sieve_context_free.restype = None

        # sieve_block
        L.sieve_block.argtypes = [
            ctypes.c_void_p,     # ctx
            ctypes.c_int64,      # start_a
            ctypes.c_uint32,     # block_size
            ctypes.c_float,      # slack
        ]
        L.sieve_block.restype = ctypes.c_void_p

        # sieve_candidates_free
        L.sieve_candidates_free.argtypes = [ctypes.c_void_p]
        L.sieve_candidates_free.restype = None

        # trial_divide
        L.trial_divide.argtypes = [
            ctypes.c_void_p,     # ctx
            ctypes.c_int64,      # a
            ctypes.c_void_p,     # rel (smooth_relation_t*)
        ]
        L.trial_divide.restype = ctypes.c_int

        # pack_octahedral_states
        L.pack_octahedral_states.argtypes = [
            ctypes.POINTER(ctypes.c_uint32),  # exponents
            ctypes.c_uint32,                  # n_primes
            ctypes.c_uint32,                  # n_octahedra
            ctypes.POINTER(ctypes.c_uint8),   # out
        ]
        L.pack_octahedral_states.restype = None

        # geometric_search
        L.geometric_search.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),   # states
            ctypes.c_uint32,                  # n_relations
            ctypes.c_uint32,                  # n_octahedra
            ctypes.c_uint32,                  # max_depth
        ]
        L.geometric_search.restype = ctypes.c_void_p

        # dependency_list_free
        L.dependency_list_free.argtypes = [ctypes.c_void_p]
        L.dependency_list_free.restype = None

        # gf2_fallback
        L.gf2_fallback.argtypes = [
            ctypes.POINTER(ctypes.c_uint64),  # parity_rows
            ctypes.c_uint32,                  # n_rows
            ctypes.c_uint32,                  # n_cols
        ]
        L.gf2_fallback.restype = ctypes.c_void_p

        # gf2_fallback_wide
        L.gf2_fallback_wide.argtypes = [
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]
        L.gf2_fallback_wide.restype = ctypes.c_void_p

        # tonelli_shanks
        L.tonelli_shanks.argtypes = [ctypes.c_uint64, ctypes.c_uint32]
        L.tonelli_shanks.restype = ctypes.c_uint32

    # ── C struct mirrors (for reading results) ──

    class _SieveCandidates(ctypes.Structure):
        _fields_ = [
            ("indices",      ctypes.POINTER(ctypes.c_uint32)),
            ("n_candidates", ctypes.c_uint32),
            ("capacity",     ctypes.c_uint32),
        ]

    class _Dependency(ctypes.Structure):
        _fields_ = [
            ("indices",   ctypes.POINTER(ctypes.c_uint32)),
            ("n_indices", ctypes.c_uint32),
        ]

    class _DependencyList(ctypes.Structure):
        _fields_ = [
            ("deps",     ctypes.POINTER("CAccelerator._Dependency")),
            ("n_deps",   ctypes.c_uint32),
            ("capacity", ctypes.c_uint32),
        ]

    # ── Public API ──

    def create_context(self, N: int, factor_base: List[int]) -> ctypes.c_void_p:
        """Create a sieve context. Caller must call free_context() when done."""
        n = len(factor_base)
        fb_arr = (ctypes.c_uint32 * n)(*factor_base)
        return self._lib.sieve_context_create(N, fb_arr, n)

    def free_context(self, ctx: ctypes.c_void_p):
        """Free a sieve context."""
        self._lib.sieve_context_free(ctx)

    def sieve_block(self, ctx: ctypes.c_void_p, start_a: int,
                    block_size: int, slack: float) -> List[int]:
        """
        Run the log sieve over [start_a, start_a + block_size).
        Returns list of candidate offsets (indices into the block).
        """
        ptr = self._lib.sieve_block(ctx, start_a, block_size,
                                     ctypes.c_float(slack))
        if not ptr:
            return []

        # Cast to struct to read fields
        sc = ctypes.cast(ptr, ctypes.POINTER(self._SieveCandidates)).contents
        result = [sc.indices[i] for i in range(sc.n_candidates)]
        self._lib.sieve_candidates_free(ptr)
        return result

    def trial_divide(self, ctx: ctypes.c_void_p, a: int,
                     n_primes: int) -> Optional[Dict]:
        """
        Trial-divide a^2 - N over the factor base.
        Returns dict {prime_index: exponent} if smooth, None otherwise.
        """
        # Build a smooth_relation_t on the Python side
        exponents = (ctypes.c_uint32 * n_primes)()

        class _SmoothRelation(ctypes.Structure):
            _fields_ = [
                ("a",         ctypes.c_int64),
                ("Q",         ctypes.c_int64),
                ("exponents", ctypes.POINTER(ctypes.c_uint32)),
            ]

        rel = _SmoothRelation()
        rel.exponents = exponents

        result = self._lib.trial_divide(ctx, a, ctypes.byref(rel))
        if result == 1:
            exp_dict = {}
            for i in range(n_primes):
                if exponents[i] > 0:
                    exp_dict[i] = exponents[i]
            return {
                'a': rel.a,
                'Q': rel.Q,
                'exponents': exp_dict,
            }
        return None

    def pack_states(self, exponents_list: List[List[int]],
                    n_primes: int, n_octahedra: int) -> bytes:
        """
        Pack multiple relations' exponents into octahedral state rows.
        Returns a bytes object (row-major packed states).
        """
        row_bytes = (n_octahedra + 1) // 2
        total = len(exponents_list) * row_bytes
        buf = (ctypes.c_uint8 * total)()

        for i, exps in enumerate(exponents_list):
            exp_arr = (ctypes.c_uint32 * n_primes)(*exps)
            out_ptr = ctypes.cast(
                ctypes.addressof(buf) + i * row_bytes,
                ctypes.POINTER(ctypes.c_uint8),
            )
            self._lib.pack_octahedral_states(exp_arr, n_primes,
                                              n_octahedra, out_ptr)

        return bytes(buf)

    def geometric_search(self, packed_states: bytes,
                         n_relations: int, n_octahedra: int,
                         max_depth: int = 4) -> List[List[int]]:
        """
        Run geometric null space search on packed octahedral states.
        Returns list of dependencies (each a list of relation indices).
        """
        states_arr = (ctypes.c_uint8 * len(packed_states))(*packed_states)
        ptr = self._lib.geometric_search(states_arr, n_relations,
                                          n_octahedra, max_depth)
        if not ptr:
            return []

        return self._read_deplist(ptr)

    def gf2_solve(self, parity_rows: List[int],
                  n_cols: int) -> List[List[int]]:
        """
        GF(2) Gaussian elimination fallback.
        parity_rows: list of integers (bitmasks of odd exponents).
        n_cols: number of primes (factor base size).
        """
        n_rows = len(parity_rows)

        if n_cols <= 64:
            arr = (ctypes.c_uint64 * n_rows)(*parity_rows)
            ptr = self._lib.gf2_fallback(arr, n_rows, n_cols)
        else:
            n_words = (n_cols + 63) // 64
            arr = (ctypes.c_uint64 * (n_rows * n_words))()
            for i, row_val in enumerate(parity_rows):
                for w in range(n_words):
                    arr[i * n_words + w] = (row_val >> (64 * w)) & ((1 << 64) - 1)
            ptr = self._lib.gf2_fallback_wide(arr, n_rows, n_cols, n_words)

        if not ptr:
            return []

        return self._read_deplist(ptr)

    def _read_deplist(self, ptr) -> List[List[int]]:
        """Read a dependency_list_t from C and free it."""
        # Read the struct fields via raw memory
        # dependency_list_t layout: deps* (8 bytes), n_deps (4), capacity (4)
        n_deps = ctypes.cast(
            ptr + ctypes.sizeof(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_uint32),
        ).contents.value

        deps_ptr = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_void_p)).contents.value

        result = []
        # Each dependency_t: indices* (8 bytes), n_indices (4 bytes)
        dep_size = ctypes.sizeof(ctypes.c_void_p) + ctypes.sizeof(ctypes.c_uint32)
        # Align to pointer size
        dep_size = (dep_size + ctypes.sizeof(ctypes.c_void_p) - 1) & ~(ctypes.sizeof(ctypes.c_void_p) - 1)

        for d in range(n_deps):
            dep_addr = deps_ptr + d * dep_size
            indices_ptr = ctypes.cast(
                dep_addr, ctypes.POINTER(ctypes.c_void_p)
            ).contents.value
            n_indices = ctypes.cast(
                dep_addr + ctypes.sizeof(ctypes.c_void_p),
                ctypes.POINTER(ctypes.c_uint32),
            ).contents.value

            indices = []
            for i in range(n_indices):
                val = ctypes.cast(
                    indices_ptr + i * ctypes.sizeof(ctypes.c_uint32),
                    ctypes.POINTER(ctypes.c_uint32),
                ).contents.value
                indices.append(val)
            result.append(indices)

        self._lib.dependency_list_free(ptr)
        return result


# Convenience: try to load on import
_default_accel = None

def get_accelerator() -> CAccelerator:
    """Get (or create) the default C accelerator singleton."""
    global _default_accel
    if _default_accel is None:
        _default_accel = CAccelerator()
    return _default_accel
