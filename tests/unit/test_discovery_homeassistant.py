from xbee_gateway.discovery.homeassistant import build_discovery_payload
from xbee_gateway.xbee.models import Channel, ChannelKind, RemoteDevice


def _device():
    return RemoteDevice(address="0013A20012345678", name="Test Device")


def test_analog_channel_maps_to_sensor_component(mqtt_config):
    channel = Channel(
        io_line="AD1",
        name="Soil Moisture",
        kind=ChannelKind.ANALOG,
        unit_of_measurement="%",
        device_class="moisture",
    )

    topic, payload = build_discovery_payload(_device(), channel, mqtt_config)

    assert topic.startswith(f"{mqtt_config.discovery_prefix}/sensor/")
    assert payload["unit_of_measurement"] == "%"
    assert payload["device_class"] == "moisture"
    assert "payload_on" not in payload


def test_threshold_binary_channel_maps_to_binary_sensor_component(mqtt_config):
    channel = Channel(io_line="AD2", name="Water Present", kind=ChannelKind.ANALOG_THRESHOLD_BINARY)

    topic, payload = build_discovery_payload(_device(), channel, mqtt_config)

    assert topic.startswith(f"{mqtt_config.discovery_prefix}/binary_sensor/")
    assert payload["payload_on"] == "ON"
    assert "unit_of_measurement" not in payload


def test_digital_binary_channel_maps_to_binary_sensor_component(mqtt_config):
    channel = Channel(io_line="DIO3", name="Door Sensor", kind=ChannelKind.DIGITAL_BINARY)

    topic, payload = build_discovery_payload(_device(), channel, mqtt_config)

    assert topic.startswith(f"{mqtt_config.discovery_prefix}/binary_sensor/")


def test_payload_always_includes_availability(mqtt_config):
    channel = Channel(io_line="AD1", name="Soil Moisture", kind=ChannelKind.ANALOG)

    _, payload = build_discovery_payload(_device(), channel, mqtt_config)

    assert payload["availability_topic"] == mqtt_config.availability_topic
    assert payload["payload_available"] == "online"
    assert payload["payload_not_available"] == "offline"


def test_unique_id_and_device_block_present(mqtt_config):
    device = _device()
    channel = Channel(io_line="AD1", name="Soil Moisture", kind=ChannelKind.ANALOG)

    _, payload = build_discovery_payload(device, channel, mqtt_config)

    assert payload["unique_id"] == f"xbee-0x{device.address}-{channel.slug()}"
    assert payload["device"]["identifiers"] == [f"xbee-0x{device.address}"]
