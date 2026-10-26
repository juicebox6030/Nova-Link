# Regulated rotating source development capture

2026-10-23, main b42c0e6284aac734fde851c69146abf73920f337. Hardware only; writes only this directory. Parent owns integration, Astra owns mechanism. No children/threads/install/outreach/hardware/firmware/git publication. Phase0 and frozen cell protection are read-only.

One prototype: stationary IRM-20-5 -> existing20mm FPC construction/1.046167656m path -> TPS259474 input reverse-blocking protection -> TPS63070 forced PWM5.136V -> TPS25810 CHG high/CHG_HI low -> full16contact GCTUSB4105 with passive D+/D- short. No PD/data processing/mains capture.25x18x1mm top-only board is target, not accepted collar fit; actual connector3.31+/-0.15mm already exceeds3.2mm height target.

Acceptance: exact primary sources/hash ledger, literal circuit/net/pin/passive/state/corner checks, real ERC, full lands and actual saved placement/DRC/unrouted count, simple package STEP if existing FreeCAD works. Hot FPC uses actual power/current quadratic, not1.5A; efficiencies/ripple/transients/max-current extrapolations declared. Readonly baseline core ID43mm/body/carrier/harness envelopes checked explicitly; no sealed thermal/mains/USB compliance acceptance.

Stop after this one captured circuit+placement and source/physical objections. Do not optimize a second architecture or alter parent contracts.

Current checkpoint:30 purchased parts,32 full footprints,25x18x1 top-only unrouted placement,349.606mm² complete courtyards.5.136V target includes full mated-connector loop allocation;4.786..5.336V conditional port window.2.453A input at85%/200mAVCONN,2.987A at80%/410mAstress, no guaranteedefficiency/currentatminVIN. Real0ERC,46ICpins/16USBterminals/24passives,18CCstates,57independentlanddimensions;4realDRCholeclearanceerrors/85unconnected retained. SimpleSTEP/FCStd32rotating solids/496pairchecks. Height3.46>3.2target;IRM20bodyfitscore butmaximum+Vlead intersectsoldmainskeepout. Routing/thermal/USB/sourcefault/assembly/integratedfit acceptance UNMET. Stopafterreceipt;parentintegrationonly.
