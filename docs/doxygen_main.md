# NOVA-LINK API reference {#mainpage}

This is the reference for the portable C99 core in `include/nova_link/`.
The same sources build for the ESP32-S3 host, the CC1352R radio
co-processor, and the POSIX simulator and unit tests. Nothing allocates
memory; every object is sized for static allocation.

Where to start:

- nl_host.h: the host core (plugins, zone claims, discovery, the link to the radio).
- nl_radio.h: the radio scheduler and the platform loop that drives it.
- nl_link.h: host <-> radio frames and their payloads.
- nl_fragment.h, nl_meta.h, nl_segment.h: what goes on the air.
- nl_config_file.h: loading `config/nova_link.ini`.

Byte-level formats are described in `docs/wire_format.adoc`, and simulation
results behind the defaults in `docs/simulation.adoc`.
