"""Local XBee coordinator setup: applies configured AT settings with retry/backoff.

Replaces the legacy LocalZigbeeDevice module / XBeeCoordinatorService class. Fixes two
specific bugs found in that code: the retry path here is a plain loop, not a recursive
`self.initialize()` call with a lowercase-i typo that raised AttributeError on every
retry; and there is exactly one AT-setting write path — `network_encryption_key` is just
another `at_settings` entry (AT command `KY`), not a separately-special-cased property.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from xbee_gateway.config.schema import CoordinatorConfig
from xbee_gateway.gpio.protocol import GpioController
from xbee_gateway.xbee.radio_port import XBeeRadioPort

logger = logging.getLogger(__name__)


def _encode_value(value: str) -> bytes:
    if value.lower().startswith("0x"):
        hex_str = value[2:]
        if len(hex_str) % 2:
            hex_str = "0" + hex_str
        return bytes.fromhex(hex_str)
    return value.encode("ascii")


class CoordinatorService:
    def __init__(self, radio: XBeeRadioPort, config: CoordinatorConfig, gpio: GpioController):
        self._radio = radio
        self._config = config
        self._gpio = gpio

    def initialize(self) -> None:
        last_error: Optional[Exception] = None
        for attempt in range(1, self._config.connect_retry_attempts + 1):
            try:
                self._reset_radio_if_configured()
                self._radio.open()
                self._apply_at_settings()
                logger.info("Coordinator initialized on %s", self._config.serial_port)
                return
            except Exception as exc:  # noqa: BLE001 - retry any failure, surface after exhausting
                last_error = exc
                logger.warning(
                    "Coordinator init attempt %s/%s failed: %s",
                    attempt,
                    self._config.connect_retry_attempts,
                    exc,
                )
                time.sleep(self._config.connect_retry_backoff_seconds)
        raise RuntimeError(
            f"Failed to initialize XBee coordinator after "
            f"{self._config.connect_retry_attempts} attempts"
        ) from last_error

    def set_io_sample_callback(self, callback: Callable) -> None:
        self._radio.add_io_sample_received_callback(callback)

    def close(self) -> None:
        self._radio.close()

    def _reset_radio_if_configured(self) -> None:
        if self._config.reset_gpio_pin >= 0:
            self._gpio.pulse_low(self._config.reset_gpio_pin, low_seconds=1, settle_seconds=2)

    def _apply_at_settings(self) -> None:
        changed = False
        for name, setting in self._config.at_settings.items():
            if not setting.value:
                logger.debug("Skipping empty AT setting %s (%s)", name, setting.at)
                continue

            new_value = _encode_value(setting.value)

            if setting.verify_before_write:
                current_value = self._radio.get_parameter(setting.at)
                if current_value == new_value:
                    continue

            self._radio.set_parameter(setting.at, new_value)
            changed = True
            logger.info("Applied AT setting %s (%s)", name, setting.at)

        if changed:
            self._radio.write_changes()
