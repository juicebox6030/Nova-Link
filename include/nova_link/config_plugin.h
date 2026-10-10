/* SPDX-License-Identifier: GPL-3.0-only */
#ifndef NOVA_LINK_CONFIG_PLUGIN_H
#define NOVA_LINK_CONFIG_PLUGIN_H

#include "nova_link/module.h"

/** @file config_plugin.h Strict, allocation-free startup INI configuration.
 * The caller supplies text, schemas and entry storage. No filesystem access,
 * dynamic loading or live reload is performed. Serialize with host operations.
 */
#define NL_CONFIG_NAME_MAX 31u
#define NL_CONFIG_VALUE_MAX 127u
#define NL_CONFIG_SECTION_MAX 16u
#define NL_CONFIG_FIELD_MAX 64u

typedef enum { NL_CONFIG_TEXT, NL_CONFIG_UINT, NL_CONFIG_BOOL, NL_CONFIG_ENUM } nl_config_type;
typedef struct {
    const char *key;
    nl_config_type type;
    bool required;
    uint64_t minimum, maximum; /**< Inclusive UINT bounds; ignored otherwise. */
    const char *const *choices; /**< ENUM: nonempty printable ASCII choices,
        * <= VALUE_MAX bytes, with no leading/trailing spaces or duplicates. */
    size_t choice_count;
} nl_config_field;
typedef struct {
    const char *name;
    bool required;
    const nl_config_field *fields;
    size_t field_count;
} nl_config_section;
typedef struct {
    char section[NL_CONFIG_NAME_MAX + 1u];
    char key[NL_CONFIG_NAME_MAX + 1u];
    char value[NL_CONFIG_VALUE_MAX + 1u];
} nl_config_entry;
typedef struct {
    nl_status status;
    size_t line; /**< One-based source line; zero for schema/global errors. */
    char section[NL_CONFIG_NAME_MAX + 1u];
    char key[NL_CONFIG_NAME_MAX + 1u];
} nl_config_error;
typedef struct {
    nl_config_entry *entries;
    size_t count;
    const nl_config_section *schema;
    size_t section_count;
    nl_host *owner;
    nl_plugin_id id;
    bool valid, active;
} nl_config_context;

/** Zero-initialize context before first use. Context, entries and optional error
 * storage must be disjoint from each other and from text/schema, including
 * borrowed metadata. Read-only schema metadata may share strings.
 * Validates schemas before text; at most SECTION_MAX sections, FIELD_MAX fields
 * per section and FIELD_MAX choices per ENUM field are supported.
 * Syntax: [section], key=value, blank lines, full-line # or ; comments. Names
 * contain ASCII letters/digits/underscore/hyphen/dot. Values are unquoted ASCII;
 * leading/trailing spaces/tabs are trimmed. Quotes/backslashes are literal
 * characters; no inline comments or escape interpretation. Empty values fail.
 * Reject unknown/duplicate sections or keys, missing required fields, embedded
 * NUL/control/non-ASCII bytes, oversized entries, signed/nondecimal/overflowing
 * UINTs and invalid BOOL/ENUM values. BOOL accepts only true or false.
 * Text need not be NUL-terminated; final line need not end with newline.
 * Active contexts return BUSY without changing context/storage. Any other
 * failure invalidates context; entry storage may contain partial parse output.
 * On success context borrows entries/schema, which must remain alive and
 * immutable while the parsed context/getters are used, including after stop.
 * Reparsing or discarding the stopped context ends that borrowing lifetime.
 * Input text may be released after parse. No callbacks run.
 * NULL error is permitted; error->line is zero for missing required values.
 */
nl_status nl_config_parse(nl_config_context *context, const char *text, size_t size,
                          nl_config_entry *entries, size_t capacity,
                          const nl_config_section *schema, size_t section_count,
                          nl_config_error *error);
/** Values are available after successful parse, before/during/after registration.
 * Pointer lifetime lasts until the next parse or entry storage modification.
 */
const char *nl_config_value(const nl_config_context *context,
                            const char *section, const char *key);
/** Output is unchanged on failure. Missing values return NOT_FOUND; wrong
 * schema types return ARGUMENT. ENUM/TEXT use nl_config_value().
 */
nl_status nl_config_uint(const nl_config_context *context, const char *section,
                         const char *key, uint64_t *value);
nl_status nl_config_bool(const nl_config_context *context, const char *section,
                         const char *key, bool *value);
/** Service named configuration, exposing context through module.service.
 * Consumers can require that name. Startup rejects unparsed/invalid contexts;
 * shutdown only unlocks reparsing, without clearing validated entries.
 */
nl_module nl_config_module(nl_config_context *context);

#endif
