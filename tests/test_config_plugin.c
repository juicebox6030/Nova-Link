/* SPDX-License-Identifier: GPL-3.0-only */
#include "test.h"
#include "nova_link/config_plugin.h"

static const char *const modes[] = {"fifo", "latest"};
static const nl_config_field host_fields[] = {
    {.key = "origin", .type = NL_CONFIG_UINT, .required = true, .minimum = 0, .maximum = 7},
    {.key = "enabled", .type = NL_CONFIG_BOOL, .required = true},
    {.key = "mode", .type = NL_CONFIG_ENUM, .required = true, .choices = modes, .choice_count = 2},
    {.key = "label", .type = NL_CONFIG_TEXT},
    {.key = "maximum", .type = NL_CONFIG_UINT, .maximum = UINT64_MAX}
};
static const nl_config_field diagnostic_fields[] = {
    {.key = "label", .type = NL_CONFIG_TEXT, .required = true}
};
static const nl_config_section schema[] = {
    {.name = "host", .required = true, .fields = host_fields,
     .field_count = sizeof(host_fields) / sizeof(host_fields[0])},
    {.name = "diagnostics", .fields = diagnostic_fields, .field_count = 1}
};
static const char valid_text[] = "[host]\norigin=3\nenabled=true\nmode=fifo\n";

static nl_status parse(nl_config_context *context, const char *text,
                       nl_config_entry *entries, size_t capacity,
                       nl_config_error *error)
{
    return nl_config_parse(context, text, strlen(text), entries, capacity,
                           schema, sizeof(schema) / sizeof(schema[0]), error);
}

static void happy_path_and_getters(void)
{
    nl_config_context context = {0};
    nl_config_entry entries[8] = {0};
    nl_config_error error = {0};
    uint64_t number = 99;
    bool boolean = false;
    char source[] = "# comment\r\n ; another\r\n\r\n [host] \r\n"
                    " origin = 0007 \r\n enabled = true\r\n mode = latest\r\n"
                    "label = a literal # and ; value\r\n"
                    "maximum=18446744073709551615";
    STATUS(nl_config_parse(&context, source, sizeof(source) - 1u, entries, 8,
                           schema, 2, &error), NL_OK);
    CHECK(context.valid && !context.active && context.count == 5u);
    CHECK(error.status == NL_OK);
    memset(source, 'X', sizeof(source)); /* Input is copied, not borrowed. */
    STATUS(nl_config_uint(&context, "host", "origin", &number), NL_OK);
    CHECK(number == 7u);
    STATUS(nl_config_uint(&context, "host", "maximum", &number), NL_OK);
    CHECK(number == UINT64_MAX);
    STATUS(nl_config_bool(&context, "host", "enabled", &boolean), NL_OK);
    CHECK(boolean);
    CHECK(strcmp(nl_config_value(&context, "host", "mode"), "latest") == 0);
    CHECK(strcmp(nl_config_value(&context, "host", "label"), "a literal # and ; value") == 0);
    CHECK(nl_config_value(&context, "diagnostics", "label") == NULL);
    number = 17;
    boolean = true;
    STATUS(nl_config_uint(&context, "host", "mode", &number), NL_ERR_ARGUMENT);
    CHECK(number == 17u);
    STATUS(nl_config_uint(&context, "host", "absent", &number), NL_ERR_NOT_FOUND);
    CHECK(number == 17u);
    STATUS(nl_config_bool(&context, "host", "origin", &boolean), NL_ERR_ARGUMENT);
    CHECK(boolean);
    STATUS(nl_config_bool(&context, "host", "absent", &boolean), NL_ERR_NOT_FOUND);
    CHECK(boolean);
    CHECK(nl_config_value(NULL, "host", "origin") == NULL);
    CHECK(nl_config_value(&context, NULL, "origin") == NULL);
    CHECK(nl_config_value(&context, "host", NULL) == NULL);
    CHECK(nl_config_uint(NULL, "host", "origin", &number) != NL_OK && number == 17u);
    CHECK(nl_config_uint(&context, "host", "origin", NULL) != NL_OK);
    CHECK(nl_config_bool(&context, "host", "enabled", NULL) != NL_OK);
    STATUS(parse(&context, "[host]\norigin=0\nenabled=false\nmode=fifo", entries, 8, NULL), NL_OK);
    STATUS(nl_config_bool(&context, "host", "enabled", &boolean), NL_OK);
    CHECK(!boolean);
    STATUS(nl_config_uint(&context, "host", "origin", &number), NL_OK);
    CHECK(number == 0u);
}

static void reject_text(const char *text, size_t size, size_t line)
{
    nl_config_context context = {0};
    nl_config_entry entries[8] = {0};
    nl_config_error error = {0};
    nl_status status;
    STATUS(parse(&context, valid_text, entries, 8, NULL), NL_OK);
    status = nl_config_parse(&context, text, size, entries, 8, schema, 2, &error);
    CHECK(status != NL_OK && !context.valid && !context.active);
    CHECK(error.status == status);
    if (line != SIZE_MAX) CHECK(error.line == line);
    CHECK(nl_config_value(&context, "host", "origin") == NULL);
}

static void text_failures(void)
{
    static const struct { const char *text; size_t line; } cases[] = {
        {"", 0},
        {"[host]\norigin=3\nenabled=true\n", 0},
        {"[host]\norigin=3\nenabled=true\nmode=fifo\n[diagnostics]\n", 0},
        {"[unknown]\n", 1},
        {"[host]\nother=1\n", 2},
        {"[host]\norigin=1\norigin=2\n", 3},
        {"[diagnostics]\n[diagnostics]\n", 2},
        {"origin=3\n", 1},
        {"[host] trailing\n", 1},
        {"[host\n", 1},
        {"[]\n", 1},
        {"[host]\n=3\n", 2},
        {"[host]\norigin\n", 2},
        {"[host]\norigin=-1\n", 2},
        {"[host]\norigin=+1\n", 2},
        {"[host]\norigin=0x1\n", 2},
        {"[host]\norigin=1e0\n", 2},
        {"[host]\norigin=1 2\n", 2},
        {"[host]\norigin=8\n", 2},
        {"[host]\norigin=1#comment\n", 2},
        {"[host]\norigin=\n", 2},
        {"[host]\nmaximum=18446744073709551616\n", 2},
        {"[host]\nmaximum=9999999999999999999999999999999999999999\n", 2},
        {"[host]\nenabled=True\n", 2},
        {"[host]\nenabled=1\n", 2},
        {"[host]\nenabled=false;comment\n", 2},
        {"[host]\nmode=FIFO\n", 2},
        {"[host]\nmode=\n", 2},
        {"[host]\nlabel=\n", 2},
        {"[host]\nlabel=a\tb\n", 2},
        {"[host]\nlabel=a\rb\n", 2},
        {"[ho st]\n", 1},
        {"[host]\nori gin=1\n", 2}
    };
    const char nul[] = "[host]\norigin=3\nenabled=true\nmode=fifo\0[evil]\n";
    const char high[] = "[host]\nlabel=\x80\n";
    const char control[] = "[host]\nlabel=\x01\n";
    const char comment_control[] = "# \x80\n";
    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i)
        reject_text(cases[i].text, strlen(cases[i].text), cases[i].line);
    reject_text(nul, sizeof(nul) - 1u, SIZE_MAX);
    reject_text(high, sizeof(high) - 1u, SIZE_MAX);
    reject_text(control, sizeof(control) - 1u, SIZE_MAX);
    reject_text(comment_control, sizeof(comment_control) - 1u, SIZE_MAX);
}

static void boundary_storage(void)
{
    nl_config_context context = {0};
    struct { unsigned before; nl_config_entry entries[1]; unsigned after; } guarded = {0};
    nl_config_error error = {0};
    const nl_config_field field = {.key = "abcdefghijklmnopqrstuvwxyz12345", .type = NL_CONFIG_TEXT,
                                   .required = true};
    const nl_config_section section = {.name = "abcdefghijklmnopqrstuvwxyz12345", .required = true,
                                       .fields = &field, .field_count = 1};
    char text[260];
    size_t prefix;
    nl_status status;
    guarded.before = 0x12345678u;
    guarded.after = 0x87654321u;
    prefix = (size_t)snprintf(text, sizeof(text), "[%s]\n%s=", section.name, field.key);
    CHECK(prefix + NL_CONFIG_VALUE_MAX + 2u < sizeof(text));
    memset(text + prefix, 'x', NL_CONFIG_VALUE_MAX);
    STATUS(nl_config_parse(&context, text, prefix + NL_CONFIG_VALUE_MAX,
                           guarded.entries, 1, &section, 1, NULL), NL_OK);
    CHECK(strlen(context.entries[0].section) == NL_CONFIG_NAME_MAX);
    CHECK(strlen(context.entries[0].key) == NL_CONFIG_NAME_MAX);
    CHECK(strlen(context.entries[0].value) == NL_CONFIG_VALUE_MAX);
    text[prefix + NL_CONFIG_VALUE_MAX] = 'x';
    status = nl_config_parse(&context, text, prefix + NL_CONFIG_VALUE_MAX + 1u,
                             guarded.entries, 1, &section, 1, &error);
    CHECK(status != NL_OK && !context.valid && error.status == status);
    CHECK(guarded.before == 0x12345678u && guarded.after == 0x87654321u);
    CHECK(parse(&context, valid_text, guarded.entries, 1, &error) != NL_OK);
    CHECK(!context.valid && guarded.before == 0x12345678u && guarded.after == 0x87654321u);
    CHECK(parse(&context, valid_text, guarded.entries, 0, &error) != NL_OK);
    CHECK(!context.valid && guarded.before == 0x12345678u && guarded.after == 0x87654321u);
    CHECK(nl_config_parse(NULL, valid_text, sizeof(valid_text) - 1u,
                          guarded.entries, 1, &section, 1, &error) != NL_OK);
    CHECK(nl_config_parse(&context, NULL, 1, guarded.entries, 1, &section, 1, &error) != NL_OK);
    CHECK(nl_config_parse(&context, valid_text, sizeof(valid_text) - 1u,
                          NULL, 1, &section, 1, &error) != NL_OK);
}

static void reject_schema(const nl_config_section *sections, size_t count)
{
    nl_config_context context = {0};
    nl_config_entry entries[8] = {0};
    nl_config_error error = {0};
    nl_status status = nl_config_parse(&context, valid_text, sizeof(valid_text) - 1u,
                                      entries, 8, sections, count, &error);
    CHECK(status != NL_OK && !context.valid && error.status == status && error.line == 0u);
}

static void schema_failures(void)
{
    nl_config_field fields[2] = {{.key = "x", .type = NL_CONFIG_UINT, .maximum = 10},
                                {.key = "x", .type = NL_CONFIG_TEXT}};
    nl_config_section sections[NL_CONFIG_SECTION_MAX + 1u] = {
        {.name = "host", .fields = fields, .field_count = 1},
        {.name = "host", .fields = fields, .field_count = 1}
    };
    reject_schema(NULL, 1);
    reject_schema(sections, NL_CONFIG_SECTION_MAX + 1u);
    reject_schema(sections, 2);
    sections[0].field_count = 2;
    reject_schema(sections, 1);
    sections[0].field_count = 1;
    fields[0].key = NULL;
    reject_schema(sections, 1);
    fields[0].key = "";
    reject_schema(sections, 1);
    fields[0].key = "bad key";
    reject_schema(sections, 1);
    fields[0].key = "abcdefghijklmnopqrstuvwxyz123456";
    reject_schema(sections, 1);
    fields[0].key = "x";
    fields[0].type = (nl_config_type)99;
    reject_schema(sections, 1);
    fields[0].type = NL_CONFIG_UINT;
    fields[0].minimum = 11;
    reject_schema(sections, 1);
    fields[0].minimum = 0;
    fields[0].type = NL_CONFIG_ENUM;
    fields[0].choice_count = 0;
    reject_schema(sections, 1);
    fields[0].choice_count = 1;
    fields[0].choices = NULL;
    reject_schema(sections, 1);
    {
        const char *const bad_choices[] = {NULL};
        fields[0].choices = bad_choices;
        reject_schema(sections, 1);
    }
    {
        const char *const bad_choices[] = {""};
        fields[0].choices = bad_choices;
        reject_schema(sections, 1);
    }
    {
        const char *const bad_choices[] = {"same", "same"};
        fields[0].choice_count = 2;
        fields[0].choices = bad_choices;
        reject_schema(sections, 1);
    }
    {
        char overlong[NL_CONFIG_VALUE_MAX + 2u];
        const char *bad_choices[1] = {overlong};
        memset(overlong, 'a', sizeof(overlong));
        overlong[sizeof(overlong) - 1u] = '\0';
        fields[0].choice_count = 1;
        fields[0].choices = bad_choices;
        reject_schema(sections, 1);
        bad_choices[0] = " leading";
        reject_schema(sections, 1);
        bad_choices[0] = "trailing ";
        reject_schema(sections, 1);
        bad_choices[0] = "a\tb";
        reject_schema(sections, 1);
        fields[0].choice_count = NL_CONFIG_FIELD_MAX + 1u;
        reject_schema(sections, 1);
    }
    fields[0].type = NL_CONFIG_TEXT;
    sections[0].field_count = NL_CONFIG_FIELD_MAX + 1u;
    reject_schema(sections, 1);
    sections[0].field_count = 1;
    sections[0].fields = NULL;
    reject_schema(sections, 1);
    sections[0].fields = fields;
    sections[0].name = "";
    reject_schema(sections, 1);
    sections[0].name = NULL;
    reject_schema(sections, 1);
    sections[0].name = "bad section";
    reject_schema(sections, 1);
    sections[0].name = "abcdefghijklmnopqrstuvwxyz123456";
    reject_schema(sections, 1);
}

typedef struct { nl_config_context *configuration; unsigned starts, stops; bool fail; } consumer_state;

static nl_status consumer_start(nl_host *host, nl_plugin_id id, void *opaque)
{
    consumer_state *state = opaque;
    nl_module_instance *configuration = nl_module_find(host, "configuration");
    uint64_t origin;
    (void)id;
    CHECK(configuration != NULL && configuration->module.service == state->configuration);
    CHECK(state->configuration->active && state->configuration->owner == host);
    STATUS(nl_config_uint(state->configuration, "host", "origin", &origin), NL_OK);
    CHECK(origin == 3u);
    ++state->starts;
    return state->fail ? NL_ERR_UNSUPPORTED : NL_OK;
}

static void consumer_stop(nl_host *host, nl_plugin_id id, void *opaque)
{
    consumer_state *state = opaque;
    (void)id;
    CHECK(nl_module_find(host, "configuration") != NULL && state->configuration->active);
    ++state->stops;
}

static void service_lifecycle(void)
{
    nl_host host, other;
    nl_config_context context = {0}, invalid = {0}, saved;
    nl_config_entry entries[8] = {0}, saved_entries[8], replacement[8] = {0};
    nl_config_error error = {0};
    nl_module configuration, application, null_module;
    nl_module_instance rejected = {0}, instances[2] = {0};
    const nl_module *manifest[2];
    static const char *const required[] = {"configuration"};
    consumer_state consumer = {.configuration = &context};
    STATUS(nl_host_init_plugins(&host, 1, 0), NL_OK);
    STATUS(nl_host_init_plugins(&other, 2, 0), NL_OK);
    null_module = nl_config_module(NULL);
    CHECK(nl_module_register(&host, &null_module, &rejected) != NL_OK);
    null_module = nl_config_module(&invalid);
    CHECK(nl_module_register(&host, &null_module, &rejected) != NL_OK);
    CHECK(!invalid.active);
    STATUS(parse(&context, valid_text, entries, 8, NULL), NL_OK);
    configuration = nl_config_module(&context);
    application = (nl_module){.name = "consumer", .version = "1", .kind = NL_MODULE_APPLICATION,
        .requires = required, .require_count = 1,
        .hooks = {.start = consumer_start, .stop = consumer_stop, .context = &consumer}};
    manifest[0] = &application; manifest[1] = &configuration;
    STATUS(nl_modules_start(&host, manifest, instances, 2), NL_OK);
    CHECK(context.active && consumer.starts == 1u);
    memcpy(&saved, &context, sizeof(context));
    memcpy(saved_entries, entries, sizeof(entries));
    STATUS(parse(&context, "bad", replacement, 8, &error), NL_ERR_BUSY);
    CHECK(memcmp(&context, &saved, sizeof(context)) == 0);
    CHECK(memcmp(entries, saved_entries, sizeof(entries)) == 0);
    CHECK(nl_module_register(&other, &configuration, &rejected) != NL_OK);
    CHECK(context.active && context.owner == &host);
    STATUS(nl_module_unregister(&instances[1]), NL_ERR_BUSY);
    STATUS(nl_modules_stop(instances, 2), NL_OK);
    CHECK(!context.active && context.valid && context.owner == NULL && consumer.stops == 1u);
    STATUS(parse(&context, valid_text, replacement, 8, NULL), NL_OK);
    CHECK(context.entries == replacement);
    consumer.fail = true;
    STATUS(nl_modules_start(&host, manifest, instances, 2), NL_ERR_UNSUPPORTED);
    CHECK(!context.active && context.valid && context.owner == NULL);
    CHECK(!instances[0].active && !instances[1].active && consumer.stops == 2u);
    STATUS(parse(&context, valid_text, entries, 8, NULL), NL_OK);
}

int main(void)
{
    happy_path_and_getters();
    text_failures();
    boundary_storage();
    schema_failures();
    service_lifecycle();
    puts("Configuration parser, bounds, schema validation and service ownership passed.");
    return EXIT_SUCCESS;
}
