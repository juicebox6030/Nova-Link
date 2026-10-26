# Superseded USB-data architecture — NOT current product acceptance

Owner correction, 2026-10-22: “Thats fine, we can skip usb interop and just leave wireless AND wired RDM as the main path. The key is going to be how do we flash updates to the device over the DMX port”.

Everything in this directory is historical evidence only. CP2102N, USB-data recovery, enumeration/current-domain gates and their ERC reports are not active product circuitry. Their old paths/comments describe the former revision. Do not run these generators as current package acceptance. Current power/service capture is `../power-service/`; USB-C is power only. Factory cJTAG and a separate resident-loader service input are retained.
