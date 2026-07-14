from digi.xbee.io import IOValue

from xbee_gateway.config.schema import ChannelConfig, DeviceConfig, DevicesConfig
from xbee_gateway.xbee.device_registry import DeviceRegistry
from xbee_gateway.xbee.sample_handler import IOSampleHandler

from conftest import FakeIOSample, FakeRemoteXBee


def _handler(fake_mqtt, mqtt_config, channel_kind="analog", **channel_kwargs):
    devices_config = DevicesConfig(
        devices=[
            DeviceConfig(
                address="0013A20012345678",
                name="Test Device",
                channels=[
                    ChannelConfig(io_line="AD1", name="Chan", kind=channel_kind, **channel_kwargs)
                ],
            )
        ],
        auto_register_unknown_devices=False,
    )
    registry = DeviceRegistry(devices_config, fake_mqtt, mqtt_config)
    return IOSampleHandler(registry, fake_mqtt, mqtt_config)


def test_analog_reading_publishes_every_sample(fake_mqtt, mqtt_config):
    handler = _handler(fake_mqtt, mqtt_config)
    fake_mqtt.published.clear()  # drop the discovery publish from setup

    remote = FakeRemoteXBee("0013A20012345678")
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 100}), remote)
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 100}), remote)

    state_publishes = [p for p in fake_mqtt.published if p[0].endswith("/state")]
    assert len(state_publishes) == 2  # analog values publish every sample, no dedup


def test_threshold_binary_only_publishes_on_change(fake_mqtt, mqtt_config):
    handler = _handler(
        fake_mqtt, mqtt_config, channel_kind="analog_threshold_binary", threshold=50
    )
    fake_mqtt.published.clear()

    remote = FakeRemoteXBee("0013A20012345678")
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 100}), remote)  # above threshold -> ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 90}), remote)  # still above -> no publish
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 10}), remote)  # below -> OFF

    state_publishes = [p for p in fake_mqtt.published if p[0].endswith("/state")]
    assert len(state_publishes) == 2
    assert state_publishes[0][1] == "ON"
    assert state_publishes[1][1] == "OFF"


def test_threshold_binary_hysteresis_suppresses_flapping_near_threshold(fake_mqtt, mqtt_config):
    handler = _handler(
        fake_mqtt, mqtt_config, channel_kind="analog_threshold_binary", threshold=50, hysteresis=10
    )
    fake_mqtt.published.clear()

    remote = FakeRemoteXBee("0013A20012345678")
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 60}), remote)  # above 50 -> ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 45}), remote)  # hysteresis band -> ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 42}), remote)  # still above 40 -> stays ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 38}), remote)  # below 40 -> OFF

    state_publishes = [p for p in fake_mqtt.published if p[0].endswith("/state")]
    assert len(state_publishes) == 2
    assert state_publishes[0][1] == "ON"
    assert state_publishes[1][1] == "OFF"


def test_threshold_binary_hysteresis_still_requires_crossing_threshold_to_turn_on(
    fake_mqtt, mqtt_config
):
    handler = _handler(
        fake_mqtt, mqtt_config, channel_kind="analog_threshold_binary", threshold=50, hysteresis=10
    )
    fake_mqtt.published.clear()

    remote = FakeRemoteXBee("0013A20012345678")
    # Never above 50, so hysteresis band (40-50) is irrelevant while OFF.
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 45}), remote)

    state_publishes = [p for p in fake_mqtt.published if p[0].endswith("/state")]
    assert len(state_publishes) == 1
    assert state_publishes[0][1] == "OFF"


def test_threshold_binary_below_direction_triggers_on_falling_value(fake_mqtt, mqtt_config):
    # NTC thermistor: raw ADC value drops as the tracked condition (hot water) intensifies.
    handler = _handler(
        fake_mqtt,
        mqtt_config,
        channel_kind="analog_threshold_binary",
        threshold=525,
        hysteresis=10,
        direction="below",
    )
    fake_mqtt.published.clear()

    remote = FakeRemoteXBee("0013A20012345678")
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 380}), remote)  # below 525 -> ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 530}), remote)  # hysteresis band -> ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 670}), remote)  # above 535 -> OFF

    state_publishes = [p for p in fake_mqtt.published if p[0].endswith("/state")]
    assert len(state_publishes) == 2
    assert state_publishes[0][1] == "ON"
    assert state_publishes[1][1] == "OFF"


def test_digital_binary_uses_configured_payloads(fake_mqtt, mqtt_config):
    handler = _handler(
        fake_mqtt,
        mqtt_config,
        channel_kind="digital_binary",
        payload_on="OPEN",
        payload_off="CLOSED",
    )
    fake_mqtt.published.clear()

    remote = FakeRemoteXBee("0013A20012345678")
    handler.handle_io_sample(FakeIOSample(digital={"AD1": IOValue.HIGH}), remote)

    state_publishes = [p for p in fake_mqtt.published if p[0].endswith("/state")]
    assert state_publishes[0][1] == "OPEN"


def test_digital_binary_low_value_uses_off_payload(fake_mqtt, mqtt_config):
    # Regression test: digi.xbee.io.IOValue.LOW is a nonzero enum member, so it is
    # truthy in Python — `if raw_value` alone can't distinguish LOW from HIGH.
    handler = _handler(
        fake_mqtt,
        mqtt_config,
        channel_kind="digital_binary",
        payload_on="OPEN",
        payload_off="CLOSED",
    )
    fake_mqtt.published.clear()

    remote = FakeRemoteXBee("0013A20012345678")
    handler.handle_io_sample(FakeIOSample(digital={"AD1": IOValue.LOW}), remote)

    state_publishes = [p for p in fake_mqtt.published if p[0].endswith("/state")]
    assert state_publishes[0][1] == "CLOSED"
