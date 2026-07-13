"""Home Assistant MQTT discovery payload construction.

The core correctness fix over the legacy gateway: every channel used to be published as
a `binary_sensor`, even raw analog ADC values, and no availability_topic was ever set.
`build_discovery_payload` is a pure function (no MQTT client dependency) so it's trivially
unit-testable with plain dict assertions.
"""
from __future__ import annotations

from xbee_gateway.config.schema import MqttConfig
from xbee_gateway.xbee.models import Channel, ChannelKind, RemoteDevice

COMPONENT_FOR_KIND = {
    ChannelKind.ANALOG: "sensor",
    ChannelKind.ANALOG_THRESHOLD_BINARY: "binary_sensor",
    ChannelKind.DIGITAL_BINARY: "binary_sensor",
}


def build_discovery_payload(
    device: RemoteDevice, channel: Channel, mqtt_config: MqttConfig
) -> tuple[str, dict]:
    """Return (discovery_topic, discovery_payload) for one device channel."""
    component = COMPONENT_FOR_KIND[channel.kind]
    topic = (
        f"{mqtt_config.discovery_prefix}/{component}/xbee-0x{device.address}/"
        f"{channel.slug()}/config"
    )

    payload: dict = {
        "name": channel.name,
        "unique_id": f"xbee-0x{device.address}-{channel.slug()}",
        "state_topic": channel.state_topic(mqtt_config.base_topic, device.address),
        "availability_topic": mqtt_config.availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "device": {
            "identifiers": [f"xbee-0x{device.address}"],
            "manufacturer": device.manufacturer,
            "model": device.model,
            "name": device.name,
        },
    }

    if channel.kind is ChannelKind.ANALOG:
        if channel.unit_of_measurement:
            payload["unit_of_measurement"] = channel.unit_of_measurement
        if channel.value_template:
            payload["value_template"] = channel.value_template
        if channel.device_class:
            payload["device_class"] = channel.device_class
    else:
        payload["payload_on"] = channel.payload_on
        payload["payload_off"] = channel.payload_off
        if channel.device_class:
            payload["device_class"] = channel.device_class

    return topic, payload
