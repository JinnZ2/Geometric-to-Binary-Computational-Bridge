/*
 * geometric_nfs_core.c -- Geometric Number Field Sieve (C acceleration)
 * =====================================================================
 * Implementation of the hot-path routines declared in geometric_nfs_core.h.
 * Mirrors experiments/geometric_nfs.py but in C for ~50-100x speedup on
 * the inner sieve loop and GF(2) elimination.
 *
 * License: CC-BY-4.0
 */

#include "geometric_nfs_core.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>

/* ======================================================================
 * INTERNAL HELPERS
 * ====================================================================== */

static uint64_t _isqrt(uint64_t n) {
    if (n == 0) return 0;
    uint64_t x = (uint64_t)sqrt((double)n);
    while (x > 0 && x * x > n) x--;
    while ((x + 1) * (x + 1) <= n) x++;
    return x;
}

static uint64_t _powmod(uint64_t base, uint64_t exp, uint64_t mod) {
    uint64_t result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1)
            result = (__uint128_t)result * base % mod;
        exp >>= 1;
        base = (__uint128_t)base * base % mod;
    }
    return result;
}

static uint64_t _abs64(int64_t v) {
    return v < 0 ? (uint64_t)(-v) : (uint64_t)v;
}

/* Simple FNV-1a hash for packed octahedral rows */
static uint32_t _hash_row(const uint8_t *row, uint32_t n_bytes) {
    uint32_t h = 2166136261u;
    for (uint32_t i = 0; i < n_bytes; i++) {
        h ^= row[i];
        h *= 16777619u;
    }
    return h;
}

/* ======================================================================
 * DEPENDENCY LIST HELPERS
 * ====================================================================== */

static dependency_list_t *_deplist_create(void) {
    dependency_list_t *dl = calloc(1, sizeof(dependency_list_t));
    if (!dl) return NULL;
    dl->capacity = 16;
    dl->deps = calloc(dl->capacity, sizeof(dependency_t));
    return dl;
}

static void _deplist_push(dependency_list_t *dl,
                           const uint32_t *indices, uint32_t n) {
    if (!dl) return;
    if (dl->n_deps >= dl->capacity) {
        dl->capacity *= 2;
        dl->deps = realloc(dl->deps, dl->capacity * sizeof(dependency_t));
    }
    dependency_t *d = &dl->deps[dl->n_deps++];
    d->n_indices = n;
    d->indices = malloc(n * sizeof(uint32_t));
    memcpy(d->indices, indices, n * sizeof(uint32_t));
}

void dependency_list_free(dependency_list_t *dl) {
    if (!dl) return;
    for (uint32_t i = 0; i < dl->n_deps; i++)
        free(dl->deps[i].indices);
    free(dl->deps);
    free(dl);
}

/* ======================================================================
 * TONELLI-SHANKS
 * ====================================================================== */

uint32_t tonelli_shanks(uint64_t n, uint32_t p) {
    if (p == 0) return (uint32_t)-1;
    n %= p;
    if (n == 0) return 0;
    if (p == 2) return (uint32_t)(n & 1);

    /* Euler criterion: n^((p-1)/2) must be 1 */
    if (_powmod(n, (p - 1) / 2, p) != 1)
        return (uint32_t)-1;  /* not a QR */

    /* Factor out powers of 2 from p-1: p-1 = Q * 2^S */
    uint64_t Q = p - 1;
    uint32_t S = 0;
    while ((Q & 1) == 0) { Q >>= 1; S++; }

    /* Simple case: p = 3 mod 4 */
    if (S == 1)
        return (uint32_t)_powmod(n, (p + 1) / 4, p);

    /* Find a quadratic non-residue z */
    uint64_t z = 2;
    while (_powmod(z, (p - 1) / 2, p) != (uint64_t)(p - 1))
        z++;

    uint32_t M = S;
    uint64_t c = _powmod(z, Q, p);
    uint64_t t = _powmod(n, Q, p);
    uint64_t R = _powmod(n, (Q + 1) / 2, p);

    while (1) {
        if (t == 1) return (uint32_t)R;

        /* Find least i such that t^(2^i) = 1 (mod p) */
        uint32_t i = 1;
        uint64_t tmp = (__uint128_t)t * t % p;
        while (tmp != 1) {
            tmp = (__uint128_t)tmp * tmp % p;
            i++;
        }

        uint64_t b = c;
        for (uint32_t j = 0; j < M - i - 1; j++)
            b = (__uint128_t)b * b % p;

        M = i;
        c = (__uint128_t)b * b % p;
        t = (__uint128_t)t * c % p;
        R = (__uint128_t)R * b % p;
    }
}

/* ======================================================================
 * SIEVE CONTEXT
 * ====================================================================== */

sieve_context_t *sieve_context_create(uint64_t N,
                                       const uint32_t *factor_base_primes,
                                       uint32_t n_primes) {
    sieve_context_t *ctx = calloc(1, sizeof(sieve_context_t));
    if (!ctx) return NULL;

    ctx->N = N;
    ctx->sqrt_N = _isqrt(N) + 1;
    ctx->n_primes = n_primes;

    /* Allocate flat arrays */
    ctx->primes     = malloc(n_primes * sizeof(uint32_t));
    ctx->log_primes = malloc(n_primes * sizeof(float));
    ctx->roots1     = malloc(n_primes * sizeof(int64_t));
    ctx->roots2     = malloc(n_primes * sizeof(int64_t));

    if (!ctx->primes || !ctx->log_primes || !ctx->roots1 || !ctx->roots2) {
        sieve_context_free(ctx);
        return NULL;
    }

    memcpy(ctx->primes, factor_base_primes, n_primes * sizeof(uint32_t));

    for (uint32_t i = 0; i < n_primes; i++) {
        uint32_t p = factor_base_primes[i];
        ctx->log_primes[i] = logf((float)p);

        /* Compute quadratic residue roots: a^2 = N mod p */
        uint32_t r = tonelli_shanks(N % p, p);
        if (r == (uint32_t)-1) {
            ctx->roots1[i] = -1;
            ctx->roots2[i] = -1;
        } else {
            ctx->roots1[i] = (int64_t)r;
            int64_t r2 = (int64_t)p - (int64_t)r;
            ctx->roots2[i] = (r2 != (int64_t)r) ? r2 : -1;
        }
    }

    /* Build octahedra (groups of 3) */
    ctx->n_octahedra = n_primes / 3;
    ctx->n_leftover  = n_primes - ctx->n_octahedra * 3;

    if (ctx->n_octahedra > 0) {
        ctx->octahedra = calloc(ctx->n_octahedra, sizeof(octahedron_t));
        for (uint32_t oi = 0; oi < ctx->n_octahedra; oi++) {
            octahedron_t *oct = &ctx->octahedra[oi];
            for (int j = 0; j < 3; j++) {
                uint32_t idx = oi * 3 + j;
                oct->primes[j]     = ctx->primes[idx];
                oct->log_primes[j] = ctx->log_primes[idx];
                oct->roots1[j]     = ctx->roots1[idx];
                oct->roots2[j]     = ctx->roots2[idx];
            }
            oct->product = (uint32_t)oct->primes[0]
                         * (uint32_t)oct->primes[1]
                         * (uint32_t)oct->primes[2];
        }
    }

    return ctx;
}

void sieve_context_free(sieve_context_t *ctx) {
    if (!ctx) return;
    free(ctx->primes);
    free(ctx->log_primes);
    free(ctx->roots1);
    free(ctx->roots2);
    free(ctx->octahedra);
    free(ctx);
}

/* ======================================================================
 * SIEVE BLOCK
 * ====================================================================== */

sieve_candidates_t *sieve_block(const sieve_context_t *ctx,
                                 int64_t start_a,
                                 uint32_t block_size,
                                 float slack) {
    /* Allocate log accumulator */
    float *sieve_log = calloc(block_size, sizeof(float));
    if (!sieve_log) return NULL;

    /* Stride sieve: for each prime, add log(p) at hit positions */
    for (uint32_t i = 0; i < ctx->n_primes; i++) {
        uint32_t p = ctx->primes[i];
        float logp = ctx->log_primes[i];
        int64_t sa_mod = ((start_a % (int64_t)p) + (int64_t)p) % (int64_t)p;

        /* Root 1 */
        if (ctx->roots1[i] >= 0) {
            int64_t r = ctx->roots1[i];
            int64_t first = ((r - sa_mod) % (int64_t)p + (int64_t)p) % (int64_t)p;
            for (int64_t pos = first; pos < (int64_t)block_size; pos += p)
                sieve_log[pos] += logp;
        }

        /* Root 2 */
        if (ctx->roots2[i] >= 0) {
            int64_t r = ctx->roots2[i];
            int64_t first = ((r - sa_mod) % (int64_t)p + (int64_t)p) % (int64_t)p;
            for (int64_t pos = first; pos < (int64_t)block_size; pos += p)
                sieve_log[pos] += logp;
        }
    }

    /* Extract candidates that pass per-position threshold */
    sieve_candidates_t *sc = calloc(1, sizeof(sieve_candidates_t));
    sc->capacity = 256;
    sc->indices  = malloc(sc->capacity * sizeof(uint32_t));
    sc->n_candidates = 0;

    for (uint32_t i = 0; i < block_size; i++) {
        int64_t a = start_a + (int64_t)i;
        /* Q = a^2 - N.  Use 128-bit to avoid overflow. */
        __int128 Q128 = (__int128)a * a - (__int128)ctx->N;
        double absQ;
        if (Q128 < 0) {
            absQ = (double)(uint64_t)(-Q128);
        } else if (Q128 == 0) {
            continue; /* Q=0 is trivial */
        } else {
            absQ = (double)(uint64_t)Q128;
        }

        float threshold = (absQ > 1.0) ? logf((float)absQ) - slack : 0.0f;

        if (sieve_log[i] >= threshold) {
            if (sc->n_candidates >= sc->capacity) {
                sc->capacity *= 2;
                sc->indices = realloc(sc->indices,
                                       sc->capacity * sizeof(uint32_t));
            }
            sc->indices[sc->n_candidates++] = i;
        }
    }

    free(sieve_log);
    return sc;
}

void sieve_candidates_free(sieve_candidates_t *sc) {
    if (!sc) return;
    free(sc->indices);
    free(sc);
}

/* ======================================================================
 * TRIAL DIVISION
 * ====================================================================== */

int trial_divide(const sieve_context_t *ctx, int64_t a,
                 smooth_relation_t *rel) {
    __int128 Q128 = (__int128)a * a - (__int128)ctx->N;
    int64_t Q = (int64_t)Q128;
    uint64_t remainder = _abs64(Q);

    rel->a = a;
    rel->Q = Q;

    if (remainder == 0) return 0;

    for (uint32_t i = 0; i < ctx->n_primes; i++) {
        uint32_t p = ctx->primes[i];
        uint32_t count = 0;
        while (remainder % p == 0) {
            count++;
            remainder /= p;
        }
        rel->exponents[i] = count;
    }

    return (remainder == 1) ? 1 : 0;
}

/* ======================================================================
 * OCTAHEDRAL STATE PACKING
 * ====================================================================== */

void pack_octahedral_states(const uint32_t *exponents,
                             uint32_t n_primes,
                             uint32_t n_octahedra,
                             uint8_t *out) {
    uint32_t rb = octa_row_bytes(n_octahedra);
    memset(out, 0, rb);

    for (uint32_t k = 0; k < n_octahedra; k++) {
        uint8_t state = 0;
        for (int j = 0; j < 3; j++) {
            uint32_t idx = k * 3 + j;
            if (idx < n_primes && (exponents[idx] & 1))
                state |= (1 << j);
        }
        octa_set(out, k, state);
    }
}

/* ======================================================================
 * GEOMETRIC NULL SPACE SEARCH
 * ====================================================================== */

/* Hash-table bucket for Phase 1 (exact duplicates) */
typedef struct _hash_entry {
    uint32_t hash;
    uint32_t rel_idx;
    struct _hash_entry *next;
} hash_entry_t;

#define HASH_BUCKETS 4096

dependency_list_t *geometric_search(const uint8_t *states,
                                     uint32_t n_relations,
                                     uint32_t n_octahedra,
                                     uint32_t max_depth) {
    dependency_list_t *dl = _deplist_create();
    if (!dl) return NULL;

    uint32_t rb = octa_row_bytes(n_octahedra);

    /* ---- Phase 0: Singles (all-zero rows) ---- */
    for (uint32_t i = 0; i < n_relations; i++) {
        if (octa_is_zero(states + i * rb, rb)) {
            _deplist_push(dl, &i, 1);
        }
    }

    /* ---- Phase 1: Hash duplicates ---- */
    /* Build hash table: hash(row) -> list of relation indices */
    hash_entry_t **ht = calloc(HASH_BUCKETS, sizeof(hash_entry_t *));
    /* Pool allocator for entries */
    hash_entry_t *pool = malloc(n_relations * sizeof(hash_entry_t));

    for (uint32_t i = 0; i < n_relations; i++) {
        const uint8_t *row = states + i * rb;
        if (octa_is_zero(row, rb)) continue;

        uint32_t h = _hash_row(row, rb);
        uint32_t bucket = h % HASH_BUCKETS;

        /* Check for exact matches in this bucket */
        for (hash_entry_t *e = ht[bucket]; e; e = e->next) {
            if (e->hash == h) {
                const uint8_t *other = states + e->rel_idx * rb;
                if (memcmp(row, other, rb) == 0) {
                    uint32_t pair[2] = {e->rel_idx, i};
                    _deplist_push(dl, pair, 2);
                }
            }
        }

        /* Insert into hash table */
        hash_entry_t *entry = &pool[i];
        entry->hash = h;
        entry->rel_idx = i;
        entry->next = ht[bucket];
        ht[bucket] = entry;
    }

    free(ht);
    free(pool);

    if (dl->n_deps > 0) return dl;

    if (max_depth < 2) return dl;

    /* ---- Phase 2: Near-duplicates (differ in 1 octahedron) ---- */
    /* For each row, generate delete-one signatures and hash them.
       Two rows with the same delete-one sig differ in at most 1 octahedron. */

    uint8_t *sig_buf = malloc(rb);
    hash_entry_t **ht2 = calloc(HASH_BUCKETS, sizeof(hash_entry_t *));
    /* Over-allocate pool: each row generates up to n_octahedra entries */
    uint32_t max_entries2 = n_relations * (n_octahedra < 8 ? n_octahedra : 8);
    if (max_entries2 > 2000000) max_entries2 = 2000000;

    typedef struct {
        uint32_t hash;
        uint32_t rel_idx;
        uint32_t octa_idx;
        uint8_t  val;
        void    *next;
    } sig_entry_t;

    sig_entry_t *pool2 = malloc(max_entries2 * sizeof(sig_entry_t));
    uint32_t pool2_used = 0;

    for (uint32_t i = 0; i < n_relations && pool2_used < max_entries2 - n_octahedra; i++) {
        const uint8_t *row = states + i * rb;
        if (octa_is_zero(row, rb)) continue;

        for (uint32_t k = 0; k < n_octahedra; k++) {
            uint8_t v = octa_get(row, k);
            if (v == 0) continue;

            /* Build signature: row with octahedron k zeroed */
            memcpy(sig_buf, row, rb);
            octa_set(sig_buf, k, 0);

            uint32_t h = _hash_row(sig_buf, rb);
            h ^= (k * 2654435761u);  /* mix in which octa was deleted */
            uint32_t bucket = h % HASH_BUCKETS;

            /* Check for matches: same sig + same deleted octahedron */
            for (sig_entry_t *e = (sig_entry_t *)ht2[bucket]; e; e = e->next) {
                if (e->hash == h && e->octa_idx == k) {
                    /* Verify the rest of the row matches */
                    const uint8_t *other_row = states + e->rel_idx * rb;
                    memcpy(sig_buf, other_row, rb);
                    octa_set(sig_buf, k, 0);

                    uint8_t *my_sig = malloc(rb);
                    memcpy(my_sig, row, rb);
                    octa_set(my_sig, k, 0);

                    if (memcmp(my_sig, sig_buf, rb) == 0) {
                        /* Same signature: they differ only at octahedron k */
                        if (e->val == v) {
                            /* Same value at k: XOR cancels completely */
                            uint32_t pair[2] = {e->rel_idx, i};
                            _deplist_push(dl, pair, 2);
                        }
                        /* Different values: would need a third relation to cancel */
                    }
                    free(my_sig);
                }
            }

            /* Insert */
            if (pool2_used < max_entries2) {
                sig_entry_t *entry = &pool2[pool2_used++];
                entry->hash = h;
                entry->rel_idx = i;
                entry->octa_idx = k;
                entry->val = v;
                entry->next = ht2[bucket];
                ht2[bucket] = (hash_entry_t *)entry;
            }
        }
    }

    free(sig_buf);
    free(ht2);
    free(pool2);

    if (dl->n_deps > 0) return dl;

    if (max_depth < 3) return dl;

    /* ---- Phase 3: Iterative cancellation ---- */
    /* XOR pairs of rows. If the result has low weight, store it.
       Then try to cancel the residual with a third row. */
    uint32_t max_pairs = n_relations < 500 ? n_relations : 500;

    /* Temp buffer for XOR result */
    uint8_t *xor_buf = malloc(rb);

    /* Index: hash(row) -> relation index, for quick lookup */
    hash_entry_t **ht3 = calloc(HASH_BUCKETS, sizeof(hash_entry_t *));
    hash_entry_t *pool3 = malloc(n_relations * sizeof(hash_entry_t));

    for (uint32_t i = 0; i < n_relations; i++) {
        const uint8_t *row = states + i * rb;
        if (octa_is_zero(row, rb)) continue;
        uint32_t h = _hash_row(row, rb);
        uint32_t bucket = h % HASH_BUCKETS;
        pool3[i].hash = h;
        pool3[i].rel_idx = i;
        pool3[i].next = ht3[bucket];
        ht3[bucket] = &pool3[i];
    }

    for (uint32_t i = 0; i < max_pairs && dl->n_deps == 0; i++) {
        const uint8_t *row_i = states + i * rb;
        if (octa_is_zero(row_i, rb)) continue;

        for (uint32_t j = i + 1; j < max_pairs; j++) {
            const uint8_t *row_j = states + j * rb;
            if (octa_is_zero(row_j, rb)) continue;

            /* XOR the two rows */
            memcpy(xor_buf, row_i, rb);
            octa_xor_row(xor_buf, row_j, rb);

            if (octa_is_zero(xor_buf, rb)) {
                uint32_t pair[2] = {i, j};
                _deplist_push(dl, pair, 2);
                break;
            }

            uint32_t w = octa_weight(xor_buf, n_octahedra);
            if (w <= 3) {
                /* Low-weight residual: look for a third row that matches */
                uint32_t h = _hash_row(xor_buf, rb);
                uint32_t bucket = h % HASH_BUCKETS;
                for (hash_entry_t *e = ht3[bucket]; e; e = e->next) {
                    if (e->hash == h && e->rel_idx != i && e->rel_idx != j) {
                        const uint8_t *row_k = states + e->rel_idx * rb;
                        if (memcmp(xor_buf, row_k, rb) == 0) {
                            uint32_t triple[3] = {i, j, e->rel_idx};
                            _deplist_push(dl, triple, 3);
                            break;
                        }
                    }
                }
            }
            if (dl->n_deps > 0) break;
        }
    }

    free(xor_buf);
    free(ht3);
    free(pool3);

    return dl;
}

/* ======================================================================
 * GF(2) GAUSSIAN ELIMINATION — NARROW (<=64 primes)
 * ====================================================================== */

dependency_list_t *gf2_fallback(const uint64_t *parity_rows,
                                 uint32_t n_rows,
                                 uint32_t n_cols) {
    dependency_list_t *dl = _deplist_create();
    if (!dl || n_rows == 0) return dl;

    /* Augmented matrix: [parity (uint64_t) | identity (uint8_t per row)] */
    uint64_t *M = malloc(n_rows * sizeof(uint64_t));
    /* Identity tracking: M_id[i * n_rows + j] = 1 if row j contributes to row i */
    uint8_t *M_id = calloc((size_t)n_rows * n_rows, sizeof(uint8_t));

    for (uint32_t i = 0; i < n_rows; i++) {
        M[i] = parity_rows[i];
        M_id[i * n_rows + i] = 1;
    }

    /* Gaussian elimination */
    uint32_t rank = 0;
    for (uint32_t col = 0; col < n_cols && rank < n_rows; col++) {
        uint64_t col_mask = 1ULL << col;

        /* Find pivot */
        uint32_t pivot = n_rows;  /* sentinel */
        for (uint32_t row = rank; row < n_rows; row++) {
            if (M[row] & col_mask) { pivot = row; break; }
        }
        if (pivot == n_rows) continue;

        /* Swap pivot to rank position */
        if (pivot != rank) {
            uint64_t tmp_m = M[rank]; M[rank] = M[pivot]; M[pivot] = tmp_m;
            /* Swap identity rows */
            for (uint32_t j = 0; j < n_rows; j++) {
                uint8_t tmp = M_id[rank * n_rows + j];
                M_id[rank * n_rows + j] = M_id[pivot * n_rows + j];
                M_id[pivot * n_rows + j] = tmp;
            }
        }

        /* Eliminate column from all other rows */
        for (uint32_t row = 0; row < n_rows; row++) {
            if (row != rank && (M[row] & col_mask)) {
                M[row] ^= M[rank];
                for (uint32_t j = 0; j < n_rows; j++)
                    M_id[row * n_rows + j] ^= M_id[rank * n_rows + j];
            }
        }
        rank++;
    }

    /* Extract null vectors: rows where all parity bits are 0 */
    uint64_t parity_mask = (n_cols >= 64) ? ~0ULL : ((1ULL << n_cols) - 1);

    for (uint32_t i = 0; i < n_rows; i++) {
        if ((M[i] & parity_mask) != 0) continue;

        /* Count contributing relations */
        uint32_t count = 0;
        for (uint32_t j = 0; j < n_rows; j++)
            if (M_id[i * n_rows + j]) count++;

        if (count > 0) {
            uint32_t *indices = malloc(count * sizeof(uint32_t));
            uint32_t k = 0;
            for (uint32_t j = 0; j < n_rows; j++)
                if (M_id[i * n_rows + j]) indices[k++] = j;
            _deplist_push(dl, indices, count);
            free(indices);
        }
    }

    free(M);
    free(M_id);
    return dl;
}

/* ======================================================================
 * GF(2) GAUSSIAN ELIMINATION — WIDE (>64 primes)
 * ====================================================================== */

dependency_list_t *gf2_fallback_wide(const uint64_t *parity_rows,
                                      uint32_t n_rows,
                                      uint32_t n_cols,
                                      uint32_t n_words) {
    dependency_list_t *dl = _deplist_create();
    if (!dl || n_rows == 0) return dl;

    /* Augmented: [parity (n_words words) | identity tracking] */
    uint64_t *M = malloc((size_t)n_rows * n_words * sizeof(uint64_t));
    uint8_t *M_id = calloc((size_t)n_rows * n_rows, sizeof(uint8_t));

    for (uint32_t i = 0; i < n_rows; i++) {
        memcpy(M + (size_t)i * n_words,
               parity_rows + (size_t)i * n_words,
               n_words * sizeof(uint64_t));
        M_id[i * n_rows + i] = 1;
    }

    /* Gaussian elimination */
    uint32_t rank = 0;
    for (uint32_t col = 0; col < n_cols && rank < n_rows; col++) {
        uint32_t word_idx = col / 64;
        uint64_t bit_mask = 1ULL << (col % 64);

        /* Find pivot */
        uint32_t pivot = n_rows;
        for (uint32_t row = rank; row < n_rows; row++) {
            if (M[row * n_words + word_idx] & bit_mask) {
                pivot = row;
                break;
            }
        }
        if (pivot == n_rows) continue;

        /* Swap pivot to rank */
        if (pivot != rank) {
            for (uint32_t w = 0; w < n_words; w++) {
                uint64_t tmp = M[rank * n_words + w];
                M[rank * n_words + w] = M[pivot * n_words + w];
                M[pivot * n_words + w] = tmp;
            }
            for (uint32_t j = 0; j < n_rows; j++) {
                uint8_t tmp = M_id[rank * n_rows + j];
                M_id[rank * n_rows + j] = M_id[pivot * n_rows + j];
                M_id[pivot * n_rows + j] = tmp;
            }
        }

        /* Eliminate */
        for (uint32_t row = 0; row < n_rows; row++) {
            if (row != rank && (M[row * n_words + word_idx] & bit_mask)) {
                for (uint32_t w = 0; w < n_words; w++)
                    M[row * n_words + w] ^= M[rank * n_words + w];
                for (uint32_t j = 0; j < n_rows; j++)
                    M_id[row * n_rows + j] ^= M_id[rank * n_rows + j];
            }
        }
        rank++;
    }

    /* Extract null vectors */
    for (uint32_t i = 0; i < n_rows; i++) {
        int is_null = 1;
        for (uint32_t w = 0; w < n_words && is_null; w++) {
            uint64_t mask = ~0ULL;
            /* Last word may not use all 64 bits */
            if (w == n_words - 1 && (n_cols % 64) != 0)
                mask = (1ULL << (n_cols % 64)) - 1;
            if (M[i * n_words + w] & mask) is_null = 0;
        }
        if (!is_null) continue;

        uint32_t count = 0;
        for (uint32_t j = 0; j < n_rows; j++)
            if (M_id[i * n_rows + j]) count++;

        if (count > 0) {
            uint32_t *indices = malloc(count * sizeof(uint32_t));
            uint32_t k = 0;
            for (uint32_t j = 0; j < n_rows; j++)
                if (M_id[i * n_rows + j]) indices[k++] = j;
            _deplist_push(dl, indices, count);
            free(indices);
        }
    }

    free(M);
    free(M_id);
    return dl;
}
