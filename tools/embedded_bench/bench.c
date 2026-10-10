/* Instruction counts for sealing/opening on a Cortex-M4, run under
 * `qemu-system-arm -M mps2-an386 -icount shift=0` (1 ns of virtual time per
 * instruction). The CMSDK timer runs at 25 MHz, so one tick is 40 instructions;
 * averaging over many runs gives counts exact to well under one instruction.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nova_link/secure.h"

#define TIMER_CTRL (*(volatile uint32_t *)0x40000000u)
#define TIMER_VALUE (*(volatile uint32_t *)0x40000004u)
#define TIMER_RELOAD (*(volatile uint32_t *)0x40000008u)
#define RUNS 2000u
#define INSNS_PER_TICK 40u

extern uint32_t __etext, __data_start__, __data_end__, __bss_start__, __bss_end__, __stack;
extern void initialise_monitor_handles(void);
int main(void);
void reset(void);
static void hang(void) { for (;;) {} }
__attribute__((section(".vectors"), used)) static void (*const vectors[16])(void) = {
    (void (*)(void))&__stack, reset, hang, hang, hang, hang, hang};

void reset(void)
{
    uint32_t *source = &__etext, *target = &__data_start__;
    while (target < &__data_end__) *target++ = *source++;
    for (target = &__bss_start__; target < &__bss_end__; ++target) *target = 0;
    initialise_monitor_handles(); /* rdimon semihosting stdio */
    exit(main());
}

static uint32_t now(void) { return TIMER_VALUE; } /* counts down */

static unsigned per_op(uint32_t start, uint32_t stop) { return (unsigned)((start - stop) * INSNS_PER_TICK / RUNS); }

static void measure(nl_secure_mode mode, uint8_t payload)
{
    static const uint8_t key[16] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16};
    static nl_secure tx, rx;
    nl_fragment value = {0}, opened;
    uint8_t air[NL_SECURE_AIR_MAX], plain[NL_FRAGMENT_MAX];
    size_t size = 0, plain_size = 0;
    uint32_t counter, start, i;
    unsigned seal, open, encode, decode;
    value.origin = 1;
    value.zone = 2;
    value.payload_size = payload;
    memset(value.payload, 0x5A, payload);
    nl_secure_init(&tx, key, mode, 0, NULL, NULL);
    nl_secure_init(&rx, key, mode, 0, NULL, NULL);
    start = now();
    for (i = 0; i < RUNS; ++i) nl_secure_seal(&tx, &value, air, sizeof(air), &size);
    seal = per_op(start, now());
    start = now();
    for (i = 0; i < RUNS; ++i) nl_secure_open(&rx, air, size, &opened, &counter);
    open = per_op(start, now());
    start = now();
    for (i = 0; i < RUNS; ++i) nl_fragment_encode(&value, plain, sizeof(plain), &plain_size);
    encode = per_op(start, now());
    start = now();
    for (i = 0; i < RUNS; ++i) nl_fragment_decode(plain, plain_size, &opened);
    decode = per_op(start, now());
    printf("%-7s payload %3u B: seal %6u  open %6u  (plain encode %4u  decode %4u) insns\n",
           mode == NL_SECURE_AUTH ? "AUTH" : "ENCRYPT", payload, seal, open, encode, decode);
}

int main(void)
{
    static const uint8_t payloads[] = {0, 16, 50, 100};
    unsigned m, p;
    TIMER_RELOAD = 0xFFFFFFFFu;
    TIMER_VALUE = 0xFFFFFFFFu;
    TIMER_CTRL = 1u;
    for (m = 0; m < 2u; ++m)
        for (p = 0; p < sizeof(payloads); ++p)
            measure(m == 0u ? NL_SECURE_AUTH : NL_SECURE_ENCRYPT, payloads[p]);
    return 0;
}
