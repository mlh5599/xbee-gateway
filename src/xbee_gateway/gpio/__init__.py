from xbee_gateway.gpio.null_backend import NullGpioController
from xbee_gateway.gpio.protocol import GpioController

__all__ = ["GpioController", "NullGpioController", "build_gpio_controller"]


def build_gpio_controller(backend: str, config) -> GpioController:
    """Explicit config-driven backend selection — never platform-sniffed.

    The legacy code used `platform.machine() == 'armv7l'` to decide whether pigpio was
    available, which is wrong for the actual target hardware (a Raspberry Pi Model B
    Rev 2 reports `armv6l`), silently disabling the real GPIO path in production.
    """
    if backend == "pigpio":
        from xbee_gateway.gpio.pigpio_backend import PigpioController

        return PigpioController(config)
    if backend == "none":
        return NullGpioController()
    raise ValueError(f"Unknown gpio_backend: {backend!r} (expected 'pigpio' or 'none')")
