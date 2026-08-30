"""Routes incoming XBee IO samples to MQTT state publishes.

Replaces the logic previously spread across RemoteSensorDevice.py / XBeeDeviceManager.py.
Analog readings publish every sample (a raw sensor stream); thresholded/digital channels
only publish on a debounced state change, matching the legacy gateway's behavior.
"""
from __future__ import annotations

from digi.xbee.io import IOValue

from xbee_gateway.config.schema import MqttConfig
from xbee_gateway.mqtt.client import MqttPort
from xbee_gateway.xbee.device_registry import DeviceRegistry
from xbee_gateway.xbee.models import ChannelKind


class IOSampleHandler:
    def __init__(self, registry: DeviceRegistry, mqtt: MqttPort, mqtt_config: MqttConfig):
        self._registry = registry
        self._mqtt = mqtt
        self._mqtt_config = mqtt_config

    def handle_io_sample(self, io_sample, remote_xbee, send_time=None) -> None:
        address = str(remote_xbee.get_64bit_addr())
        device = self._registry.get_or_auto_register(address, io_sample)
        if device is None:
            return

        if io_sample.has_analog_values():
            for line, raw_value in io_sample.analog_values.items():
                self._publish_channel_value(device, line.name, raw_value)

        if io_sample.has_digital_values():
            for line, raw_value in io_sample.digital_values.items():
                self._publish_channel_value(device, line.name, raw_value)

    def _publish_channel_value(self, device, io_line: str, raw_value) -> None:
        channels = device.channels.get(io_line)
        if not channels:
            return

        for channel in channels:
            self._publish_single_channel(device, channel, raw_value)

    def _publish_single_channel(self, device, channel, raw_value) -> None:
        topic = channel.state_topic(self._mqtt_config.base_topic, device.address)

        if channel.kind is ChannelKind.ANALOG:
            channel.last_value = raw_value
            self._mqtt.publish(topic, raw_value, qos=0, retain=False)
            return

        if channel.kind is ChannelKind.ANALOG_THRESHOLD_BINARY:
            # Two independent setpoints, not one threshold + deadband: turn ON as soon as
            # the reading passes `on_threshold` (set close to the resting level so a slow
            # ramp trips early), hold state through the band, turn OFF once it comes back
            # past `off_threshold`. `direction: "below"` is the NTC case, where the raw ADC
            # reading falls as the monitored condition heats up.
            on_at, off_at = channel.on_threshold, channel.off_threshold
            if not channel.triggered:
                if channel.direction == "below":
                    crossed_on = on_at is not None and raw_value <= on_at
                else:
                    crossed_on = on_at is not None and raw_value >= on_at
                if crossed_on:
                    channel.triggered = True
            else:
                if channel.direction == "below":
                    crossed_off = off_at is not None and raw_value >= off_at
                else:
                    crossed_off = off_at is not None and raw_value <= off_at
                if crossed_off:
                    channel.triggered = False
            triggered = bool(channel.triggered)
            payload = (
                channel.above_threshold_payload if triggered else channel.below_threshold_payload
            )
        else:  # DIGITAL_BINARY
            payload = channel.payload_on if raw_value == IOValue.HIGH else channel.payload_off

        if payload == channel.last_value:
            return
        channel.last_value = payload
        self._mqtt.publish(topic, payload, qos=1, retain=True)
