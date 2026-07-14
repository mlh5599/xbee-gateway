"""Maps remote XBee 64-bit addresses to RemoteDevice instances.

Instance-based (constructed per-app-run / per-test), unlike the legacy
XBeeDeviceManager's class-level `registered_devices` dict, which made isolating test
state from real usage awkward.
"""
from __future__ import annotations

import json
import logging

from xbee_gateway.config.schema import DevicesConfig, DeviceConfig, MqttConfig
from xbee_gateway.discovery.homeassistant import build_discovery_payload
from xbee_gateway.mqtt.client import MqttPort
from xbee_gateway.xbee.models import Channel, ChannelKind, RemoteDevice

logger = logging.getLogger(__name__)


def _channel_from_config(channel_cfg) -> Channel:
    return Channel(
        io_line=channel_cfg.io_line,
        name=channel_cfg.name,
        kind=ChannelKind(channel_cfg.kind),
        unit_of_measurement=channel_cfg.unit_of_measurement,
        device_class=channel_cfg.device_class,
        value_template=channel_cfg.value_template,
        threshold=channel_cfg.threshold,
        hysteresis=channel_cfg.hysteresis,
        above_threshold_payload=channel_cfg.above_threshold_payload,
        below_threshold_payload=channel_cfg.below_threshold_payload,
        payload_on=channel_cfg.payload_on,
        payload_off=channel_cfg.payload_off,
    )


def _device_from_config(device_cfg: DeviceConfig) -> RemoteDevice:
    channels: dict[str, list[Channel]] = {}
    seen_slugs: dict[str, str] = {}
    for channel_cfg in device_cfg.channels:
        channel = _channel_from_config(channel_cfg)
        slug = channel.slug()
        if slug in seen_slugs:
            raise ValueError(
                f"Device {device_cfg.address!r} has two channels that both resolve to "
                f"slug {slug!r} ({seen_slugs[slug]!r} and {channel.name!r}) — entity "
                "names must be unique per device."
            )
        seen_slugs[slug] = channel.name
        channels.setdefault(channel.io_line, []).append(channel)
    return RemoteDevice(
        address=device_cfg.address,
        name=device_cfg.name,
        manufacturer=device_cfg.manufacturer,
        model=device_cfg.model,
        channels=channels,
    )


def _synthesize_device(address: str, io_sample) -> RemoteDevice:
    """Generic device/channels for an IO sample from an address not in devices.json.

    Preserves the currently-running legacy gateway's "any device that talks gets
    registered" behavior out of the box when auto_register_unknown_devices is set.
    """
    channels: dict[str, list[Channel]] = {}
    if io_sample.has_analog_values():
        for line in io_sample.analog_values:
            channels[line.name] = [
                Channel(io_line=line.name, name=line.name, kind=ChannelKind.ANALOG)
            ]
    if io_sample.has_digital_values():
        for line in io_sample.digital_values:
            channels[line.name] = [
                Channel(io_line=line.name, name=line.name, kind=ChannelKind.DIGITAL_BINARY)
            ]
    return RemoteDevice(
        address=address,
        name=f"XBee {address}",
        channels=channels,
        auto_registered=True,
    )


class DeviceRegistry:
    def __init__(self, devices_config: DevicesConfig, mqtt: MqttPort, mqtt_config: MqttConfig):
        self._mqtt = mqtt
        self._mqtt_config = mqtt_config
        self._auto_register = devices_config.auto_register_unknown_devices
        self._devices: dict[str, RemoteDevice] = {}
        for device_cfg in devices_config.devices:
            device = _device_from_config(device_cfg)
            self._devices[device.address] = device
            self._publish_discovery(device)

    def get(self, address: str) -> RemoteDevice | None:
        return self._devices.get(address)

    def get_or_auto_register(self, address: str, io_sample) -> RemoteDevice | None:
        device = self._devices.get(address)
        if device is not None:
            return device

        if not self._auto_register:
            logger.warning("Ignoring IO sample from unconfigured device %s", address)
            return None

        device = _synthesize_device(address, io_sample)
        self._devices[address] = device
        logger.warning("Auto-registered unconfigured device %s", address)
        self._publish_discovery(device)
        return device

    def _publish_discovery(self, device: RemoteDevice) -> None:
        for channels in device.channels.values():
            for channel in channels:
                topic, payload = build_discovery_payload(device, channel, self._mqtt_config)
                self._mqtt.publish(topic, json.dumps(payload), qos=1, retain=True)
