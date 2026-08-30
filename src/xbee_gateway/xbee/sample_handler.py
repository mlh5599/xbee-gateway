"""Routes incoming XBee IO samples to MQTT state publishes.

Replaces the logic previously spread across RemoteSensorDevice.py / XBeeDeviceManager.py.
Analog readings publish every sample (a raw sensor stream); thresholded/digital channels
only publish on a debounced state change, matching the legacy gateway's behavior.
"""
from __future__ import annotations

import logging
import time
from typing import Callable

from digi.xbee.io import IOValue

from xbee_gateway.config.schema import MqttConfig
from xbee_gateway.mqtt.client import MqttPort
from xbee_gateway.xbee.device_registry import DeviceRegistry
from xbee_gateway.xbee.models import Channel, ChannelKind

logger = logging.getLogger(__name__)


class IOSampleHandler:
    def __init__(
        self,
        registry: DeviceRegistry,
        mqtt: MqttPort,
        mqtt_config: MqttConfig,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._registry = registry
        self._mqtt = mqtt
        self._mqtt_config = mqtt_config
        self._clock = clock

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

    def tick(self) -> None:
        """Advance time-based threshold transitions without a fresh IO sample.

        The hold-band timeout (`band_timeout_seconds`) must be able to fire even if
        the end device has gone quiet while sitting in the band — otherwise a stuck
        channel with no incoming samples would never be re-evaluated. Called on a
        periodic tick from the app loop; a no-op for every channel that isn't a
        currently-triggered analog_threshold_binary with a known last reading.
        """
        for device in self._registry.all_devices():
            for channels in device.channels.values():
                for channel in channels:
                    if (
                        channel.kind is ChannelKind.ANALOG_THRESHOLD_BINARY
                        and channel.triggered
                        and channel.last_raw is not None
                    ):
                        self._publish_single_channel(device, channel, channel.last_raw)

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
            channel.last_raw = raw_value
            self._advance_threshold_state(channel, raw_value)
            payload = (
                channel.above_threshold_payload
                if channel.triggered
                else channel.below_threshold_payload
            )
        else:  # DIGITAL_BINARY
            payload = channel.payload_on if raw_value == IOValue.HIGH else channel.payload_off

        if payload == channel.last_value:
            return
        channel.last_value = payload
        self._mqtt.publish(topic, payload, qos=1, retain=True)

    def _advance_threshold_state(self, channel: Channel, raw_value) -> None:
        """One step of the analog_threshold_binary state machine.

        Two independent setpoints, not one threshold + deadband: turn ON as soon as
        the reading passes `on_threshold` (set close to the resting level so a slow
        ramp trips early), hold state through the band, turn OFF once it comes back
        past `off_threshold`. `direction: "below"` is the NTC case, where the raw ADC
        reading falls as the monitored condition heats up.

        `band_timeout_seconds` is the failsafe against a latch that never clears: a
        real event drives the reading well past `on_threshold` and holds it there,
        so it never lingers in the hold band. Anything that trips `on_threshold` but
        then just sits in the band (crosstalk warming the pipe, sensor drift, a
        now-silent device) is released once the timeout elapses.

        After a `band_timeout_seconds` release the channel is left `suppressed`: the
        reading is still on the triggered side of `on_threshold`, and if it wobbles
        across the setpoint (crosstalk plus ADC noise) each re-cross would otherwise
        re-trip ON, time out again, and flap the state on a ~`band_timeout` cycle.
        While suppressed a lone on-side sample is ignored; it takes two consecutive
        on-side samples to re-arm (a real event holds the reading there), or one
        sample back past `off_threshold` to clear the suppression with the state OFF.
        """
        on_at, off_at = channel.on_threshold, channel.off_threshold

        if channel.direction == "below":
            crossed_on = on_at is not None and raw_value <= on_at
            crossed_off = off_at is not None and raw_value >= off_at
            in_band = on_at is not None and raw_value >= on_at and not crossed_off
        else:
            crossed_on = on_at is not None and raw_value >= on_at
            crossed_off = off_at is not None and raw_value <= off_at
            in_band = on_at is not None and raw_value <= on_at and not crossed_off

        if not channel.triggered:
            if crossed_off:
                # Recovered past off_threshold — any post-timeout suppression is done.
                channel.suppressed = False
                channel.recross_seen = False
            elif crossed_on:
                if channel.suppressed and not channel.recross_seen:
                    # First on-side sample since a band_timeout release. Treat it as
                    # more of the same crosstalk/noise; wait for a second one in a row.
                    channel.recross_seen = True
                    return
                channel.triggered = True
                channel.triggered_at = self._clock()
                channel.suppressed = False
                channel.recross_seen = False
            elif channel.suppressed:
                # Drifted back into the band without recovering; the on-side streak is
                # broken, so re-arming needs two fresh consecutive on-side samples.
                channel.recross_seen = False
            return

        if crossed_off:
            channel.triggered = False
            channel.triggered_at = None
            return

        if (
            channel.band_timeout_seconds is not None
            and in_band
            and channel.triggered_at is not None
            and self._clock() - channel.triggered_at >= channel.band_timeout_seconds
        ):
            logger.info(
                "Channel %r stuck in hold band for >= %ss without reaching off_threshold "
                "(last raw=%s); releasing as a false trigger and suppressing re-trigger "
                "until it recovers or trips twice in a row",
                channel.name,
                channel.band_timeout_seconds,
                raw_value,
            )
            channel.triggered = False
            channel.triggered_at = None
            channel.suppressed = True
            channel.recross_seen = False
