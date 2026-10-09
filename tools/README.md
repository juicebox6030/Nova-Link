# NOVA-LINK host tools

Pure Python 3 (standard library only, no pip installs). The C code in
`src/` and `include/` is the reference: every codec here is checked
byte-for-byte against vectors generated from the C library.

## Layout

| Path | Contents |
| --- | --- |
| `novalink/fragment.py` | DataFragment encode/decode (`nl_fragment.c`) |
| `novalink/link.py` | SPI link frames, CRC-8, `nl_link_decode` scan, byte-at-a-time parser, radio params / zone plan / status / pong codecs (`nl_link.c`) |
| `novalink/meta.py` | Zone 0 TLV records, device/claim/plugin-data/congestion/peers values, meta queue (`nl_meta.c`) |
| `novalink/segment.py` | Message segmentation and reassembly (`nl_segment.c`) |
| `novalink/airtime.py` | PHY airtime model, per-zone budget, FCC Part 15 note (estimate only, not in C) |
| `nl_decode.py` | Decoder CLI |
| `nl_airtime.py` | Airtime / budget CLI |
| `tests/` | `unittest` suite |

## nl_decode.py

Each positional argument or non-blank file line (text after `#` ignored) is
one input. Spaces, colons and `0x` prefixes in hex are accepted.

    tools/nl_decode.py 40090b0108...              # raw fragment
    tools/nl_decode.py aad0...                    # SPI link stream (auto-detected)
    tools/nl_decode.py --mode link --stream aa..  # use nl_link_parser_feed instead of the scan
    tools/nl_decode.py -f capture.txt --join      # one stream split over many lines
    tools/nl_decode.py -f capture.txt --reassemble --json
    some_tool | tools/nl_decode.py -f -

`--mode auto` treats an input as a link stream if `nl_link_decode` finds a
valid frame in it, otherwise as a fragment. Zone 0 payloads are decoded as
meta records; other zones show the segment sub-header when it is valid.
`--reassemble` rebuilds segmented messages per (origin, zone) across inputs.
Exit status: 0 ok, 1 decode error, 2 usage or hex error.

## nl_airtime.py

    tools/nl_airtime.py                       # subghz-50k table (0..100 B) + zone budget
    tools/nl_airtime.py --phy all --step 10
    tools/nl_airtime.py --preamble 8 --crc 4 --setup-us 150
    tools/nl_airtime.py --repeats 2 --dual --duty-limit 0.01 --rate 5
    tools/nl_airtime.py --fcc --json

PHY presets: `subghz-50k` (CC1352R EasyLink 50 kbps 2-GFSK, default),
`ble-1m` (2.4 GHz LE 1M framing), `prop-500k` (2.4 GHz 500 kbps). Preamble,
sync, length, address, CRC, whitening and per-packet setup time can all be
overridden. Budget defaults come from `nl_radio_params_default`. The C radio
model treats a transmission as instantaneous; the budget output warns when
`repeat_interval_us` or `dwell_us` is shorter than a fragment's airtime.

## Tests and vectors

    python3 -m unittest discover -s tools/tests -t tools

`tests/vectors/*.json` are produced by `tests/gen_vectors.c` (linked against
the nova_link library). After a C change that alters the wire format:

    cmake --build build --target gen_vectors
    build/tests/gen_vectors --out tests/vectors

`ctest` runs `vectors_up_to_date` (`gen_vectors --check`) and
`python_tools` (the unittest suite above, when Python 3 is found).
Set `NL_VECTORS_DIR` to run the Python tests against another vector set.
