import logging

logger = logging.getLogger(__name__)


class NullGpioController:
    """No-op GPIO backend for hosts with no GPIO reset wiring (e.g. Docker, dev machines)."""

    def set_output(self, pin: int, high: bool) -> None:
        logger.debug("NullGpioController.set_output(pin=%s, high=%s) — no-op", pin, high)

    def pulse_low(self, pin: int, low_seconds: float, settle_seconds: float) -> None:
        logger.debug("NullGpioController.pulse_low(pin=%s) — no-op", pin)
