/**
 * @file nl_test.h
 * @brief Minimal unit test framework (no dependencies).
 *
 * Each test file defines static test functions and a main() that runs them:
 *
 * @code
 * static void test_something(void) { CHECK_EQ(1 + 1, 2); }
 * int main(void) { RUN(test_something); return nl_test_finish(); }
 * @endcode
 *
 * A failed CHECK prints file:line and marks the current test failed but
 * keeps going, so one run reports every broken assertion.
 */
#ifndef NL_TEST_H
#define NL_TEST_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "nova_link/nl_log.h"

extern int nl_test_failures;      /**< Failed checks in the current test. */
extern int nl_test_total_failed;  /**< Failed tests so far. */
extern int nl_test_total_run;

void nl_test_fail(const char *file, int line, const char *fmt, ...)
#if defined(__GNUC__)
    __attribute__((format(printf, 3, 4)))
#endif
    ;

void nl_test_run(const char *name, void (*fn)(void));
int nl_test_finish(void);

#define RUN(fn) nl_test_run(#fn, fn)

#define CHECK(cond)                                                            \
    do {                                                                       \
        if (!(cond)) {                                                         \
            nl_test_fail(__FILE__, __LINE__, "CHECK(%s)", #cond);              \
        }                                                                      \
    } while (0)

#define CHECK_EQ(a, b)                                                         \
    do {                                                                       \
        long long nl_a_ = (long long)(a), nl_b_ = (long long)(b);              \
        if (nl_a_ != nl_b_) {                                                  \
            nl_test_fail(__FILE__, __LINE__, "%s == %s (%lld != %lld)", #a, #b, \
                         nl_a_, nl_b_);                                        \
        }                                                                      \
    } while (0)

#define CHECK_MEM(a, b, n)                                                     \
    do {                                                                       \
        if (memcmp((a), (b), (n)) != 0) {                                      \
            nl_test_fail(__FILE__, __LINE__, "memcmp(%s, %s, %s)", #a, #b, #n); \
        }                                                                      \
    } while (0)

#define CHECK_STR(a, b)                                                        \
    do {                                                                       \
        const char *nl_a_ = (a), *nl_b_ = (b);                                 \
        if (strcmp(nl_a_, nl_b_) != 0) {                                       \
            nl_test_fail(__FILE__, __LINE__, "%s == %s (\"%s\" != \"%s\")", #a, \
                         #b, nl_a_, nl_b_);                                    \
        }                                                                      \
    } while (0)

/* ---- Log capture ------------------------------------------------------- */

/** Clear captured log messages. Called automatically before each test. */
void nl_test_log_clear(void);
/** Number of captured messages at or above @p level. */
int nl_test_log_count(nl_log_level_t level);
/** True if a message at or above @p level contains @p needle. */
bool nl_test_log_contains(nl_log_level_t level, const char *needle);
/** Echo captured messages to stderr as they arrive (NL_TEST_VERBOSE=1). */
void nl_test_log_echo(bool on);

/** Parse a hex string ("aa 01 00 ff" or "aa0100ff") into @p out. */
size_t nl_test_hex(const char *hex, uint8_t *out, size_t cap);

#endif /* NL_TEST_H */
