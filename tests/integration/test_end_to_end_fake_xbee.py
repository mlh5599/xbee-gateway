"""End-to-end pipeline test wired entirely from fakes: coordinator init -> IO sample
callback -> device registry/discovery -> MQTT publish. Regression test for the legacy
bug class where every discovery entity was published as binary_sensor regardless of
channel kind, and where LWT/availability was never wired up.
"""
from digi.xbee.io import IOValue

from xbee_gateway.config.schema import (
    ATSetting,
    ChannelConfig,
    CoordinatorConfig,
    DeviceConfig,
    DevicesConfig,
    MqttConfig,
)
from xbee_gateway.xbee.coordinator import CoordinatorService
from xbee_gateway.xbee.device_registry import DeviceRegistry
from xbee_gateway.xbee.sample_handler import IOSampleHandler

from conftest import FakeIOSample, FakeRemoteXBee


def test_full_pipeline_publishes_correctly_typed_discovery_and_state(
    fake_mqtt, fake_radio, fake_gpio
):
    mqtt_config = MqttConfig()
    devices_config = DevicesConfig(
        devices=[
            DeviceConfig(
                address="0013A20012345678",
                name="Greenhouse Sensor",
                channels=[
                    ChannelConfig(
                        io_line="AD1", name="Soil Moisture", kind="analog",
                        unit_of_measurement="%",
                    ),
                    ChannelConfig(io_line="DIO3", name="Door", kind="digital_binary"),
                ],
            )
        ],
        auto_register_unknown_devices=True,
    )
    coordinator_config = CoordinatorConfig(
        serial_port="/dev/ttyUSB0",
        baud_rate=9600,
        reset_gpio_pin=-1,
        status_led_gpio_pin=-1,
        gpio_backend="none",
        connect_retry_attempts=3,
        connect_retry_backoff_seconds=0,
        at_settings={"pan_id": ATSetting(at="ID", value="0x2000")},
    )

    registry = DeviceRegistry(devices_config, fake_mqtt, mqtt_config)
    sample_handler = IOSampleHandler(registry, fake_mqtt, mqtt_config)
    coordinator = CoordinatorService(fake_radio, coordinator_config, fake_gpio)
    coordinator.initialize()
    coordinator.set_io_sample_callback(sample_handler.handle_io_sample)

    discovery_publishes = list(fake_mqtt.published)
    assert len(discovery_publishes) == 2
    sensor_topics = [t for t, _, _, _ in discovery_publishes if "/sensor/" in t]
    binary_sensor_topics = [t for t, _, _, _ in discovery_publishes if "/binary_sensor/" in t]
    assert len(sensor_topics) == 1  # analog channel -> sensor, not binary_sensor
    assert len(binary_sensor_topics) == 1  # digital_binary channel -> binary_sensor

    fake_mqtt.published.clear()
    remote = FakeRemoteXBee("0013A20012345678")
    fake_radio.callback(
        FakeIOSample(analog={"AD1": 512}, digital={"DIO3": IOValue.HIGH}), remote
    )

    state_publishes = [p for p in fake_mqtt.published if p[0].endswith("/state")]
    assert len(state_publishes) == 2
    assert fake_radio.set_calls == [("ID", bytes.fromhex("2000"))]


def test_one_io_line_fans_out_to_raw_sensor_and_derived_binary_entity(
    fake_mqtt, fake_radio, fake_gpio
):
    """Shower Monitor scenario: one thermistor (one io_line) backs both a raw ADC
    sensor (every sample) and a hysteresis-debounced running/not-running binary_sensor,
    both grouped under the same HA device.
    """
    mqtt_config = MqttConfig()
    devices_config = DevicesConfig(
        devices=[
            DeviceConfig(
                address="0013A20012345678",
                name="Shower Monitor",
                channels=[
                    ChannelConfig(
                        io_line="DIO1_AD1",
                        name="Master Bathroom Shower",
                        kind="analog_threshold_binary",
                        device_class="running",
                        threshold=600,
                        hysteresis=40,
                    ),
                    ChannelConfig(
                        io_line="DIO1_AD1",
                        name="Master Bathroom Pipe Temp (Raw)",
                        kind="analog",
                    ),
                ],
            )
        ],
        auto_register_unknown_devices=False,
    )
    coordinator_config = CoordinatorConfig(
        serial_port="/dev/ttyUSB0",
        baud_rate=9600,
        reset_gpio_pin=-1,
        status_led_gpio_pin=-1,
        gpio_backend="none",
        connect_retry_attempts=3,
        connect_retry_backoff_seconds=0,
    )

    registry = DeviceRegistry(devices_config, fake_mqtt, mqtt_config)
    sample_handler = IOSampleHandler(registry, fake_mqtt, mqtt_config)
    coordinator = CoordinatorService(fake_radio, coordinator_config, fake_gpio)
    coordinator.initialize()
    coordinator.set_io_sample_callback(sample_handler.handle_io_sample)

    assert len(fake_mqtt.published) == 2  # both entities discovered from one io_line
    fake_mqtt.published.clear()

    remote = FakeRemoteXBee("0013A20012345678")
    fake_radio.callback(FakeIOSample(analog={"DIO1_AD1": 650}), remote)  # above threshold
    fake_radio.callback(FakeIOSample(analog={"DIO1_AD1": 580}), remote)  # within hysteresis band

    state_publishes = [p for p in fake_mqtt.published if p[0].endswith("/state")]
    raw_publishes = [p for p in state_publishes if p[1] == 650 or p[1] == 580]
    binary_publishes = [p for p in state_publishes if p[1] == "ON"]
    assert len(raw_publishes) == 2  # raw sensor publishes every sample
    assert len(binary_publishes) == 1  # binary only publishes on the initial ON transition
