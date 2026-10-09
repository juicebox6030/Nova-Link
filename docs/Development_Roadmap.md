# Development Roadmap – NOVA-LINK/API

## Next milestone: direct Multiverse TX/RX at 2.4 GHz

Target: receive from a Multiverse Transmitter and transmit to ETC ColorSource V fixtures using the CC1352R directly. See the [bench plan and protocol questions](Multiverse_2_4GHz.md).

- [x] Portable DMX level framing and software TX/RX loopback
- [x] RF capture log format, analyzer, and validation checks
- [ ] Confirm the CC1352R board, SDK, and transmitter variant
- [ ] Verify the existing transmitter-to-fixture reference link and record settings
- [ ] Build and flash receive capture firmware for the selected board
- [ ] Establish the actual PHY, framing/integrity fields, and hopping behavior
- [ ] Reconstruct received DMX levels and compare with known input
- [ ] Implement Multiverse RF TX and verify fixture output/reacquisition
- [ ] Integrate verified RF TX/RX with ESP32 host/plugin API
- [ ] Implement and validate RDM independently

Software checks do not establish Multiverse RF compatibility. Native NOVA-LINK fragments are a separate wire format.

## NOVA-API

- [ ] Data_Fragment Structure
- [ ] Fragment -> Payload
- [ ] Payload -> Fragment
- [ ] Zone Claim Table
- [ ] Logging/Alerts
- [ ] Zone 0 Flag Managment
- [ ] Send Payload (Plugin)
- [ ] Receive Payload (Plugin)
- [ ] Zone Claim Managment (Plugin)
- [ ] Send Fragment (SPI)
- [ ] Receive Fragment (SPI)


## NOVA-Link

- [ ] Send Fragment (SPI)
- [ ] Receive Fragment (SPI)
- [ ] Data_Fragment Structure
- [ ] Clock Scheduler
- [ ] Fragment -> TX 
- [ ] RX -> Fragment
- [ ] Logging/Alerts
- [ ] Fragment De-Duplication
- [ ] Zone 0 Flag Managment

## Plugins

- [ ] TBD...
