# Extended NOVA-LINK prototype API reference {#mainpage}

This is the reference for the portable C99 core in `include/nova_link/`.
The sources are intended for an ESP32-S3 host and CC1352R radio co-processor;
only desktop builds, simulation, and unit tests have been validated. Nothing allocates
memory; every object is sized for static allocation.

Where to start:

- nl_host.h: the host core (plugins, zone claims, discovery, the link to the radio).
- nl_radio.h: the radio scheduler and the platform loop that drives it.
- nl_link.h: host <-> radio frames and their payloads.
- nl_fragment.h, nl_meta.h, nl_segment.h: what goes on the air.
- nl_config_file.h: loading `config/nova_link.ini`.

Byte-level formats are described in `docs/wire_format.adoc`, and simulation
results behind the defaults in `docs/simulation.adoc`.
