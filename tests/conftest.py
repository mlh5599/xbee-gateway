import pytest

from xbee_gateway.config.schema import MqttConfig


class FakeMqttPort:
    def __init__(self):
        self.published = []
        self.connected = False
        self.availability = []

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))

    def publish_availability(self, online):
        self.availability.append(online)


class FakeXBeeRadioPort:
    def __init__(self, address="0013A20012345678", parameters=None):
        self._address = address
        self.parameters = dict(parameters or {})
        self.opened = False
        self.closed = False
        self.write_changes_called = False
        self.set_calls = []
        self.callback = None

    def open(self):
        self.opened = True

    def close(self):
        self.closed = True

    def get_64bit_addr(self):
        return self._address

    def get_parameter(self, at_command):
        return self.parameters.get(at_command, b"")

    def set_parameter(self, at_command, value):
        self.parameters[at_command] = value
        self.set_calls.append((at_command, value))

    def write_changes(self):
        self.write_changes_called = True

    def add_io_sample_received_callback(self, callback):
        self.callback = callback


class FakeGpioController:
    def __init__(self):
        self.pulses = []

    def set_output(self, pin, high):
        pass

    def pulse_low(self, pin, low_seconds, settle_seconds):
        self.pulses.append(pin)


class FakeRemoteXBee:
    def __init__(self, address):
        self._address = address

    def get_64bit_addr(self):
        return self._address


class FakeIOLine:
    """Duck-types the one attribute of digi.xbee.io.IOLine that sample_handler
    relies on (`.name`) — real IOLine keys stringify as "IOLine.DIO3_AD3", not
    "DIO3_AD3", which is why production code must use `.name`, not `str()`.
    """

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"FakeIOLine({self.name!r})"


class FakeIOSample:
    def __init__(self, analog=None, digital=None):
        self.analog_values = {FakeIOLine(k): v for k, v in (analog or {}).items()}
        self.digital_values = {FakeIOLine(k): v for k, v in (digital or {}).items()}

    def has_analog_values(self):
        return bool(self.analog_values)

    def has_digital_values(self):
        return bool(self.digital_values)


@pytest.fixture
def fake_mqtt():
    return FakeMqttPort()


@pytest.fixture
def fake_radio():
    return FakeXBeeRadioPort()


@pytest.fixture
def fake_gpio():
    return FakeGpioController()


@pytest.fixture
def mqtt_config():
    return MqttConfig()
