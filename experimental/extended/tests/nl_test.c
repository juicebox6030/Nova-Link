/**
 * @file nl_test.c
 * @brief Minimal unit test framework implementation.
 */
#include "nl_test.h"

#include <ctype.h>
#include <stdarg.h>
#include <stdlib.h>

int nl_test_failures;
int nl_test_total_failed;
int nl_test_total_run;

static const char *current_test = "?";

#define LOG_CAP 64
#define LOG_MSG_LEN 160

static struct {
    nl_log_level_t level;
    char msg[LOG_MSG_LEN];
} log_buf[LOG_CAP];
static int log_len;
static bool log_echo;
static bool log_installed;

static void capture_sink(nl_log_level_t level, const char *module, const char *msg,
                         void *user)
{
    (void)user;
    if (log_echo) {
        fprintf(stderr, "    [%s] %s: %s\n", nl_log_level_str(level), module, msg);
    }
    if (log_len < LOG_CAP) {
        log_buf[log_len].level = level;
        snprintf(log_buf[log_len].msg, LOG_MSG_LEN, "%s: %s", module, msg);
        log_len++;
    }
}

static void install_sink(void)
{
    if (log_installed) {
        return;
    }
    log_installed = true;
    const char *v = getenv("NL_TEST_VERBOSE");
    log_echo = v != NULL && v[0] != '\0' && v[0] != '0';
    nl_log_set_sink(capture_sink, NULL);
    nl_log_set_level(NL_LOG_DEBUG);
}

void nl_test_log_clear(void)
{
    log_len = 0;
}

int nl_test_log_count(nl_log_level_t level)
{
    int n = 0;
    for (int i = 0; i < log_len; i++) {
        if (log_buf[i].level >= level) {
            n++;
        }
    }
    return n;
}

bool nl_test_log_contains(nl_log_level_t level, const char *needle)
{
    for (int i = 0; i < log_len; i++) {
        if (log_buf[i].level >= level && strstr(log_buf[i].msg, needle) != NULL) {
            return true;
        }
    }
    return false;
}

void nl_test_log_echo(bool on)
{
    log_echo = on;
}

void nl_test_fail(const char *file, int line, const char *fmt, ...)
{
    va_list ap;
    if (nl_test_failures == 0) {
        fprintf(stderr, "FAIL %s\n", current_test);
    }
    nl_test_failures++;
    fprintf(stderr, "  %s:%d: ", file, line);
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fputc('\n', stderr);
}

void nl_test_run(const char *name, void (*fn)(void))
{
    install_sink();
    current_test = name;
    nl_test_failures = 0;
    nl_test_log_clear();
    fn();
    nl_test_total_run++;
    if (nl_test_failures != 0) {
        nl_test_total_failed++;
    } else {
        printf("ok   %s\n", name);
    }
}

int nl_test_finish(void)
{
    printf("%d/%d tests passed\n", nl_test_total_run - nl_test_total_failed,
           nl_test_total_run);
    return nl_test_total_failed == 0 ? 0 : 1;
}

size_t nl_test_hex(const char *hex, uint8_t *out, size_t cap)
{
    size_t n = 0;
    int hi = -1;
    for (; *hex != '\0'; hex++) {
        if (!isxdigit((unsigned char)*hex)) {
            continue;
        }
        int v = isdigit((unsigned char)*hex) ? *hex - '0'
                                             : (tolower((unsigned char)*hex) - 'a' + 10);
        if (hi < 0) {
            hi = v;
        } else {
            if (n < cap) {
                out[n] = (uint8_t)((hi << 4) | v);
            }
            n++;
            hi = -1;
        }
    }
    return n;
}
