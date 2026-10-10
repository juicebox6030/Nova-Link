/* SPDX-License-Identifier: GPL-3.0-only */
#include "nova_link/config_plugin.h"
#include <string.h>

static bool name_character(unsigned char c)
{
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
           (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.';
}

static bool valid_name(const char *name)
{
    size_t i;
    if (name == NULL || name[0] == '\0') return false;
    for (i = 0; i <= NL_CONFIG_NAME_MAX; ++i) {
        if (name[i] == '\0') return true;
        if (!name_character((unsigned char)name[i])) return false;
    }
    return false;
}

static bool valid_choice(const char *value)
{
    size_t i;
    if (value == NULL || value[0] == '\0') return false;
    for (i = 0; i <= NL_CONFIG_VALUE_MAX; ++i) {
        unsigned char c = (unsigned char)value[i];
        if (c == 0u) return value[0] != ' ' && value[i - 1u] != ' ';
        if (c < 32u || c > 126u) return false;
    }
    return false;
}

static void copy_name(char *output, const char *name)
{
    if (name == NULL) output[0] = '\0';
    else {
        size_t length = strlen(name);
        if (length > NL_CONFIG_NAME_MAX) length = NL_CONFIG_NAME_MAX;
        memcpy(output, name, length);
        output[length] = '\0';
    }
}

static nl_status fail(nl_config_error *error, nl_status status, size_t line,
                      const char *section, const char *key)
{
    if (error != NULL) {
        error->status = status;
        error->line = line;
        copy_name(error->section, section);
        copy_name(error->key, key);
    }
    return status;
}

static nl_status validate_schema(const nl_config_section *schema, size_t count,
                                 nl_config_error *error)
{
    size_t i, j, k, n;
    if (count > NL_CONFIG_SECTION_MAX || (count != 0u && schema == NULL))
        return fail(error, NL_ERR_ARGUMENT, 0, NULL, NULL);
    for (i = 0; i < count; ++i) {
        const nl_config_section *section = &schema[i];
        if (!valid_name(section->name) || section->field_count > NL_CONFIG_FIELD_MAX ||
            (section->field_count != 0u && section->fields == NULL))
            return fail(error, NL_ERR_ARGUMENT, 0, NULL, NULL);
        for (j = 0; j < i; ++j)
            if (strcmp(section->name, schema[j].name) == 0)
                return fail(error, NL_ERR_ARGUMENT, 0, section->name, NULL);
        for (j = 0; j < section->field_count; ++j) {
            const nl_config_field *field = &section->fields[j];
            if (!valid_name(field->key) || field->type < NL_CONFIG_TEXT ||
                field->type > NL_CONFIG_ENUM)
                return fail(error, NL_ERR_ARGUMENT, 0, section->name, NULL);
            for (k = 0; k < j; ++k)
                if (strcmp(field->key, section->fields[k].key) == 0)
                    return fail(error, NL_ERR_ARGUMENT, 0, section->name, field->key);
            if (field->type == NL_CONFIG_UINT && field->minimum > field->maximum)
                return fail(error, NL_ERR_ARGUMENT, 0, section->name, field->key);
            if (field->type == NL_CONFIG_ENUM) {
                if (field->choices == NULL || field->choice_count == 0u ||
                    field->choice_count > NL_CONFIG_FIELD_MAX)
                    return fail(error, NL_ERR_ARGUMENT, 0, section->name, field->key);
                for (k = 0; k < field->choice_count; ++k) {
                    if (!valid_choice(field->choices[k]))
                        return fail(error, NL_ERR_ARGUMENT, 0, section->name, field->key);
                    for (n = 0; n < k; ++n)
                        if (strcmp(field->choices[k], field->choices[n]) == 0)
                            return fail(error, NL_ERR_ARGUMENT, 0, section->name, field->key);
                }
            }
        }
    }
    return NL_OK;
}

static bool parse_uint(const char *text, uint64_t *output)
{
    uint64_t value = 0;
    size_t i;
    if (text[0] == '\0') return false;
    for (i = 0; text[i] != '\0'; ++i) {
        unsigned char c = (unsigned char)text[i];
        uint64_t digit;
        if (c < '0' || c > '9') return false;
        digit = (uint64_t)(c - (unsigned char)'0');
        if (value > (UINT64_MAX - digit) / 10u) return false;
        value = value * 10u + digit;
    }
    *output = value;
    return true;
}

static const nl_config_field *find_field(const nl_config_section *section,
                                         const char *key)
{
    size_t i;
    for (i = 0; i < section->field_count; ++i)
        if (strcmp(section->fields[i].key, key) == 0) return &section->fields[i];
    return NULL;
}

static bool valid_value(const nl_config_field *field, const char *value)
{
    uint64_t number;
    size_t i;
    if (value[0] == '\0') return false;
    switch (field->type) {
    case NL_CONFIG_TEXT: return true;
    case NL_CONFIG_UINT:
        return parse_uint(value, &number) && number >= field->minimum && number <= field->maximum;
    case NL_CONFIG_BOOL: return strcmp(value, "true") == 0 || strcmp(value, "false") == 0;
    case NL_CONFIG_ENUM:
        for (i = 0; i < field->choice_count; ++i)
            if (strcmp(value, field->choices[i]) == 0) return true;
        return false;
    }
    return false;
}

static bool space(char c) { return c == ' ' || c == '\t'; }

nl_status nl_config_parse(nl_config_context *context, const char *text, size_t size,
                          nl_config_entry *entries, size_t capacity,
                          const nl_config_section *schema, size_t section_count,
                          nl_config_error *error)
{
    bool declared[NL_CONFIG_SECTION_MAX] = {false};
    size_t offset = 0, line = 0, current = SIZE_MAX, count = 0, i, j;
    nl_status status;
    if (error != NULL) memset(error, 0, sizeof(*error));
    if (context == NULL) return fail(error, NL_ERR_ARGUMENT, 0, NULL, NULL);
    if (context->active) return fail(error, NL_ERR_BUSY, 0, NULL, NULL);
    memset(context, 0, sizeof(*context));
    context->id = NL_PLUGIN_ID_NONE;
    if ((size != 0u && text == NULL) || (capacity != 0u && entries == NULL))
        return fail(error, NL_ERR_ARGUMENT, 0, NULL, NULL);
    status = validate_schema(schema, section_count, error);
    if (status != NL_OK) return status;
    while (offset < size) {
        size_t begin = offset, end, equal;
        char name[NL_CONFIG_NAME_MAX + 1u], value[NL_CONFIG_VALUE_MAX + 1u];
        const nl_config_field *field;
        ++line;
        while (offset < size && text[offset] != '\n') {
            unsigned char c = (unsigned char)text[offset];
            if ((c < 32u && c != '\t' && c != '\r') || c > 126u)
                return fail(error, NL_ERR_FORMAT, line,
                            current == SIZE_MAX ? NULL : schema[current].name, NULL);
            ++offset;
        }
        end = offset;
        if (offset < size) ++offset;
        if (end > begin && text[end - 1u] == '\r') --end;
        for (i = begin; i < end; ++i)
            if (text[i] == '\r') return fail(error, NL_ERR_FORMAT, line, NULL, NULL);
        while (begin < end && space(text[begin])) ++begin;
        while (end > begin && space(text[end - 1u])) --end;
        if (begin == end || text[begin] == '#' || text[begin] == ';') continue;
        if (text[begin] == '[') {
            size_t length;
            if (end - begin < 3u || text[end - 1u] != ']')
                return fail(error, NL_ERR_FORMAT, line, NULL, NULL);
            length = end - begin - 2u;
            if (length > NL_CONFIG_NAME_MAX) return fail(error, NL_ERR_SIZE, line, NULL, NULL);
            memcpy(name, text + begin + 1u, length); name[length] = '\0';
            if (!valid_name(name)) return fail(error, NL_ERR_FORMAT, line, name, NULL);
            for (i = 0; i < section_count; ++i)
                if (strcmp(name, schema[i].name) == 0) break;
            if (i == section_count) return fail(error, NL_ERR_NOT_FOUND, line, name, NULL);
            if (declared[i]) return fail(error, NL_ERR_DUPLICATE, line, name, NULL);
            declared[i] = true; current = i;
            continue;
        }
        if (current == SIZE_MAX) return fail(error, NL_ERR_FORMAT, line, NULL, NULL);
        for (equal = begin; equal < end && text[equal] != '='; ++equal) {}
        if (equal == end) return fail(error, NL_ERR_FORMAT, line, schema[current].name, NULL);
        i = equal;
        while (i > begin && space(text[i - 1u])) --i;
        if (i - begin > NL_CONFIG_NAME_MAX) return fail(error, NL_ERR_SIZE, line, schema[current].name, NULL);
        memcpy(name, text + begin, i - begin); name[i - begin] = '\0';
        if (!valid_name(name)) return fail(error, NL_ERR_FORMAT, line, schema[current].name, name);
        field = find_field(&schema[current], name);
        if (field == NULL) return fail(error, NL_ERR_NOT_FOUND, line, schema[current].name, name);
        for (i = 0; i < count; ++i)
            if (strcmp(entries[i].section, schema[current].name) == 0 && strcmp(entries[i].key, name) == 0)
                return fail(error, NL_ERR_DUPLICATE, line, schema[current].name, name);
        begin = equal + 1u;
        while (begin < end && space(text[begin])) ++begin;
        if (end - begin > NL_CONFIG_VALUE_MAX)
            return fail(error, NL_ERR_SIZE, line, schema[current].name, name);
        for (i = begin; i < end; ++i)
            if ((unsigned char)text[i] < 32u)
                return fail(error, NL_ERR_FORMAT, line, schema[current].name, name);
        memcpy(value, text + begin, end - begin); value[end - begin] = '\0';
        if (!valid_value(field, value)) return fail(error, NL_ERR_FORMAT, line, schema[current].name, name);
        if (count == capacity) return fail(error, NL_ERR_FULL, line, schema[current].name, name);
        copy_name(entries[count].section, schema[current].name);
        copy_name(entries[count].key, name);
        memcpy(entries[count].value, value, end - begin + 1u);
        ++count;
    }
    for (i = 0; i < section_count; ++i) {
        if (!declared[i]) {
            if (schema[i].required) return fail(error, NL_ERR_NOT_FOUND, 0, schema[i].name, NULL);
            continue;
        }
        for (j = 0; j < schema[i].field_count; ++j) {
            size_t k;
            if (!schema[i].fields[j].required) continue;
            for (k = 0; k < count; ++k)
                if (strcmp(entries[k].section, schema[i].name) == 0 &&
                    strcmp(entries[k].key, schema[i].fields[j].key) == 0) break;
            if (k == count) return fail(error, NL_ERR_NOT_FOUND, 0, schema[i].name, schema[i].fields[j].key);
        }
    }
    context->entries = entries; context->count = count;
    context->schema = schema; context->section_count = section_count; context->valid = true;
    return NL_OK;
}

const char *nl_config_value(const nl_config_context *context, const char *section, const char *key)
{
    size_t i;
    if (context == NULL || !context->valid || section == NULL || key == NULL) return NULL;
    for (i = 0; i < context->count; ++i)
        if (strcmp(context->entries[i].section, section) == 0 && strcmp(context->entries[i].key, key) == 0)
            return context->entries[i].value;
    return NULL;
}

static const nl_config_field *context_field(const nl_config_context *context, const char *section, const char *key)
{
    size_t i;
    if (context == NULL || !context->valid || section == NULL || key == NULL) return NULL;
    for (i = 0; i < context->section_count; ++i)
        if (strcmp(context->schema[i].name, section) == 0) return find_field(&context->schema[i], key);
    return NULL;
}

nl_status nl_config_uint(const nl_config_context *context, const char *section, const char *key, uint64_t *value)
{
    const char *text;
    const nl_config_field *field;
    uint64_t parsed;
    if (context == NULL || !context->valid || section == NULL || key == NULL || value == NULL) return NL_ERR_ARGUMENT;
    field = context_field(context, section, key);
    if (field != NULL && field->type != NL_CONFIG_UINT) return NL_ERR_ARGUMENT;
    text = nl_config_value(context, section, key);
    if (text == NULL) return NL_ERR_NOT_FOUND;
    if (field == NULL || !valid_value(field, text) || !parse_uint(text, &parsed)) return NL_ERR_FORMAT;
    *value = parsed;
    return NL_OK;
}

nl_status nl_config_bool(const nl_config_context *context, const char *section, const char *key, bool *value)
{
    const char *text;
    const nl_config_field *field;
    if (context == NULL || !context->valid || section == NULL || key == NULL || value == NULL) return NL_ERR_ARGUMENT;
    field = context_field(context, section, key);
    if (field != NULL && field->type != NL_CONFIG_BOOL) return NL_ERR_ARGUMENT;
    text = nl_config_value(context, section, key);
    if (text == NULL) return NL_ERR_NOT_FOUND;
    if (field == NULL || !valid_value(field, text)) return NL_ERR_FORMAT;
    *value = strcmp(text, "true") == 0;
    return NL_OK;
}

static nl_status start(nl_host *host, nl_plugin_id plugin, void *context)
{
    nl_config_context *config = context;
    if (config == NULL || !config->valid) return NL_ERR_ARGUMENT;
    if (config->active) return NL_ERR_BUSY;
    config->owner = host; config->id = plugin; config->active = true;
    return NL_OK;
}

static void stop(nl_host *host, nl_plugin_id plugin, void *context)
{
    nl_config_context *config = context;
    if (config != NULL && config->active && config->owner == host && config->id == plugin) {
        config->owner = NULL; config->id = NL_PLUGIN_ID_NONE; config->active = false;
    }
}

nl_module nl_config_module(nl_config_context *context)
{
    nl_module module = {.name = "configuration", .version = "1", .kind = NL_MODULE_SERVICE,
        .service = context, .hooks = {.start = start, .stop = stop, .context = context}};
    return module;
}
