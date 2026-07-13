"""XBee coordinator radio boundary.

`XBeeRadioPort` is a Protocol so CoordinatorService can be unit tested against a
`FakeXBeeRadioPort` without any real serial hardware attached.
"""
from __future__ import annotations

from typing import Callable, Protocol


class XBeeRadioPort(Protocol):
    def open(self) -> None: ...

    def close(self) -> None: ...

    def get_64bit_addr(self) -> str: ...

    def get_parameter(self, at_command: str) -> bytes: ...

    def set_parameter(self, at_command: str, value: bytes) -> None: ...

    def write_changes(self) -> None: ...

    def add_io_sample_received_callback(self, callback: Callable) -> None: ...


class DigiXBeeRadioPort:
    """Real XBeeRadioPort implementation, wrapping digi.xbee.devices.XBeeDevice."""

    def __init__(self, serial_port: str, baud_rate: int):
        from digi.xbee.devices import XBeeDevice

        self._device = XBeeDevice(serial_port, baud_rate)

    def open(self) -> None:
        self._device.open()

    def close(self) -> None:
        self._device.close()

    def get_64bit_addr(self) -> str:
        return str(self._device.get_64bit_addr())

    def get_parameter(self, at_command: str) -> bytes:
        return self._device.get_parameter(at_command)

    def set_parameter(self, at_command: str, value: bytes) -> None:
        self._device.set_parameter(at_command, value)

    def write_changes(self) -> None:
        self._device.write_changes()

    def add_io_sample_received_callback(self, callback) -> None:
        self._device.add_io_sample_received_callback(callback)
