/*
 * test_nfs.c — Smoke test for geometric_nfs_core
 *
 * Factors small semiprimes to verify the sieve, geometric search,
 * and GF(2) fallback all produce correct results.
 *
 * Build & run:  make test
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "geometric_nfs_core.h"

/* ---------- helpers ---------- */

static int is_prime(uint32_t n) {
    if (n < 2) return 0;
    if (n < 4) return 1;
    if (n % 2 == 0 || n % 3 == 0) return 0;
    for (uint32_t i = 5; i * i <= n; i += 6)
        if (n % i == 0 || n % (i + 2) == 0) return 0;
    return 1;
}

/* Compute factor base: primes <= B where N is a QR mod p */
static uint32_t *make_factor_base(uint64_t N, uint32_t B, uint32_t *out_n) {
    uint32_t *fb = malloc(B * sizeof(uint32_t));
    uint32_t n = 0;
    fb[n++] = 2;  /* 2 always included */
    for (uint32_t p = 3; p <= B; p += 2) {
        if (!is_prime(p)) continue;
        /* Euler criterion: N^((p-1)/2) mod p == 1 means N is QR mod p */
        uint64_t exp = (p - 1) / 2;
        uint64_t base = N % p;
        uint64_t result = 1;
        uint64_t b = base;
        for (uint64_t e = exp; e > 0; e >>= 1) {
            if (e & 1) result = (result * b) % p;
            b = (b * b) % p;
        }
        if (result == 1 || p == 2)
            fb[n++] = p;
    }
    *out_n = n;
    return fb;
}

static uint64_t isqrt64(uint64_t n) {
    if (n == 0) return 0;
    uint64_t x = (uint64_t)sqrt((double)n);
    while (x * x > n) x--;
    while ((x + 1) * (x + 1) <= n) x++;
    return x;
}

/* ---------- tests ---------- */

static int tests_run = 0;
static int tests_passed = 0;

#define ASSERT(cond, msg) do { \
    tests_run++; \
    if (!(cond)) { printf("  FAIL: %s\n", msg); } \
    else { tests_passed++; } \
} while(0)

static void test_tonelli_shanks(void) {
    printf("== tonelli_shanks ==\n");

    /* sqrt(2) mod 7 = 3 or 4 (since 3^2=9=2 mod 7, 4^2=16=2 mod 7) */
    uint32_t r = tonelli_shanks(2, 7);
    ASSERT(r != (uint32_t)-1, "2 is QR mod 7");
    ASSERT((uint64_t)r * r % 7 == 2, "root^2 = 2 mod 7");

    /* 3 is not a QR mod 7 */
    r = tonelli_shanks(3, 7);
    ASSERT(r == (uint32_t)-1, "3 is not QR mod 7");

    /* sqrt(2) mod 17 = 6 or 11 */
    r = tonelli_shanks(2, 17);
    ASSERT(r != (uint32_t)-1, "2 is QR mod 17");
    ASSERT((uint64_t)r * r % 17 == 2, "root^2 = 2 mod 17");

    /* sqrt(0) mod p = 0 */
    r = tonelli_shanks(0, 13);
    ASSERT(r == 0, "sqrt(0) mod 13 = 0");

    printf("  %d/%d passed\n\n", tests_passed, tests_run);
}

static void test_sieve_context(void) {
    printf("== sieve_context ==\n");
    int prev_passed = tests_passed;
    int prev_run = tests_run;

    /* N = 15 = 3 * 5, factor base primes up to 20 */
    uint64_t N = 15;
    uint32_t fb[] = {2, 3, 5, 7, 11, 13};
    uint32_t n_primes = 6;

    sieve_context_t *ctx = sieve_context_create(N, fb, n_primes);
    ASSERT(ctx != NULL, "context created");
    ASSERT(ctx->N == 15, "N stored correctly");
    ASSERT(ctx->n_primes == 6, "n_primes correct");
    ASSERT(ctx->n_octahedra == 2, "6 primes = 2 octahedra");
    ASSERT(ctx->n_leftover == 0, "no leftover primes");
    ASSERT(ctx->sqrt_N == isqrt64(15) + 1, "sqrt_N correct");

    sieve_context_free(ctx);
    printf("  %d/%d passed\n\n", tests_passed - prev_passed, tests_run - prev_run);
}

static void test_trial_divide(void) {
    printf("== trial_divide ==\n");
    int prev_passed = tests_passed;
    int prev_run = tests_run;

    /* N = 91 = 7*13. a=10 -> Q = 100 - 91 = 9 = 3^2. Smooth if 3 in FB. */
    uint64_t N = 91;
    uint32_t fb[] = {2, 3, 5, 7, 11, 13};
    uint32_t n_primes = 6;

    sieve_context_t *ctx = sieve_context_create(N, fb, n_primes);

    smooth_relation_t rel;
    rel.exponents = calloc(n_primes, sizeof(uint32_t));

    int smooth = trial_divide(ctx, 10, &rel);
    ASSERT(smooth == 1, "a=10, Q=9=3^2 is smooth");
    ASSERT(rel.a == 10, "a stored");
    ASSERT(rel.Q == 9, "Q stored");
    ASSERT(rel.exponents[1] == 2, "3^2: exponent of prime[1]=3 is 2");

    /* a=11 -> Q = 121 - 91 = 30 = 2*3*5. Smooth. */
    memset(rel.exponents, 0, n_primes * sizeof(uint32_t));
    smooth = trial_divide(ctx, 11, &rel);
    ASSERT(smooth == 1, "a=11, Q=30=2*3*5 is smooth");
    ASSERT(rel.exponents[0] == 1, "2^1");
    ASSERT(rel.exponents[1] == 1, "3^1");
    ASSERT(rel.exponents[2] == 1, "5^1");

    free(rel.exponents);
    sieve_context_free(ctx);
    printf("  %d/%d passed\n\n", tests_passed - prev_passed, tests_run - prev_run);
}

static void test_sieve_block(void) {
    printf("== sieve_block ==\n");
    int prev_passed = tests_passed;
    int prev_run = tests_run;

    /* N = 1073 (prime, so we sieve Q=a^2-1073). Factor base up to ~50. */
    uint64_t N = 1073;
    uint32_t n_fb;
    uint32_t *fb = make_factor_base(N, 50, &n_fb);

    sieve_context_t *ctx = sieve_context_create(N, fb, n_fb);
    ASSERT(ctx != NULL, "context created for N=1073");

    uint64_t start_a = ctx->sqrt_N;
    float slack = log((float)fb[n_fb - 1]);

    sieve_candidates_t *sc = sieve_block(ctx, (int64_t)start_a, 1000, slack);
    ASSERT(sc != NULL, "sieve_block returned result");
    ASSERT(sc->n_candidates > 0, "found at least 1 candidate");

    /* Verify at least one candidate is actually smooth */
    int any_smooth = 0;
    smooth_relation_t rel;
    rel.exponents = calloc(n_fb, sizeof(uint32_t));
    for (uint32_t i = 0; i < sc->n_candidates && i < 20; i++) {
        int64_t a = (int64_t)start_a + sc->indices[i];
        memset(rel.exponents, 0, n_fb * sizeof(uint32_t));
        if (trial_divide(ctx, a, &rel))
            any_smooth = 1;
    }
    ASSERT(any_smooth, "at least one sieve candidate is truly smooth");

    free(rel.exponents);
    sieve_candidates_free(sc);
    sieve_context_free(ctx);
    free(fb);
    printf("  %d/%d passed\n\n", tests_passed - prev_passed, tests_run - prev_run);
}

static void test_pack_octahedral(void) {
    printf("== pack_octahedral_states ==\n");
    int prev_passed = tests_passed;
    int prev_run = tests_run;

    /* 6 primes = 2 octahedra. Exponents: [1,0,3, 2,1,0] */
    /* Octa 0: primes 0,1,2 -> odd mask = bit0(1 odd) | bit2(3 odd) = 0b101 = 5 */
    /* Octa 1: primes 3,4,5 -> odd mask = bit1(1 odd) = 0b010 = 2 */
    uint32_t exponents[] = {1, 0, 3, 2, 1, 0};
    uint8_t packed[1];  /* 2 octahedra -> 1 byte */
    memset(packed, 0, 1);

    pack_octahedral_states(exponents, 6, 2, packed);

    ASSERT(octa_get(packed, 0) == 5, "octa 0 state = 5 (primes 0,2 odd)");
    ASSERT(octa_get(packed, 1) == 2, "octa 1 state = 2 (prime 4 odd)");

    printf("  %d/%d passed\n\n", tests_passed - prev_passed, tests_run - prev_run);
}

static void test_geometric_search_singles(void) {
    printf("== geometric_search (singles) ==\n");
    int prev_passed = tests_passed;
    int prev_run = tests_run;

    /* 3 relations, 2 octahedra. Relation 0 has all-even exponents (zero state). */
    uint32_t n_oct = 2;
    uint32_t rb = octa_row_bytes(n_oct);
    uint8_t *states = calloc(3, rb);

    /* Relation 0: all zero (a "single") */
    octa_set(states + 0 * rb, 0, 0);
    octa_set(states + 0 * rb, 1, 0);

    /* Relation 1: non-zero */
    octa_set(states + 1 * rb, 0, 3);
    octa_set(states + 1 * rb, 1, 0);

    /* Relation 2: non-zero */
    octa_set(states + 2 * rb, 0, 0);
    octa_set(states + 2 * rb, 1, 5);

    dependency_list_t *dl = geometric_search(states, 3, n_oct, 4);
    ASSERT(dl != NULL, "search returned result");
    ASSERT(dl->n_deps >= 1, "found at least 1 dependency (the single)");

    /* The single should be relation 0 */
    int found_single = 0;
    for (uint32_t d = 0; d < dl->n_deps; d++) {
        if (dl->deps[d].n_indices == 1 && dl->deps[d].indices[0] == 0)
            found_single = 1;
    }
    ASSERT(found_single, "relation 0 identified as single");

    dependency_list_free(dl);
    free(states);
    printf("  %d/%d passed\n\n", tests_passed - prev_passed, tests_run - prev_run);
}

static void test_geometric_search_duplicates(void) {
    printf("== geometric_search (duplicates) ==\n");
    int prev_passed = tests_passed;
    int prev_run = tests_run;

    /* 4 relations, 2 octahedra. Relations 1 and 3 have identical states. */
    uint32_t n_oct = 2;
    uint32_t rb = octa_row_bytes(n_oct);
    uint8_t *states = calloc(4, rb);

    octa_set(states + 0 * rb, 0, 1); octa_set(states + 0 * rb, 1, 2);
    octa_set(states + 1 * rb, 0, 5); octa_set(states + 1 * rb, 1, 3);  /* dup */
    octa_set(states + 2 * rb, 0, 7); octa_set(states + 2 * rb, 1, 4);
    octa_set(states + 3 * rb, 0, 5); octa_set(states + 3 * rb, 1, 3);  /* dup */

    dependency_list_t *dl = geometric_search(states, 4, n_oct, 4);
    ASSERT(dl != NULL, "search returned result");
    ASSERT(dl->n_deps >= 1, "found at least 1 dependency");

    /* Should find dependency {1, 3} */
    int found_dup = 0;
    for (uint32_t d = 0; d < dl->n_deps; d++) {
        if (dl->deps[d].n_indices == 2) {
            uint32_t a = dl->deps[d].indices[0];
            uint32_t b = dl->deps[d].indices[1];
            if ((a == 1 && b == 3) || (a == 3 && b == 1))
                found_dup = 1;
        }
    }
    ASSERT(found_dup, "duplicate pair {1,3} found");

    dependency_list_free(dl);
    free(states);
    printf("  %d/%d passed\n\n", tests_passed - prev_passed, tests_run - prev_run);
}

static void test_gf2_fallback(void) {
    printf("== gf2_fallback ==\n");
    int prev_passed = tests_passed;
    int prev_run = tests_run;

    /*
     * 4 relations over 3 primes. Parity matrix:
     *   R0: 1 0 1   (primes 0,2 odd)
     *   R1: 0 1 1   (primes 1,2 odd)
     *   R2: 1 1 0   (primes 0,1 odd)
     *   R3: 1 0 1   (same as R0)
     *
     * Dependencies: {R0,R3} (identical rows), {R0,R1,R2} (XOR to zero).
     */
    uint64_t rows[4] = {
        0b101,  /* R0 */
        0b110,  /* R1 */
        0b011,  /* R2 */
        0b101,  /* R3 */
    };

    dependency_list_t *dl = gf2_fallback(rows, 4, 3);
    ASSERT(dl != NULL, "gf2 returned result");
    ASSERT(dl->n_deps >= 1, "found at least 1 dependency");

    printf("  Found %u dependencies\n", dl->n_deps);
    for (uint32_t d = 0; d < dl->n_deps; d++) {
        printf("    dep %u: {", d);
        for (uint32_t i = 0; i < dl->deps[d].n_indices; i++)
            printf("%s%u", i ? "," : "", dl->deps[d].indices[i]);
        printf("}\n");

        /* Verify: XOR of selected rows should be 0 */
        uint64_t xor_check = 0;
        for (uint32_t i = 0; i < dl->deps[d].n_indices; i++)
            xor_check ^= rows[dl->deps[d].indices[i]];
        ASSERT(xor_check == 0, "dependency XORs to zero");
    }

    dependency_list_free(dl);
    printf("  %d/%d passed\n\n", tests_passed - prev_passed, tests_run - prev_run);
}

/* ---------- main ---------- */

int main(void) {
    printf("Geometric NFS Core — C Library Smoke Tests\n");
    printf("==========================================\n\n");

    test_tonelli_shanks();
    test_sieve_context();
    test_trial_divide();
    test_sieve_block();
    test_pack_octahedral();
    test_geometric_search_singles();
    test_geometric_search_duplicates();
    test_gf2_fallback();

    printf("==========================================\n");
    printf("Total: %d/%d passed\n", tests_passed, tests_run);
    return (tests_passed == tests_run) ? 0 : 1;
}
