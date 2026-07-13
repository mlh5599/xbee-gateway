from typing import Protocol


class GpioController(Protocol):
    def set_output(self, pin: int, high: bool) -> None: ...

    def pulse_low(self, pin: int, low_seconds: float, settle_seconds: float) -> None:
        """Used for the XBee coordinator hardware reset line."""
        ...
