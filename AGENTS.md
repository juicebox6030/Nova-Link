# Agent guidance

## Project
NOVA-LINK is a portable C99 wireless protocol and firmware SDK for live event applications. The repository includes a native software protocol, plugin lifecycle, DMX support, hardware independent simulations, and a separate experimental extended protocol. Hardware drivers and Multiverse over the air compatibility remain incomplete or unverified; do not describe simulations or compilation as hardware validation.

## Repository map
- `include/`: public C APIs (`nova_link/` and `nova/`).
- `src/`: portable protocol, host, queue, scheduler, radio, DMX and Multiverse engine.
- `plugins/`: lifecycle managed transport and application services.
- `platform/`: ESP-IDF and TI CC1352R compile integrations.
- `examples/`, `support/`: demonstrations and developer simulation support.
- `tests/`: C and Python host tests.
- `tools/`: offline inspection, capture analysis and replay helpers.
- `experimental/extended/`: distinct prototype API and wire format.
- `docs/`: development, protocol, hardware, validation and roadmap records.

## Build and host checks
Requires CMake 3.16+, a C99 compiler, and Python 3 for Python-backed tests. Use a temporary build directory so generated output stays outside the checkout. Do not flash boards or run hardware tests as part of the host check.

```sh
cmake -S . -B /tmp/nova-link-build -DCMAKE_BUILD_TYPE=Debug
cmake --build /tmp/nova-link-build --parallel
ctest --test-dir /tmp/nova-link-build --output-on-failure
```

The root decision index is [`DECISIONS.md`](DECISIONS.md). Native wire-format decisions and golden vector are maintained in [`docs/Protocol_Decisions.md`](docs/Protocol_Decisions.md); link to that table rather than copying it here. Record every new design decision in `DECISIONS.md` in the same commit that introduces the decision.

## Clean room and provenance
For Multiverse work, follow [`docs/Multiverse_2_4GHz.md`](docs/Multiverse_2_4GHz.md), [`docs/Multiverse_Firmware_Findings.md`](docs/Multiverse_Firmware_Findings.md), and [`docs/Hardware_Preparation.md`](docs/Hardware_Preparation.md): firmware-derived findings are hypotheses, not on-air confirmation; interoperability requires bench evidence. Keep implementation original and based on independently obtained, permitted behavior requirements. Do not copy vendor code or proprietary implementation material into implementation or docs. Record source and confidence, distinguish observed behavior from inference, and state unknowns rather than guessing. Do not add firmware binaries, keys, secrets, or decompiled/disassembled material.

## Hardware and generated data
Devices on `ltpshop-board` are shared. Before flashing, debugging, serial access, or RF capture on that host, take the `hw-lease` skill lease. Never delete or modify Multiverse `build*` paths, device locks, or run logs. Host builds and software simulations are not hardware verification.

## Git
Work only in the repository and branch named for the task. When complete, commit and push to `main`; do not open PRs unless asked and do not run CI. If work cannot be completed, use a work branch and a draft PR titled `WIP: …`. Do not merge remote branches without explicit direction.

## Documentation
Keep claims narrow and sourced. Pin assignments, board revisions, PHY parameters, and protocol behavior must not be invented. Use `DECISIONS.md` for decisions not already covered by the protocol table, with a source and status for each entry.

## GitHub Actions and local checks

Owner policy (2026-10-22): GitHub Actions must remain disabled for this repository.
- Run tests, lint, builds, security checks, packaging and other automation locally on the authorized development host. Use existing project scripts and report the commands and exit results.
- Do not create, enable, trigger, repair or depend on GitHub Actions workflows, including self-hosted Actions runners. Existing workflow files are historical references for local commands only.
- Do not require GitHub Actions status checks in branch protection or rulesets. This policy supersedes older CI/Actions directions in project documentation; changing it requires an explicit owner instruction.
