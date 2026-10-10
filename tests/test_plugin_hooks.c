/* Builds host.c with sandbox hooks defined (as an MPU port would) and checks
 * that every plugin callback runs inside a balanced ENTER/EXIT for its slot.
 * The library's own host.o is not linked: this unit defines every nl_host_*.
 */
static void hook_enter(unsigned index);
static void hook_exit(unsigned index);
#define NL_PLUGIN_ENTER(host, index) ((void)(host), hook_enter(index))
#define NL_PLUGIN_EXIT(host, index) ((void)(host), hook_exit(index))
#include "test.h"

static unsigned hook_enters, hook_exits, hook_depth;
static int hook_slot = -1;
static void hook_enter(unsigned index) { ++hook_enters; ++hook_depth; hook_slot = (int)index; }
static void hook_exit(unsigned index)
{
    CHECK(hook_depth == 1u && hook_slot == (int)index);
    ++hook_exits;
    --hook_depth;
    hook_slot = -1;
}
#include "../src/host.c"

static unsigned calls;
static void inside(nl_plugin_id id)
{
    CHECK(hook_depth == 1u && hook_slot == (int)(id & 0xFFu));
    ++calls;
}
static nl_status start(nl_host *host, nl_plugin_id id, void *context)
{
    (void)host;
    inside(id);
    return context != NULL ? NL_ERR_FORMAT : nl_host_claim(host, id, 2, NL_ZONE_READ_ONLY);
}
static void stop(nl_host *host, nl_plugin_id id, void *context) { (void)host; (void)context; inside(id); }
static void receive(nl_host *host, nl_plugin_id id, const nl_fragment *value, void *context)
{
    (void)host; (void)value; (void)context;
    inside(id);
}
static void tick(nl_host *host, nl_plugin_id id, uint64_t now_us, void *context)
{
    (void)host; (void)now_us; (void)context;
    inside(id);
}
static nl_status send_ok(void *context, const nl_fragment *value) { (void)context; (void)value; return NL_OK; }

int main(void)
{
    static int fail = 1;
    nl_host host;
    nl_plugin plugin = {start, receive, tick, stop, NULL}, failing = {start, receive, tick, stop, &fail};
    nl_plugin_id a, b, unused = NL_PLUGIN_ID_NONE;
    nl_fragment value = fragment(1, 2, 0);
    STATUS(nl_host_init(&host, 0, 1000000u, send_ok, NULL), NL_OK);
    STATUS(nl_host_register(&host, &plugin, &a), NL_OK);                 /* start */
    STATUS(nl_host_register(&host, &failing, &unused), NL_ERR_FORMAT);   /* start + stop */
    STATUS(nl_host_register(&host, &plugin, &b), NL_OK);                 /* start */
    STATUS(nl_host_receive(&host, &value, 10), NL_OK);                   /* 2 x receive */
    STATUS(nl_host_tick(&host, 20), NL_OK);                              /* 2 x tick */
    STATUS(nl_host_unregister(&host, a), NL_OK);                         /* stop */
    STATUS(nl_host_unregister(&host, b), NL_OK);                         /* stop */
    CHECK(calls == 10u && hook_enters == calls && hook_exits == calls && hook_depth == 0u);
    puts("plugin hooks: every start/receive/tick/stop ran inside a balanced sandbox hook");
    return EXIT_SUCCESS;
}
