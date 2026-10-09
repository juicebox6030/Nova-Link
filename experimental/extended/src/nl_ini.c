/**
 * @file nl_ini.c
 * @brief Tiny streaming INI parser.
 */
#include "nova_link/nl_ini.h"

#include <string.h>

/* Locale-independent and safe for negative char values, unlike <ctype.h>. */
static bool is_space(char c)
{
    return c == ' ' || c == '\t' || c == '\r' || c == '\v' || c == '\f';
}

static bool is_name_char(char c)
{
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
           c == '_' || c == '.' || c == '-';
}

static bool is_comment_start(char c)
{
    return c == ';' || c == '#';
}

static int fail(nl_ini_error_t *err, int line, int status, const char *msg)
{
    if (err != NULL) {
        err->line = line;
        err->msg = msg;
    }
    return status;
}

/** Trim whitespace in place; returns the start of the trimmed string. */
static char *trim(char *s)
{
    while (is_space(*s)) {
        s++;
    }
    size_t n = strlen(s);
    while (n > 0 && is_space(s[n - 1])) {
        s[--n] = '\0';
    }
    return s;
}

/** True if @p s is empty or only whitespace followed by a comment. */
static bool only_comment(const char *s)
{
    while (is_space(*s)) {
        s++;
    }
    return *s == '\0' || is_comment_start(*s);
}

static bool valid_name(const char *s)
{
    for (; *s != '\0'; s++) {
        if (!is_name_char(*s)) {
            return false;
        }
    }
    return true;
}

/* @p buf is a trimmed line starting with '['. */
static int parse_section(char *buf, char *section, int line, nl_ini_handler_t handler,
                         void *user, nl_ini_error_t *err)
{
    char *close = strchr(buf, ']');
    if (close == NULL) {
        return fail(err, line, NL_ERR_PROTO, "missing ']' in section header");
    }
    if (!only_comment(close + 1)) {
        return fail(err, line, NL_ERR_PROTO, "unexpected text after ']'");
    }
    *close = '\0';
    char *name = trim(buf + 1);
    if (*name == '\0') {
        return fail(err, line, NL_ERR_PROTO, "empty section name");
    }
    if (strlen(name) > NL_INI_MAX_SECTION) {
        return fail(err, line, NL_ERR_SIZE, "section name too long");
    }
    if (!valid_name(name)) {
        return fail(err, line, NL_ERR_PROTO, "invalid character in section name");
    }
    memcpy(section, name, strlen(name) + 1);
    int rc = handler(user, section, NULL, NULL, line);
    if (rc != NL_OK) {
        return fail(err, line, rc, "stopped by handler");
    }
    return NL_OK;
}

/* @p buf is a trimmed, non-empty, non-comment line not starting with '['. */
static int parse_pair(char *buf, const char *section, int line,
                      nl_ini_handler_t handler, void *user, nl_ini_error_t *err)
{
    char *eq = strchr(buf, '=');
    if (eq == NULL) {
        return fail(err, line, NL_ERR_PROTO, "expected 'key = value'");
    }
    *eq = '\0';
    char *key = trim(buf);
    if (*key == '\0') {
        return fail(err, line, NL_ERR_PROTO, "missing key before '='");
    }
    if (strlen(key) > NL_INI_MAX_KEY) {
        return fail(err, line, NL_ERR_SIZE, "key too long");
    }
    if (!valid_name(key)) {
        return fail(err, line, NL_ERR_PROTO, "invalid character in key");
    }

    char *value = eq + 1;
    while (is_space(*value)) {
        value++;
    }
    if (*value == '"') {
        value++;
        char *close = strchr(value, '"');
        if (close == NULL) {
            return fail(err, line, NL_ERR_PROTO, "unterminated quoted value");
        }
        if (!only_comment(close + 1)) {
            return fail(err, line, NL_ERR_PROTO, "unexpected text after quoted value");
        }
        *close = '\0';
    } else {
        for (char *p = value; *p != '\0'; p++) {
            if (is_comment_start(*p) && (p == value || is_space(p[-1]))) {
                *p = '\0';
                break;
            }
        }
        value = trim(value);
    }

    int rc = handler(user, section, key, value, line);
    if (rc != NL_OK) {
        return fail(err, line, rc, "stopped by handler");
    }
    return NL_OK;
}

int nl_ini_parse(const char *text, size_t len, nl_ini_handler_t handler, void *user,
                 nl_ini_error_t *err)
{
    char section[NL_INI_MAX_SECTION + 1];
    char buf[NL_INI_MAX_LINE + 1];

    if (err != NULL) {
        err->line = 0;
        err->msg = "";
    }
    if ((text == NULL && len != 0) || handler == NULL) {
        return fail(err, 0, NL_ERR_ARG, "invalid argument");
    }
    if (text == NULL) {
        return NL_OK;
    }
    const char *nul = memchr(text, '\0', len);
    size_t end = nul != NULL ? (size_t)(nul - text) : len;
    size_t pos = 0;
    if (end >= 3 && (uint8_t)text[0] == 0xEFu && (uint8_t)text[1] == 0xBBu &&
        (uint8_t)text[2] == 0xBFu) {
        pos = 3;
    }

    section[0] = '\0';
    int line = 0;
    while (pos < end) {
        line++;
        size_t start = pos;
        const char *nl = memchr(text + pos, '\n', end - pos);
        size_t stop = nl != NULL ? (size_t)(nl - text) : end;
        pos = nl != NULL ? stop + 1 : end;

        while (start < stop && is_space(text[start])) {
            start++;
        }
        while (stop > start && is_space(text[stop - 1])) {
            stop--;
        }
        if (start == stop || is_comment_start(text[start])) {
            continue;
        }
        if (stop - start > NL_INI_MAX_LINE) {
            return fail(err, line, NL_ERR_SIZE, "line too long");
        }
        memcpy(buf, text + start, stop - start);
        buf[stop - start] = '\0';

        int rc = buf[0] == '['
                     ? parse_section(buf, section, line, handler, user, err)
                     : parse_pair(buf, section, line, handler, user, err);
        if (rc != NL_OK) {
            return rc;
        }
    }
    return NL_OK;
}
