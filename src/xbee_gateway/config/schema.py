"""Config dataclasses shared by the CLI app and the future web UI (Milestone 2).

Deliberately stdlib dataclasses, not pydantic: avoids a compiled dependency on
low-resource ARM hardware where wheel availability/build time is a real risk.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


@dataclass
class MqttConfig:
    host: str = "mqtt.example.local"
    port: int = 1883
    username: str = ""
    password: str = ""
    client_id: str = "xbee-gateway"
    base_topic: str = "xbeegateway"
    discovery_prefix: str = "homeassistant"
    availability_topic: str = "xbeegateway/status"
    tls: bool = False
    # Belt-and-suspenders re-assert of retained "online" while connected, guarding against
    # the retained value getting clobbered by anything other than our own on_connect (e.g.
    # broker losing retained state, another publisher). 0 disables.
    availability_reassert_interval: float = 3600.0


@dataclass
class ATSetting:
    """One coordinator AT-command parameter.

    `verify_before_write` replaces the old, misleadingly-named `read_only` field: the old
    code used it to mean "can't be read back from the radio, write unconditionally" which
    is backwards from what "read only" implies. `secret` flags values (e.g. the network
    encryption key) that must never be logged or rendered in plaintext by a future UI.
    """

    at: str
    value: str
    verify_before_write: bool = True
    secret: bool = False


@dataclass
class CoordinatorConfig:
    serial_port: str = "/dev/ttyUSB0"
    baud_rate: int = 9600
    reset_gpio_pin: int = -1
    status_led_gpio_pin: int = -1
    gpio_backend: str = "none"  # "pigpio" | "none" — explicit config choice, never platform-sniffed
    connect_retry_attempts: int = 5
    connect_retry_backoff_seconds: float = 2.0
    at_settings: dict[str, ATSetting] = field(default_factory=dict)


@dataclass
class LoggingConfig:
    level: str = "INFO"


@dataclass
class AppConfig:
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    coordinator: CoordinatorConfig = field(default_factory=CoordinatorConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


@dataclass
class ChannelConfig:
    io_line: str
    name: str
    kind: str  # "analog" | "analog_threshold_binary" | "digital_binary"
    unit_of_measurement: Optional[str] = None
    device_class: Optional[str] = None
    value_template: Optional[str] = None
    threshold: Optional[float] = None
    hysteresis: float = 0.0
    direction: str = "above"  # "above" | "below" — which side of threshold means "triggered"
    above_threshold_payload: str = "ON"
    below_threshold_payload: str = "OFF"
    payload_on: str = "ON"
    payload_off: str = "OFF"

    def slug(self) -> str:
        return _SLUG_NON_ALNUM.sub("-", self.name.lower()).strip("-")


@dataclass
class DeviceConfig:
    address: str
    name: str
    manufacturer: str = "Unknown"
    model: str = "XBee Sensor"
    channels: list[ChannelConfig] = field(default_factory=list)


@dataclass
class DevicesConfig:
    devices: list[DeviceConfig] = field(default_factory=list)
    auto_register_unknown_devices: bool = True
