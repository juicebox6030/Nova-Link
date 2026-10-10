# Extended NOVA-LINK protocol prototype

This directory preserves an independent portable C99 implementation developed
alongside the root SDK. It includes metadata and peer discovery, segmentation,
INI configuration, CRC-8 link frames, Python codecs with shared C vectors, and
multi-node simulation. Board drivers and physical RF operation are unimplemented.
Simulation delivery and latency figures are model results, not radio measurements.

The root build includes this prototype and its checks by default. From the
repository root:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --parallel
ctest --test-dir build --output-on-failure
./build/experimental/extended/sim/nl_sim --nodes 4 --runs 4
python3 experimental/extended/tools/nl_decode.py --help
cmake --build build --target docs-extended
```

For a standalone prototype build:

```sh
cmake -S experimental/extended -B build/extended
cmake --build build/extended --parallel
ctest --test-dir build/extended --output-on-failure
```

Radio firmware whose SPI handling runs in an interrupt uses the deferred
handoff (`nl_radio_spi_isr()` / `nl_radio_spi_arm()` in the ISR,
`nl_radio_poll()` in the main loop; see `include/nova_link/nl_radio.h`).
Compile-time switches in `nl_config.h`: `NL_CRITICAL_ENTER`/`EXIT` for the
few shared updates, `NL_ISR_BUILD=1` to compile out all logging
(`NL_LOG_MIN_LEVEL` 4), `NL_LOG_IN_ISR` (default 0) to keep the SPI request
path free of log calls while still counting rejected frames, and
`NL_PLUGIN_ENTER`/`EXIT` around plugin callbacks. `nl_sim --spi-deferred`
simulates this path.

`NL_BUILD_TESTS`, `NL_BUILD_SIM`, and `NL_UBSAN` control standalone tests,
simulation, and runtime-free undefined-behavior checks. In the root build,
`NOVA_BUILD_TESTS`, `NOVA_BUILD_TOOLS`, and `NOVA_ENABLE_SANITIZERS` also apply here.
Use `NOVA_BUILD_EXTENDED=OFF` to exclude the entire prototype.

The library target is `nova_link_extended`. Its public headers live here under
`include/nova_link/nl_*.h`, and its settings are in `config/nova_link.ini`.
It is excluded from the installed SDK. Do not link it together with the root
`nova_link` library: they define overlapping `nl_*` symbols with different APIs.
The prototype's `[AA][CMD][LEN][DATA][CRC8]` framing also differs from the root
SDK's `[AA][LEN][CMD][DATA]`. Select one stack for each program and adapter.

The [wire reference](docs/wire_format.adoc), [simulation notes](docs/simulation.adoc),
and [tools guide](tools/README.md) describe this directory only. Paths in those
guides are relative to this directory. No simulated format establishes
Multiverse compatibility or CC1352R hardware readiness.

Run the Python suite directly from this directory with:

```sh
python3 -m unittest discover -s tools/tests -t tools
```

Shared vectors are checked automatically by CTest. After an intentional format
change, regenerate them from the repository root with:

```sh
./build/experimental/extended/tests/gen_vectors --out experimental/extended/tests/vectors
```

The generated API reference is `experimental/extended/build/doxygen/html/index.html`
when using the root `docs-extended` target. For direct Doxygen use from this
directory, create `build` first, then run `doxygen Doxyfile`.
