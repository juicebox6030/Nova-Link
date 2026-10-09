/**
 * @file nl_ini.h
 * @brief Tiny streaming INI parser (no allocation, memory buffer input).
 *
 * The parser walks a text buffer line by line and calls a handler for every
 * section header and every `key = value` pair. Nothing is stored except the
 * current section name, so memory use is two small stack buffers bounded by
 * NL_INI_MAX_LINE and NL_INI_MAX_SECTION. It works on firmware without a
 * filesystem: hand it a string compiled into flash or a buffer received over
 * the network.
 *
 * Syntax:
 *
 * @code
 * ; full-line comment          # also a full-line comment
 * [section]                    ; names: letters, digits, '_', '.', '-'
 * [zone.3]
 * key = value                  ; inline comment (needs whitespace before it)
 * name = "quoted; # kept"      ; quotes keep ';', '#' and edge spaces
 * empty =
 * @endcode
 *
 * - Lines end with LF or CRLF. Leading/trailing whitespace is trimmed from
 *   lines, section names, keys, and values.
 * - Inside an unquoted value, `;` or `#` starts a comment only when it is
 *   preceded by whitespace (or is the first character), so `a#b` is a value.
 * - A value that starts with `"` runs to the next `"`; there are no escape
 *   sequences. Only whitespace or a comment may follow the closing quote.
 * - Names are case-sensitive. Keys before the first section header are
 *   reported with section "".
 * - A UTF-8 byte order mark at the start of the buffer is skipped.
 * - Parsing stops at @p len bytes or at the first NUL byte, whichever comes
 *   first, so both strlen() and sizeof() of a string literal work.
 * - Comment and blank lines may be any length; other lines are limited to
 *   NL_INI_MAX_LINE characters after trimming.
 *
 * Parsing stops at the first error; its 1-based line number and a static
 * message are reported through nl_ini_error_t.
 */
#ifndef NL_INI_H
#define NL_INI_H

#include "nl_common.h"

#ifdef __cplusplus
extern "C" {
#endif

/** @name Limits (override with compiler defines, like nl_config.h) */
/**@{*/
/** Longest non-comment line in characters, after trimming whitespace. */
#ifndef NL_INI_MAX_LINE
#define NL_INI_MAX_LINE 128
#endif

/** Longest section name in characters (without the brackets). */
#ifndef NL_INI_MAX_SECTION
#define NL_INI_MAX_SECTION 32
#endif

/** Longest key in characters. */
#ifndef NL_INI_MAX_KEY
#define NL_INI_MAX_KEY 32
#endif
/**@}*/

/**
 * Called for every section header and every key/value pair.
 *
 * On a section header @p key and @p value are NULL and @p section is the new
 * name; this lets the handler reject unknown sections on their own line,
 * even when they contain no keys. All strings are NUL-terminated and only
 * valid during the call.
 *
 * @param user     Pointer passed to nl_ini_parse().
 * @param section  Current section ("" before the first header).
 * @param key      Key, or NULL for a section header.
 * @param value    Value (possibly ""), or NULL for a section header.
 * @param line     1-based line number.
 * @return NL_OK to continue; any other value stops parsing and is returned
 *         from nl_ini_parse().
 */
typedef int (*nl_ini_handler_t)(void *user, const char *section, const char *key,
                                const char *value, int line);

/** Where and why parsing stopped. */
typedef struct {
    int line;        /**< 1-based line of the first error; 0 if none. */
    const char *msg; /**< Static description; "" if none. */
} nl_ini_error_t;

/**
 * Parse an INI buffer.
 * @param text     Buffer (need not be NUL-terminated); may be NULL if @p len is 0.
 * @param len      Buffer length in bytes.
 * @param handler  Called per section header and per key.
 * @param user     Passed through to @p handler.
 * @param err      Optional; receives the first error's line and message.
 * @return NL_OK, NL_ERR_ARG (bad arguments), NL_ERR_SIZE (line, section, or
 *         key too long), NL_ERR_PROTO (syntax error), or the handler's
 *         non-zero return value (err->msg is then "stopped by handler").
 */
int nl_ini_parse(const char *text, size_t len, nl_ini_handler_t handler, void *user,
                 nl_ini_error_t *err);

#ifdef __cplusplus
}
#endif

#endif /* NL_INI_H */
