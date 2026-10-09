#include "nova_link/nova_link.h"
#include "nova/dmx.h"
int main(void)
{
    nl_fragment fragment = {0};
    uint8_t bytes[NL_FRAGMENT_MAX];
    size_t size = 0;
    nova_dmx_frame_t dmx = {0};
    size_t dmx_size = 0;
    uint8_t dmx_bytes[NOVA_DMX_MAX_PACKET_BYTES];
    return nl_fragment_encode(&fragment, bytes, sizeof(bytes), &size) == NL_OK && size == 2u &&
        nova_dmx_encode(&dmx, dmx_bytes, sizeof(dmx_bytes), &dmx_size) == NOVA_DMX_OK &&
        dmx_size == 1u && dmx_bytes[0] == 0u ? 0 : 1;
}
