import json

import pytest

from xbee_gateway.config.schema import ChannelConfig, DeviceConfig, DevicesConfig
from xbee_gateway.xbee.device_registry import DeviceRegistry

from conftest import FakeIOLine


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


def test_channels_sharing_an_io_line_both_get_discovery_published(fake_mqtt, mqtt_config):
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

    registry = DeviceRegistry(devices_config, fake_mqtt, mqtt_config)

    device = registry.get("0013A20012345678")
    assert len(device.channels["DIO1_AD1"]) == 2
    assert len(fake_mqtt.published) == 2

    topics = [t for t, _, _, _ in fake_mqtt.published]
    assert any("/binary_sensor/" in t for t in topics)
    assert any("/sensor/" in t for t in topics)

    device_blocks = [json.loads(p)["device"]["identifiers"] for _, p, _, _ in fake_mqtt.published]
    assert device_blocks[0] == device_blocks[1] == ["xbee-0x0013A20012345678"]


def test_duplicate_channel_names_on_one_device_raise(fake_mqtt, mqtt_config):
    devices_config = DevicesConfig(
        devices=[
            DeviceConfig(
                address="0013A20012345678",
                name="Shower Monitor",
                channels=[
                    ChannelConfig(
                        io_line="DIO1_AD1", name="Shower", kind="analog_threshold_binary"
                    ),
                    ChannelConfig(
                        io_line="DIO2_AD2", name="Shower", kind="analog_threshold_binary"
                    ),
                ],
            )
        ],
        auto_register_unknown_devices=False,
    )

    with pytest.raises(ValueError, match="slug"):
        DeviceRegistry(devices_config, fake_mqtt, mqtt_config)


def test_unknown_device_ignored_when_auto_register_disabled(fake_mqtt, mqtt_config):
    devices_config = DevicesConfig(devices=[], auto_register_unknown_devices=False)
    registry = DeviceRegistry(devices_config, fake_mqtt, mqtt_config)

    class FakeIOSample:
        def has_analog_values(self):
            return True

        analog_values = {FakeIOLine("AD1"): 100}

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

        analog_values = {FakeIOLine("AD1"): 100}

        def has_digital_values(self):
            return False

    device = registry.get_or_auto_register("new-address", FakeIOSample())

    assert device is not None
    assert device.auto_registered is True
    assert registry.get("new-address") is device
    assert len(fake_mqtt.published) == 1  # discovery published for the synthesized channel
