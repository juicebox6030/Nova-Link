# Direct Multiverse interoperability at 2.4 GHz

The next NOVA-LINK milestone is direct communication between a TI CC1352R
and City Theatrical Multiverse equipment. The bench targets are an ETC
ColorSource V fixture and a Multiverse Transmitter. This is a separate radio
backend from the planned native NOVA-LINK DataFragment protocol.

The intended data paths are:

```text
RX: Multiverse Transmitter -> 2.4 GHz RF -> CC1352R -> decoded DMX levels
TX: DMX levels -> CC1352R -> 2.4 GHz RF -> ETC ColorSource V
```

Current implementation: portable DMX level framing, a software loopback, an
RF capture log analyzer with differential stimulus comparisons, and a
[TX/RX software emulator](Multiverse_Emulator.md) with chunked full/delta state,
completion ownership, integrity checks, loss/recovery simulation and replay.
The emulator uses explicitly synthetic packets behind a normalized adapter API.
No CC1352R firmware, actual Multiverse RF decoder, or actual Multiverse RF
transmitter has been implemented or tested. Both example RF traffic and emulator
traffic are synthetic. Hardware preparation targets the documented ESP32-S3,
CC1352R and 5911 2.4 GHz reference; record the actual board revision and SDK
release with the deployment. The [preparation guide](Hardware_Preparation.md)
provides a compile/startup project and capture-service handoff without assigning
unverified PHY settings or board pins.

## Established facts and open questions

| Item | Evidence / implication |
| --- | --- |
| Fixture settings | ETC documents the ColorSource V radio settings `Uni` (universe), `id` (SHoW ID suffix), and `PAS` (SHoW Key). For example, `id=100` represents full SHoW ID `24100`. Record the full ID in captures. |
| Wireless mode | Multiverse uses frequency hopping. The SHoW ID selects data-rate class, band selection, and hop pattern; it does not specify the bit-level radio configuration in the public user guide. |
| Transmitter variant | City Theatrical lists 5910 (900 MHz/2.4 GHz), 5911 (2.4 GHz), and 5912 (900 MHz). Confirm the label; 5912 cannot supply the required 2.4 GHz signal. |
| Two radio streams | The 5911 has two 2.4 GHz radio streams. Record which radio and universes are active to avoid combining two independent streams during analysis. |
| Packet contents | mDMX, error correction, SHoW Key, and mRDM affect transport. A complete DMX universe is not necessarily present verbatim in an RF packet. |
| CC1352R capabilities | TI documents configurable proprietary PHYs, preambles, sync words, and CRCs. Supported combinations depend on the device, RF patches, SDK, and SmartRF configuration. Sharing the frequency band does not establish compatibility. |
| Unknown RF details | Modulation, actual bit rates, deviation/bandwidth, channel frequencies, preamble/sync, whitening, length encoding, CRC, FEC, key handling, hopping timing/sequence, and control traffic remain unverified. |

Do not send native NOVA-LINK DataFragments, IEEE 802.15.4 packets, or TI
example packets to the fixtures and label that Multiverse support. A TI-to-TI
link only validates the local radio setup. A matching candidate-PHY CRC alone
does not identify Multiverse traffic.

## Next milestones

1. **Identify the board and establish a known-good fixture link.** Record the
   CC1352R board/revision, SDK version, Multiverse Transmitter part number and
   firmware, ColorSource V model/firmware, full SHoW ID, SHoW Key, universe,
   fixture address/personality, mDMX/FEC settings, and active radio(s). Verify
   that the existing transmitter drives a repeatable look on the fixture.
   ETC's `Con=3` means DMX and RDM are connected; `Con=1` indicates DMX-only
   reception with suboptimal communication. Preserve this known-good baseline.
2. **Bring up a receiver and characterize the PHY.** Start from a TI SDK
   receiver example for the exact board. Export candidate 2.4 GHz settings
   from SmartRF Studio for that device and keep each export with its profile
   identifier. First confirm the receiver with a known test signal. Capture
   Multiverse observations and, if available, independent RF measurements.
   Investigate occupied frequencies, modulation, symbol rate, and packet
   synchronization before treating any candidate payload as decoded data.
   The CC1352R packet receiver needs a compatible PHY and framing configuration;
   it is not a general raw-IQ spectrum capture device. An RF analyzer/SDR may be
   needed to determine parameters that cannot be recovered from packet entries.
3. **Decode reception from Multiverse.** Capture cold startup/receiver joining,
   a constant DMX baseline, one-channel changes, and controlled patterns with
   an explicit stimulus label. Change one variable per run. Resolve packet
   integrity and delta/full-state reconstruction, universe mapping, and timing.
   Compare reconstructed levels with the known input across repeated runs,
   including loss, resynchronization, and fixture reconnects. Do not feed raw
   RF bytes into the DMX serial parser: a radio decoder must first reconstruct
   a complete `nova_dmx_frame_t`.
4. **Implement compatible transmission to ColorSource V.** Once the PHY,
   integrity fields, hopping synchronization, and required control exchanges
   are understood, implement a separate Multiverse encoder/scheduler. Test on
   the isolated bench with the original transmitter stopped for the TX run.
   Verify the fixture's output for known level patterns, not just whether an
   RF command reports success. Verify startup and reacquisition as well as
   sustained changes. RDM support requires its own implementation and tests.
5. **Integrate the host interface.** Connect verified Multiverse TX/RX to the
   ESP32/plugin API through decoded frames and explicit link status. Keep
   native NOVA-LINK zones and SPI framing separate from Multiverse's on-air
   format. Report DMX-only and DMX/RDM interoperability separately.

Use existing connectivity for the reference transmitter's sACN/Art-Net input.
This work requires no changes to UniFi, gateway/controller settings, firewall,
NAT, routing, DNS, databases, or gateway persistence.

## Capture logs

The receiver adapter should emit one JSON object per observation, one per line.
Retain the exact generated PHY configuration alongside the log. Log the
transmitter/fixture settings above in the run notes; a profile identifier alone
is not a reproducible configuration.

| Field | Meaning |
| --- | --- |
| `timestamp_us` | Non-negative monotonic capture timestamp, extended across hardware timer wraps. Keep a single receiver/clock per file. |
| `frequency_hz` | Actual tuned receive frequency in Hz, not a Wi-Fi channel or assumed transmitter hop. |
| `profile` | Identifier of the candidate radio configuration/SDK export used. |
| `stimulus` | Known bench input, such as `baseline` or `channel_1_32`; defaults to `unspecified`. |
| `payload_hex` | Bytes returned by the configured receiver, as contiguous hex pairs. Record in the profile which headers/trailers the RF core removes. These bytes are not raw IQ or necessarily a complete on-air packet. |
| `crc` | `ok`, `bad`, or `unknown`, according to the candidate configuration. Use `unknown` when checking is disabled or not established. |
| `rssi_dbm` | Measured RSSI or null/omitted if unavailable. |

Store receiver queue overflows, UART drops, tuning intervals, and RF command
status in separate run diagnostics. Otherwise missing log entries can be
mistaken for missing RF packets. Copy packet entries promptly and print from a
task rather than blocking the RF callback. Preserve failed-CRC entries when
supported during discovery; do not silently filter them out.

Run the analyzer with:

```sh
python3 tools/analyze_rf_capture.py capture.jsonl --output summary.json
```

It reports observation counts, lengths, distinct payload counts, RSSI, and
inter-arrival gaps grouped by profile, frequency, and stimulus. With
`--compare-stimuli baseline channel_1_32` it also compares byte distributions
within matching profile/frequency/length/CRC groups. These offsets are candidates
for investigation, not decoded DMX channel mappings. It does not decode
Multiverse or infer a hop schedule. Observations on a scanned channel
omit traffic received elsewhere or while tuning, so observed gaps are not
proof of the transmitter's packet rate or hop timing.

Try the synthetic example without hardware:

```sh
python3 tools/analyze_rf_capture.py examples/rf_capture.simulated.jsonl
```

The example frequency and byte values are illustrative; they are not measured
Multiverse settings or traffic.

## Portable DMX core

`include/nova/dmx.h` exposes a frame with 0–512 level slots. `nova_dmx_encode`
serializes a null start code followed by those slots for a future wired UART
adapter or software reference. The receive parser accepts validated BREAK,
MARK, and byte events from such an adapter, completing a packet at the next
BREAK. It rejects alternate start codes and oversized packets and drops
incomplete data when reset after a UART error.

This core provides a stable level representation for the future RF decoder
and encoder; its serial bytes do not implement Multiverse packet framing.
UART timing, RS-485 hardware, and RF-core commands belong in board adapters.
It uses no heap allocation. Access each receiver state from one task or provide
external synchronization. UART read chunk boundaries and idle timeouts are
not treated as DMX packet delimiters.

Build and check the current implementation:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
./build/dmx_loopback
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Sources

- [ETC Multiverse Wireless Setup Information Guide, revision D](https://www.etcconnect.com/WorkArea/DownloadAsset.aspx?id=10737510878)
  describes SHoW IDs and the ColorSource V radio settings/status.
- [City Theatrical Multiverse Transmitter product page](https://www.citytheatrical.com/products/electronics/multiverse-wireless-dmx-rdm/multiverse-transmitter)
  lists the transmitter variants.
- [City Theatrical 5911 Multiverse Transmitter manual](https://www.citytheatrical.com/docs/default-source/manuals/5911-multiverse-transmitter.pdf)
  documents the two radios, hopping selections, universe mapping, mDMX/FEC,
  and SHoW Key settings, but not a bit-level interoperability specification.
- [TI CC1352R datasheet, section 9.3](https://www.ti.com/lit/ds/symlink/cc1352r.pdf)
  documents the RF core and limitations of supported PHY combinations.
- [ESTA published standards](https://tsp.esta.org/tsp/documents/published_docs.php)
  lists ANSI E1.11 (DMX512-A), the serial framing reference. The DMX core uses
  transmit minima of 92 us BREAK / 12 us MARK and receive minima of
  88 us BREAK / 8 us MARK, with 250 kbaud, 8 data bits, no parity, 2 stop bits.
