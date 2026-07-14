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
    threshold: float | None = None
    hysteresis: float = 0.0
    direction: str = "above"  # "above" | "below" — which side of threshold means "triggered"
    above_threshold_payload: str = "ON"
    below_threshold_payload: str = "OFF"
    payload_on: str = "ON"
    payload_off: str = "OFF"
    last_value: float | str | None = None
    triggered: bool | None = None

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
