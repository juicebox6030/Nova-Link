# Compiled plugin examples

`counter.c` and `counter.h` implement a four-byte big-endian counter payload.
Configure its context as a transmitter with an exclusive zone claim or a receiver
with a read-only claim. A transmitter sends one value per host tick and advances
its application counter only when the transport accepts it. The receiver ignores
other zones and payload sizes.

The example is compiled into `nova-sim`; it has no OS, device, or logging
dependency. Keep the context alive until the host unregisters the plugin. Plugin
hooks and ownership behavior are described in
[the development guide](../docs/Development.md).
