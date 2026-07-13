import time


class PigpioController:
    """Real GpioController implementation, wrapping pigpio (requires pigpiod running)."""

    def __init__(self, coordinator_config):
        import pigpio

        self._pigpio = pigpio
        self._pi = pigpio.pi()
        if not self._pi.connected:
            raise RuntimeError("Could not connect to pigpiod — is it running?")

    def set_output(self, pin: int, high: bool) -> None:
        self._pi.set_mode(pin, self._pigpio.OUTPUT)
        self._pi.write(pin, self._pigpio.HIGH if high else self._pigpio.LOW)

    def pulse_low(self, pin: int, low_seconds: float, settle_seconds: float) -> None:
        self.set_output(pin, high=False)
        time.sleep(low_seconds)
        self.set_output(pin, high=True)
        time.sleep(settle_seconds)
