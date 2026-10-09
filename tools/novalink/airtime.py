"""On-air time and per-zone transmit budget estimates.

This is an engineering estimate, not something the C core computes: the
radio model in src/nl_radio.c treats a TX as instantaneous (it schedules the
next repeat ``repeat_interval_us + rand(0..repeat_jitter_us)`` after the TX
*starts*). Real PHYs take milliseconds per fragment, which this module makes
visible.

Packet model (every field is an explicit :class:`Phy` parameter)::

    [preamble][sync word][length][address][fragment: 2 + payload][CRC]

* The NOVA-LINK fragment (2-byte header + 0..100 payload bytes) is the PHY
  payload; nothing else is added by the link layer.
* Whitening (PN9 on the CC13xx/CC26xx) scrambles bits but does not change the
  length, so it never affects airtime; it is recorded for documentation only.
* FEC / coded PHYs are not modelled. ``setup_us`` can absorb synthesizer
  calibration, ramp-up or other per-packet fixed costs (0 by default).
"""

from dataclasses import asdict, dataclass, replace
from typing import Optional

from .common import FRAGMENT_HEADER_SIZE, MAX_PAYLOAD

#: Depth of the radio's per-zone TX queue (NL_RADIO_TXQ_DEPTH).
TXQ_DEPTH = 8


@dataclass(frozen=True)
class Phy:
    """A PHY and its framing overhead, in bytes.

    Attributes:
        name: Short preset key.
        description: Human-readable summary.
        bitrate_bps: Raw on-air bit rate (symbols carry 1 bit for 2-GFSK).
        preamble_bytes: 0x55/0xAA preamble.
        sync_bytes: Sync word / access address.
        length_bytes: Length field (EasyLink: 1 byte; BLE: 2-byte PDU header).
        address_bytes: Destination address byte(s) inside the payload
            (EasyLink default address filter uses 1 byte; 0 disables it).
        crc_bytes: Trailing CRC.
        whitening: True if data whitening is on (length-neutral).
        setup_us: Fixed per-packet cost added to the airtime (default 0).
        band: "sub-GHz" or "2.4 GHz", used by the regulatory note.
    """
    name: str
    description: str
    bitrate_bps: int
    preamble_bytes: int
    sync_bytes: int
    length_bytes: int
    address_bytes: int
    crc_bytes: int
    whitening: bool = True
    setup_us: float = 0.0
    band: str = "sub-GHz"

    @property
    def overhead_bytes(self):
        return (self.preamble_bytes + self.sync_bytes + self.length_bytes +
                self.address_bytes + self.crc_bytes)

    def frame_bytes(self, payload_len):
        """Bytes on air for a fragment carrying ``payload_len`` payload bytes."""
        return self.overhead_bytes + FRAGMENT_HEADER_SIZE + payload_len

    def airtime_us(self, payload_len):
        return airtime_us(self, payload_len)

    def with_overrides(self, **kw):
        """Copy with some fields replaced (None values are ignored)."""
        return replace(self, **{k: v for k, v in kw.items() if v is not None})


PHYS = {
    "subghz-50k": Phy(
        name="subghz-50k",
        description="TI CC1352R EasyLink 50 kbps 2-GFSK, sub-GHz (868/915 MHz), 25 kHz deviation",
        bitrate_bps=50_000,
        # EasyLink 50 kbps defaults (SmartRF Studio "50 kbps, 2-GFSK"):
        # 4-byte preamble, 32-bit sync word 0x930B51DE, 1-byte length,
        # 1-byte address filter, CRC-16, PN9 whitening.
        preamble_bytes=4, sync_bytes=4, length_bytes=1, address_bytes=1, crc_bytes=2,
        whitening=True, band="sub-GHz"),
    "ble-1m": Phy(
        name="ble-1m",
        description="2.4 GHz BLE-like 1 Mbps GFSK (LE 1M framing; payload > 37 B needs extended PDUs)",
        bitrate_bps=1_000_000,
        # LE 1M: 1-byte preamble, 4-byte access address, 2-byte PDU header
        # (counted as the length field), 24-bit CRC, whitening always on.
        preamble_bytes=1, sync_bytes=4, length_bytes=2, address_bytes=0, crc_bytes=3,
        whitening=True, band="2.4 GHz"),
    "prop-500k": Phy(
        name="prop-500k",
        description="2.4 GHz proprietary 500 kbps GFSK with EasyLink-style framing",
        bitrate_bps=500_000,
        # Assumed EasyLink-like framing scaled to 500 kbps: 4-byte preamble,
        # 4-byte sync, 1-byte length, 1-byte address, CRC-16, whitening.
        preamble_bytes=4, sync_bytes=4, length_bytes=1, address_bytes=1, crc_bytes=2,
        whitening=True, band="2.4 GHz"),
}

DEFAULT_PHY = "subghz-50k"


def get_phy(name=DEFAULT_PHY):
    try:
        return PHYS[name]
    except KeyError:
        raise ValueError("unknown PHY %r (known: %s)" % (name, ", ".join(sorted(PHYS)))) from None


def airtime_us(phy, payload_len):
    """Time on air in microseconds for one fragment with ``payload_len``
    (0..100) payload bytes: 8 * frame_bytes / bitrate + setup_us."""
    if not 0 <= payload_len <= MAX_PAYLOAD:
        raise ValueError("payload_len must be 0..%d" % MAX_PAYLOAD)
    return phy.frame_bytes(payload_len) * 8 * 1e6 / phy.bitrate_bps + phy.setup_us


def airtime_table(phy, payloads=None):
    """Rows of {payload_len, fragment_len, frame_bytes, airtime_us} for 0..100."""
    if payloads is None:
        payloads = range(MAX_PAYLOAD + 1)
    return [{"payload_len": p, "fragment_len": FRAGMENT_HEADER_SIZE + p,
             "frame_bytes": phy.frame_bytes(p), "airtime_us": airtime_us(phy, p)}
            for p in payloads]


@dataclass
class ZoneBudget:
    """Result of :func:`zone_budget`. Times in microseconds, rates per second,
    duty cycles as fractions (0.01 = 1 %)."""
    phy: str
    payload_len: int
    tx_repeats: int
    bands: int
    airtime_us: float
    tx_per_fragment: int
    radio_time_per_fragment_us: float
    repeat_gap_mean_us: float
    queue_residence_us: float
    max_fps_radio: float
    max_fps_queue: float
    max_fps: float
    offered_fps: float
    channel_duty: float
    radio_duty: float
    duty_limit: Optional[float]
    max_fps_duty: Optional[float]
    warnings: list

    def to_dict(self):
        return asdict(self)


def zone_budget(phy, payload_len=MAX_PAYLOAD, tx_repeats=3, bands=1,
                repeat_interval_us=1500, repeat_jitter_us=1000, dwell_us=2000,
                turnaround_us=0.0, duty_limit=None, offered_fps=None):
    """Transmit budget of one zone that has the radio to itself.

    Model (one half-duplex radio, as on the CC1352R):

    * Each fragment is sent ``tx_repeats`` times; a dual-band zone with both
      frequencies sends each repeat on both bands (``bands`` = 2), so
      ``tx_per_fragment = tx_repeats * bands`` (each counts in tx_sent).
    * Radio time per fragment = tx_per_fragment * (airtime + turnaround).
      ``max_fps_radio`` is the rate at which the radio is busy 100 %.
    * Repeats of one fragment are spaced ``repeat_interval + U(0, jitter)``
      from TX start, but never closer than the radio needs to finish:
      gap_mean = max(interval + jitter/2, bands * (airtime + turnaround)).
    * The zone's TX queue holds 8 fragments, each until its last repeat is
      sent, so ``max_fps_queue = 8 / residence`` with
      residence = (repeats-1) * gap_mean + bands * (airtime + turnaround).
    * ``max_fps = min(max_fps_radio, max_fps_queue)``.
    * Duty cycles are evaluated at ``offered_fps`` (default ``max_fps``):
      channel_duty is per frequency (repeats * airtime per fragment),
      radio_duty is total transmit time. With ``duty_limit`` (e.g. 0.01 for
      EN 300 220's 1 %), ``max_fps_duty`` is the highest rate that keeps
      each channel under the limit.
    """
    if tx_repeats < 1:
        raise ValueError("tx_repeats must be >= 1 (the radio rejects 0)")
    if bands not in (1, 2):
        raise ValueError("bands must be 1 or 2")
    air = airtime_us(phy, payload_len)
    per_tx = air + turnaround_us
    tx_per_fragment = tx_repeats * bands
    radio_time = tx_per_fragment * per_tx
    gap = max(repeat_interval_us + repeat_jitter_us / 2.0, bands * per_tx)
    residence = (tx_repeats - 1) * gap + bands * per_tx
    fps_radio = 1e6 / radio_time
    fps_queue = TXQ_DEPTH * 1e6 / residence
    fps = min(fps_radio, fps_queue)
    rate = fps if offered_fps is None else float(offered_fps)
    channel_duty = rate * tx_repeats * air / 1e6
    radio_duty = rate * radio_time / 1e6
    fps_duty = None
    if duty_limit is not None:
        fps_duty = min(fps, duty_limit * 1e6 / (tx_repeats * air))

    warnings = []
    if repeat_interval_us < bands * per_tx:
        warnings.append("repeat_interval_us %d is shorter than the %.0f us a repeat occupies the "
                        "radio; the C model treats TX as instantaneous and would schedule the next "
                        "repeat before this one ends" % (repeat_interval_us, bands * per_tx))
    if dwell_us < air:
        warnings.append("dwell_us %d is shorter than one %.0f us fragment; with tx_policy "
                        "IN_SLOT a fragment cannot finish inside its zone slot"
                        % (dwell_us, air))
    if offered_fps is not None and rate > fps:
        warnings.append("offered %.1f fragments/s exceeds the %.1f/s the zone can sustain"
                        % (rate, fps))
    if duty_limit is not None and channel_duty > duty_limit:
        warnings.append("channel duty cycle %.2f %% exceeds the %.2f %% limit"
                        % (channel_duty * 100, duty_limit * 100))

    return ZoneBudget(phy=phy.name, payload_len=payload_len, tx_repeats=tx_repeats, bands=bands,
                      airtime_us=air, tx_per_fragment=tx_per_fragment,
                      radio_time_per_fragment_us=radio_time, repeat_gap_mean_us=gap,
                      queue_residence_us=residence, max_fps_radio=fps_radio,
                      max_fps_queue=fps_queue, max_fps=fps, offered_fps=rate,
                      channel_duty=channel_duty, radio_duty=radio_duty, duty_limit=duty_limit,
                      max_fps_duty=fps_duty, warnings=warnings)


FCC_NOTE = """\
Regulatory note (US, FCC Part 15) -- informational only, not legal advice.

15.249 (902-928 MHz and 2400-2483.5 MHz, any modulation): field strength of
the fundamental <= 50 mV/m at 3 m (about -1.2 dBm EIRP), measured as an
average; the peak may be 20 dB above the average limit. Harmonics <= 500 uV/m
at 3 m. No channel-count or dwell rules.

15.247 allows up to 1 W conducted (0.25 W for 902-928 MHz FHSS with 25-49
channels; antenna gain limits apply) but only for:
  * Digital modulation (DTS): 6 dB bandwidth >= 500 kHz and power spectral
    density <= 8 dBm in any 3 kHz band.
  * Frequency hopping (FHSS): 902-928 MHz needs >= 50 channels with at most
    0.4 s occupancy per 20 s when the 20 dB bandwidth is < 250 kHz, or >= 25
    channels with 0.4 s per 10 s for 250-500 kHz; 2400-2483.5 MHz needs >= 15
    channels with 0.4 s per (0.4 s x channels).

NOVA-LINK as configured (50 kbps 2-GFSK, roughly 100 kHz occupied bandwidth,
8 fixed zone frequencies chosen by the zone plan) is neither DTS-wide nor a
hopping system, so it falls under 15.249's low power limit unless the PHY and
channel plan are redesigned. Per-zone dwell time is not regulated by 15.249,
but average field strength is, so the duty cycle reported here matters when
averaging. Outside the US, ETSI EN 300 220 sub-bands impose duty-cycle limits
(commonly 0.1 %, 1 % or 10 %); check them with --duty-limit.
"""
