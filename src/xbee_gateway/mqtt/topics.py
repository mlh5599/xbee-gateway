"""Single source of truth for non-discovery topic strings.

Discovery topics are built alongside their payload in discovery/homeassistant.py, since
the component name (sensor vs binary_sensor) is part of the topic itself.
"""
from xbee_gateway.config.schema import MqttConfig


def availability_topic(mqtt_config: MqttConfig) -> str:
    return mqtt_config.availability_topic


def state_topic(mqtt_config: MqttConfig, device_address: str, channel_slug: str) -> str:
    return f"{mqtt_config.base_topic}/{device_address}/{channel_slug}/state"
