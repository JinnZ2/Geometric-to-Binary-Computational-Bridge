/*
 * geometric_nfs_core.h — Geometric Number Field Sieve (C acceleration)
 * =====================================================================
 * C implementation of the hot-path routines from experiments/geometric_nfs.py.
 *
 * Three components:
 *   1. sieve_block()       — log sieve over a block of 'a' values
 *   2. geometric_search()  — octahedral null space search (phases 0-3)
 *   3. gf2_fallback()      — sparse GF(2) Gaussian elimination
 *
 * The octahedral model: factor-base primes are grouped in triples
 * (3 primes = 1 octahedron = 8 states = 3 bits). Each smooth relation
 * is represented as a packed array of 3-bit octahedral states encoding
 * which primes have odd exponents. A GF(2) dependency = a set of
 * relations whose octahedral states XOR to all-zero.
 *
 * Build:
 *   cc -O3 -shared -fPIC -o libgeometric_nfs.so geometric_nfs_core.c -lm
 *
 * License: CC-BY-4.0 (same as parent project)
 */

#ifndef GEOMETRIC_NFS_CORE_H
#define GEOMETRIC_NFS_CORE_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ======================================================================
 * DATA STRUCTURES
 * ====================================================================== */

/*
 * One octahedral unit: 3 primes with precomputed quadratic residue roots.
 * Mirrors experiments/geometric_nfs.py:Octahedron.
 */
typedef struct {
    uint32_t primes[3];       /* the 3 primes in this octahedron         */
    float    log_primes[3];   /* log(p) for each prime                   */
    int64_t  roots1[3];       /* first root:  a^2 ≡ N (mod p)           */
    int64_t  roots2[3];       /* second root (-root1 mod p), or -1       */
    uint32_t product;         /* p0 * p1 * p2 (for glyph projection)     */
} octahedron_t;

/*
 * Full sieve context — everything needed for sieve_block().
 */
typedef struct {
    uint64_t    N;                /* number to factor                     */
    uint64_t    sqrt_N;           /* isqrt(N) + 1                        */

    /* Factor base (all primes, flat) */
    uint32_t   *primes;           /* factor base primes                  */
    float      *log_primes;       /* log(p) for each prime               */
    int64_t    *roots1;           /* first sieve root per prime           */
    int64_t    *roots2;           /* second root per prime (-1 = none)    */
    uint32_t    n_primes;         /* total primes in factor base          */

    /* Octahedral grouping */
    octahedron_t *octahedra;      /* array of octahedra (n_primes/3)      */
    uint32_t      n_octahedra;    /* number of octahedra                  */
    uint32_t      n_leftover;     /* primes not in any octahedron         */
} sieve_context_t;

/*
 * Smooth relation found by sieve_block + trial division.
 */
typedef struct {
    int64_t  a;                   /* the sieved 'a' value                */
    int64_t  Q;                   /* a^2 - N                             */
    uint32_t *exponents;          /* exponent of each factor-base prime  */
    /* (allocated by caller, length = n_primes) */
} smooth_relation_t;

/*
 * Sieve block result: candidate indices that passed the log threshold.
 */
typedef struct {
    uint32_t *indices;            /* indices into [0..block_size) that
                                     passed the log threshold            */
    uint32_t  n_candidates;       /* number of candidates returned       */
    uint32_t  capacity;           /* allocated capacity of indices[]      */
} sieve_candidates_t;

/*
 * A single GF(2) dependency: a set of relation indices whose
 * octahedral states XOR to zero.
 */
typedef struct {
    uint32_t *indices;            /* relation indices in this dependency  */
    uint32_t  n_indices;          /* count                               */
} dependency_t;

/*
 * List of dependencies found by geometric_search / gf2_fallback.
 */
typedef struct {
    dependency_t *deps;           /* array of dependencies               */
    uint32_t      n_deps;         /* count                               */
    uint32_t      capacity;       /* allocated capacity of deps[]        */
} dependency_list_t;


/* ======================================================================
 * SIEVE — log accumulation + candidate extraction
 * ====================================================================== */

/*
 * Initialize a sieve context. Caller owns the returned struct.
 * factor_base_primes: array of primes (must be sorted ascending).
 * n_primes: length of factor_base_primes.
 * N: the number to factor.
 *
 * Computes quadratic residue roots for each prime via Tonelli-Shanks.
 * Groups primes into octahedra (triples).
 */
sieve_context_t *sieve_context_create(uint64_t N,
                                       const uint32_t *factor_base_primes,
                                       uint32_t n_primes);

/*
 * Free all memory owned by a sieve context.
 */
void sieve_context_free(sieve_context_t *ctx);

/*
 * Sieve one block: accumulate log(p) contributions for a-values
 * in [start_a, start_a + block_size).
 *
 * Returns candidates whose accumulated log exceeds the per-position
 * threshold log(|a^2 - N|) - slack.  Caller must free the result
 * with sieve_candidates_free().
 *
 * slack: log tolerance (typically max_log_p, the log of the largest
 *        prime in the factor base).
 */
sieve_candidates_t *sieve_block(const sieve_context_t *ctx,
                                 int64_t start_a,
                                 uint32_t block_size,
                                 float slack);

/*
 * Free a sieve_candidates_t returned by sieve_block().
 */
void sieve_candidates_free(sieve_candidates_t *sc);

/*
 * Trial-divide a single candidate a against the factor base.
 * Fills rel->exponents (must be pre-allocated to ctx->n_primes).
 * Returns 1 if a^2-N is smooth over the factor base, 0 otherwise.
 */
int trial_divide(const sieve_context_t *ctx,
                 int64_t a,
                 smooth_relation_t *rel);


/* ======================================================================
 * GEOMETRIC NULL SPACE SEARCH
 * ====================================================================== */

/*
 * Pack a smooth relation's exponents into 3-bit octahedral states.
 *
 * For each octahedron (3 primes), the state (0-7) = bitmask of which
 * primes have odd exponents. Packed 3 bits per octahedron, 2 states
 * per byte (bits 0-2 = first state, bits 4-6 = second), with the
 * high nibble unused when n_octahedra is odd.
 *
 * out: must have room for (n_octahedra + 1) / 2 bytes.
 */
void pack_octahedral_states(const uint32_t *exponents,
                             uint32_t n_primes,
                             uint32_t n_octahedra,
                             uint8_t *out);

/*
 * Geometric null space search over packed octahedral states.
 *
 * Implements four phases (mirroring geometric_null_search in Python):
 *   Phase 0: Singles — relations with all-zero states (weight 0).
 *   Phase 1: Hash duplicates — identical state vectors cancel via XOR.
 *   Phase 2: Near-duplicates — states differing in 1 octahedron,
 *            found via delete-one signatures.
 *   Phase 3: Iterative cancellation — partial XOR pairs extended
 *            to triples/quads.
 *
 * states:       row-major packed states, one row per relation.
 *               Row i starts at states[i * row_bytes].
 * n_relations:  number of rows.
 * n_octahedra:  number of octahedra per row.
 * max_depth:    maximum dependency size to search for (2-4).
 *
 * Returns a dependency_list_t (caller must free with dependency_list_free).
 */
dependency_list_t *geometric_search(const uint8_t *states,
                                     uint32_t n_relations,
                                     uint32_t n_octahedra,
                                     uint32_t max_depth);

/*
 * Free a dependency_list_t.
 */
void dependency_list_free(dependency_list_t *dl);


/* ======================================================================
 * GF(2) SPARSE GAUSSIAN ELIMINATION (fallback)
 * ====================================================================== */

/*
 * Standard GF(2) Gaussian elimination on the parity matrix.
 *
 * parity_rows: array of n_rows uint64_t bitmasks.  Bit j of row i
 *              is 1 iff prime j has an odd exponent in relation i.
 *              (Supports up to 64 primes; for larger factor bases,
 *              use parity_rows_wide / gf2_fallback_wide.)
 * n_rows:      number of relations.
 * n_cols:      number of primes (factor base size), must be <= 64.
 *
 * Returns dependencies found in the null space.
 */
dependency_list_t *gf2_fallback(const uint64_t *parity_rows,
                                 uint32_t n_rows,
                                 uint32_t n_cols);

/*
 * Wide GF(2) elimination for factor bases > 64 primes.
 *
 * parity_rows: array of n_rows * n_words uint64_t words.
 *              Row i occupies words [i*n_words .. (i+1)*n_words).
 * n_words:     ceil(n_cols / 64).
 */
dependency_list_t *gf2_fallback_wide(const uint64_t *parity_rows,
                                      uint32_t n_rows,
                                      uint32_t n_cols,
                                      uint32_t n_words);


/* ======================================================================
 * UTILITY
 * ====================================================================== */

/*
 * Tonelli-Shanks: compute sqrt(n) mod p.
 * Returns the root, or (uint32_t)-1 if n is not a QR mod p.
 */
uint32_t tonelli_shanks(uint64_t n, uint32_t p);

/*
 * Bytes per row in packed octahedral state arrays.
 */
static inline uint32_t octa_row_bytes(uint32_t n_octahedra) {
    return (n_octahedra + 1) / 2;
}

/*
 * Read the 3-bit state of octahedron k from a packed row.
 */
static inline uint8_t octa_get(const uint8_t *row, uint32_t k) {
    uint32_t byte_idx = k / 2;
    return (k & 1) ? (row[byte_idx] >> 4) & 0x07
                    : row[byte_idx] & 0x07;
}

/*
 * Set the 3-bit state of octahedron k in a packed row.
 */
static inline void octa_set(uint8_t *row, uint32_t k, uint8_t val) {
    uint32_t byte_idx = k / 2;
    if (k & 1)
        row[byte_idx] = (row[byte_idx] & 0x0F) | ((val & 0x07) << 4);
    else
        row[byte_idx] = (row[byte_idx] & 0xF0) | (val & 0x07);
}

/*
 * XOR two packed octahedral state rows: dst[i] ^= src[i].
 */
static inline void octa_xor_row(uint8_t *dst, const uint8_t *src,
                                  uint32_t n_bytes) {
    for (uint32_t i = 0; i < n_bytes; i++)
        dst[i] ^= src[i];
}

/*
 * Check if a packed octahedral state row is all-zero.
 */
static inline int octa_is_zero(const uint8_t *row, uint32_t n_bytes) {
    for (uint32_t i = 0; i < n_bytes; i++)
        if (row[i] != 0) return 0;
    return 1;
}

/*
 * Count non-zero octahedral states in a packed row (the "weight").
 */
static inline uint32_t octa_weight(const uint8_t *row, uint32_t n_octahedra) {
    uint32_t w = 0;
    for (uint32_t k = 0; k < n_octahedra; k++)
        if (octa_get(row, k) != 0) w++;
    return w;
}


#ifdef __cplusplus
}
#endif

#endif /* GEOMETRIC_NFS_CORE_H */
