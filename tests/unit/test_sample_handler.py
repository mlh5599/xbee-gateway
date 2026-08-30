from digi.xbee.io import IOValue

from xbee_gateway.config.schema import ChannelConfig, DeviceConfig, DevicesConfig
from xbee_gateway.xbee.device_registry import DeviceRegistry
from xbee_gateway.xbee.sample_handler import IOSampleHandler

from conftest import FakeIOSample, FakeRemoteXBee


def _handler(fake_mqtt, mqtt_config, channel_kind="analog", clock=None, **channel_kwargs):
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
    if clock is None:
        return IOSampleHandler(registry, fake_mqtt, mqtt_config)
    return IOSampleHandler(registry, fake_mqtt, mqtt_config, clock=clock)


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
        fake_mqtt,
        mqtt_config,
        channel_kind="analog_threshold_binary",
        on_threshold=50,
        off_threshold=50,
    )
    fake_mqtt.published.clear()

    remote = FakeRemoteXBee("0013A20012345678")
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 100}), remote)  # >= on_threshold -> ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 90}), remote)  # still on -> no publish
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 10}), remote)  # <= off_threshold -> OFF

    state_publishes = [p for p in fake_mqtt.published if p[0].endswith("/state")]
    assert len(state_publishes) == 2
    assert state_publishes[0][1] == "ON"
    assert state_publishes[1][1] == "OFF"


def test_threshold_binary_hold_band_suppresses_flapping(fake_mqtt, mqtt_config):
    handler = _handler(
        fake_mqtt,
        mqtt_config,
        channel_kind="analog_threshold_binary",
        on_threshold=50,
        off_threshold=40,
    )
    fake_mqtt.published.clear()

    remote = FakeRemoteXBee("0013A20012345678")
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 60}), remote)  # >= 50 -> ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 45}), remote)  # hold band -> stays ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 42}), remote)  # hold band -> stays ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 38}), remote)  # <= 40 -> OFF

    state_publishes = [p for p in fake_mqtt.published if p[0].endswith("/state")]
    assert len(state_publishes) == 2
    assert state_publishes[0][1] == "ON"
    assert state_publishes[1][1] == "OFF"


def test_threshold_binary_hold_band_irrelevant_until_on_threshold_crossed(
    fake_mqtt, mqtt_config
):
    handler = _handler(
        fake_mqtt,
        mqtt_config,
        channel_kind="analog_threshold_binary",
        on_threshold=50,
        off_threshold=40,
    )
    fake_mqtt.published.clear()

    remote = FakeRemoteXBee("0013A20012345678")
    # Never reaches on_threshold (50), so the hold band (40-50) can't hold it ON.
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
        on_threshold=525,
        off_threshold=535,
        direction="below",
    )
    fake_mqtt.published.clear()

    remote = FakeRemoteXBee("0013A20012345678")
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 380}), remote)  # <= 525 -> ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 530}), remote)  # hold band -> stays ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 670}), remote)  # >= 535 -> OFF

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


def _state_payloads(fake_mqtt):
    return [p[1] for p in fake_mqtt.published if p[0].endswith("/state")]


def _below_timeout_handler(fake_mqtt, mqtt_config, clock):
    # NTC pipe-temp channel: raw ADC falls as the pipe heats. A real shower slams the
    # reading well past on_threshold; crosstalk from a nearby pipe only nudges it into
    # the hold band, where band_timeout_seconds must eventually release it.
    return _handler(
        fake_mqtt,
        mqtt_config,
        channel_kind="analog_threshold_binary",
        clock=clock,
        on_threshold=550,
        off_threshold=640,
        direction="below",
        band_timeout_seconds=60,
    )


def test_band_timeout_releases_channel_stuck_in_hold_band(fake_mqtt, mqtt_config, fake_clock):
    handler = _below_timeout_handler(fake_mqtt, mqtt_config, fake_clock)
    fake_mqtt.published.clear()
    remote = FakeRemoteXBee("0013A20012345678")

    handler.handle_io_sample(FakeIOSample(analog={"AD1": 545}), remote)  # <= 550 -> ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 600}), remote)  # drifts into hold band
    fake_clock.advance(30)
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 605}), remote)  # 30s < 60s -> still ON
    fake_clock.advance(40)
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 610}), remote)  # 70s in band -> released

    assert _state_payloads(fake_mqtt) == ["ON", "OFF"]


def test_band_timeout_does_not_release_while_reading_stays_past_on_threshold(
    fake_mqtt, mqtt_config, fake_clock
):
    handler = _below_timeout_handler(fake_mqtt, mqtt_config, fake_clock)
    fake_mqtt.published.clear()
    remote = FakeRemoteXBee("0013A20012345678")

    handler.handle_io_sample(FakeIOSample(analog={"AD1": 400}), remote)  # real shower -> ON
    fake_clock.advance(120)
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 380}), remote)  # still hot, not in band
    fake_clock.advance(600)
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 350}), remote)  # still hot

    assert _state_payloads(fake_mqtt) == ["ON"]  # never released while genuinely triggered


def test_off_threshold_release_is_immediate_and_ignores_band_timer(
    fake_mqtt, mqtt_config, fake_clock
):
    handler = _below_timeout_handler(fake_mqtt, mqtt_config, fake_clock)
    fake_mqtt.published.clear()
    remote = FakeRemoteXBee("0013A20012345678")

    handler.handle_io_sample(FakeIOSample(analog={"AD1": 400}), remote)  # ON
    fake_clock.advance(10)
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 650}), remote)  # >= 640 -> OFF at 10s

    assert _state_payloads(fake_mqtt) == ["ON", "OFF"]


def test_band_timeout_fires_on_tick_without_a_new_sample(fake_mqtt, mqtt_config, fake_clock):
    handler = _below_timeout_handler(fake_mqtt, mqtt_config, fake_clock)
    fake_mqtt.published.clear()
    remote = FakeRemoteXBee("0013A20012345678")

    handler.handle_io_sample(FakeIOSample(analog={"AD1": 545}), remote)  # ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 600}), remote)  # into hold band
    handler.tick()  # 0s elapsed -> no change
    assert _state_payloads(fake_mqtt) == ["ON"]

    fake_clock.advance(70)
    handler.tick()  # device has gone silent, but the timeout still releases it

    assert _state_payloads(fake_mqtt) == ["ON", "OFF"]


def test_no_band_timeout_configured_leaves_stuck_channel_latched(
    fake_mqtt, mqtt_config, fake_clock
):
    handler = _handler(
        fake_mqtt,
        mqtt_config,
        channel_kind="analog_threshold_binary",
        clock=fake_clock,
        on_threshold=550,
        off_threshold=640,
        direction="below",
    )
    fake_mqtt.published.clear()
    remote = FakeRemoteXBee("0013A20012345678")

    handler.handle_io_sample(FakeIOSample(analog={"AD1": 400}), remote)  # ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 600}), remote)  # hold band
    fake_clock.advance(100_000)
    handler.tick()
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 600}), remote)

    assert _state_payloads(fake_mqtt) == ["ON"]  # pure hysteresis: still latched


def test_band_timeout_applies_to_above_direction(fake_mqtt, mqtt_config, fake_clock):
    handler = _handler(
        fake_mqtt,
        mqtt_config,
        channel_kind="analog_threshold_binary",
        clock=fake_clock,
        on_threshold=50,
        off_threshold=40,
        band_timeout_seconds=60,
    )
    fake_mqtt.published.clear()
    remote = FakeRemoteXBee("0013A20012345678")

    handler.handle_io_sample(FakeIOSample(analog={"AD1": 60}), remote)  # >= 50 -> ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 45}), remote)  # hold band (40-50)
    fake_clock.advance(70)
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 45}), remote)  # 70s in band -> released

    assert _state_payloads(fake_mqtt) == ["ON", "OFF"]


def test_channel_can_re_arm_after_a_band_timeout_release(fake_mqtt, mqtt_config, fake_clock):
    handler = _below_timeout_handler(fake_mqtt, mqtt_config, fake_clock)
    fake_mqtt.published.clear()
    remote = FakeRemoteXBee("0013A20012345678")

    handler.handle_io_sample(FakeIOSample(analog={"AD1": 545}), remote)  # ON
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 600}), remote)  # hold band
    fake_clock.advance(70)
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 600}), remote)  # timeout -> OFF
    handler.handle_io_sample(FakeIOSample(analog={"AD1": 400}), remote)  # fresh trip -> ON again

    assert _state_payloads(fake_mqtt) == ["ON", "OFF", "ON"]
