#include "nova_link/nova_link.h"
int main(void)
{
    nl_fragment fragment = {0};
    uint8_t bytes[NL_FRAGMENT_MAX];
    size_t size = 0;
    return nl_fragment_encode(&fragment, bytes, sizeof(bytes), &size) == NL_OK && size == 2u ? 0 : 1;
}
