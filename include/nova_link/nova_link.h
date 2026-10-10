#ifndef NOVA_LINK_H
#define NOVA_LINK_H
/** @file nova_link.h Convenience include for the portable SDK. */
#include "nova_link/fragment.h"
#include "nova_link/transport.h"
#include "nova_link/stream.h"
#include "nova_link/queue.h"
#include "nova_link/zones.h"
#include "nova_link/host.h"
#include "nova_link/scheduler.h"
#include "nova_link/radio.h"
#if defined(NOVA_SECURITY) && NOVA_SECURITY
#include "nova_link/secure.h"
#endif
#endif
