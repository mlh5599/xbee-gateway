from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


class ChannelKind(str, Enum):
    ANALOG = "analog"
    ANALOG_THRESHOLD_BINARY = "analog_threshold_binary"
    DIGITAL_BINARY = "digital_binary"


@dataclass
class Channel:
    io_line: str
    name: str
    kind: ChannelKind
    unit_of_measurement: str | None = None
    device_class: str | None = None
    value_template: str | None = None
    on_threshold: float | None = None
    off_threshold: float | None = None
    direction: str = "above"  # "above" | "below" — which side is "hotter"/triggered
    # Failsafe against a latched-ON channel that never comes back past off_threshold:
    # once triggered, if the reading sits in the hold band (between on_threshold and
    # off_threshold) for this many seconds without either reaching off_threshold or
    # going deeper than on_threshold, treat it as a false trigger and release. None
    # disables the failsafe (pure two-setpoint hysteresis).
    band_timeout_seconds: float | None = None
    above_threshold_payload: str = "ON"
    below_threshold_payload: str = "OFF"
    payload_on: str = "ON"
    payload_off: str = "OFF"
    last_value: float | str | None = None
    # Last raw analog reading seen for an analog_threshold_binary channel, so the
    # band timeout can be re-evaluated on a periodic tick even if no new sample
    # has arrived (e.g. the end device has gone silent while in the hold band).
    last_raw: float | None = None
    triggered: bool | None = None
    # Monotonic timestamp of the most recent OFF->ON transition, for band_timeout_seconds.
    triggered_at: float | None = None

    def slug(self) -> str:
        return _SLUG_NON_ALNUM.sub("-", self.name.lower()).strip("-")

    def state_topic(self, base_topic: str, device_address: str) -> str:
        return f"{base_topic}/{device_address}/{self.slug()}/state"


@dataclass
class RemoteDevice:
    address: str
    name: str
    manufacturer: str = "Unknown"
    model: str = "XBee Sensor"
    channels: dict[str, list[Channel]] | None = None
    auto_registered: bool = False

    def __post_init__(self) -> None:
        if self.channels is None:
            self.channels = {}
