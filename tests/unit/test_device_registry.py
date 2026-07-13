import json

from xbee_gateway.config.schema import ChannelConfig, DeviceConfig, DevicesConfig
from xbee_gateway.xbee.device_registry import DeviceRegistry


def test_explicit_device_publishes_discovery_on_construction(fake_mqtt, mqtt_config):
    devices_config = DevicesConfig(
        devices=[
            DeviceConfig(
                address="0013A20012345678",
                name="Test Device",
                channels=[ChannelConfig(io_line="AD1", name="Moisture", kind="analog")],
            )
        ],
        auto_register_unknown_devices=False,
    )

    registry = DeviceRegistry(devices_config, fake_mqtt, mqtt_config)

    assert registry.get("0013A20012345678") is not None
    assert len(fake_mqtt.published) == 1
    topic, payload, qos, retain = fake_mqtt.published[0]
    assert "sensor" in topic
    assert retain is True
    assert json.loads(payload)["name"] == "Moisture"


def test_unknown_device_ignored_when_auto_register_disabled(fake_mqtt, mqtt_config):
    devices_config = DevicesConfig(devices=[], auto_register_unknown_devices=False)
    registry = DeviceRegistry(devices_config, fake_mqtt, mqtt_config)

    class FakeIOSample:
        def has_analog_values(self):
            return True

        analog_values = {"AD1": 100}

        def has_digital_values(self):
            return False

    device = registry.get_or_auto_register("unknown-address", FakeIOSample())

    assert device is None
    assert fake_mqtt.published == []


def test_unknown_device_auto_registered_when_enabled(fake_mqtt, mqtt_config):
    devices_config = DevicesConfig(devices=[], auto_register_unknown_devices=True)
    registry = DeviceRegistry(devices_config, fake_mqtt, mqtt_config)

    class FakeIOSample:
        def has_analog_values(self):
            return True

        analog_values = {"AD1": 100}

        def has_digital_values(self):
            return False

    device = registry.get_or_auto_register("new-address", FakeIOSample())

    assert device is not None
    assert device.auto_registered is True
    assert registry.get("new-address") is device
    assert len(fake_mqtt.published) == 1  # discovery published for the synthesized channel
