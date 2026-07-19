"""Composition root — replaces the legacy XBee2MQTT.py.

The only place that decides which concrete implementation of each hardware/network
boundary (GpioController, MqttPort, XBeeRadioPort) to use, based on config — never
platform-sniffed.
"""
from __future__ import annotations

import argparse
import logging
import os

from xbee_gateway.config.loader import ConfigStore
from xbee_gateway.gpio import build_gpio_controller
from xbee_gateway.logging_setup import setup_logging
from xbee_gateway.mqtt.client import PahoMqttClient
from xbee_gateway.signals import install_signal_handlers
from xbee_gateway.xbee.coordinator import CoordinatorService
from xbee_gateway.xbee.device_registry import DeviceRegistry
from xbee_gateway.xbee.radio_port import DigiXBeeRadioPort
from xbee_gateway.xbee.sample_handler import IOSampleHandler

logger = logging.getLogger(__name__)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="XBee to MQTT gateway")
    parser.add_argument(
        "--config",
        default=os.environ.get("XBEE_GATEWAY_CONFIG", "config.json"),
        help="Path to config.json (default: %(default)s, or XBEE_GATEWAY_CONFIG env var)",
    )
    parser.add_argument(
        "--devices",
        default=os.environ.get("XBEE_GATEWAY_DEVICES", "devices.json"),
        help="Path to devices.json (default: %(default)s, or XBEE_GATEWAY_DEVICES env var)",
    )
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    config = ConfigStore.load_app_config(args.config)
    devices_config = ConfigStore.load_devices_config(args.devices)

    setup_logging(config.logging.level)

    gpio = build_gpio_controller(config.coordinator.gpio_backend, config.coordinator)

    mqtt = PahoMqttClient(config.mqtt)
    mqtt.connect()

    registry = DeviceRegistry(devices_config, mqtt, config.mqtt)
    sample_handler = IOSampleHandler(registry, mqtt, config.mqtt)

    radio = DigiXBeeRadioPort(config.coordinator.serial_port, config.coordinator.baud_rate)
    coordinator = CoordinatorService(radio, config.coordinator, gpio)
    coordinator.initialize()
    coordinator.set_io_sample_callback(sample_handler.handle_io_sample)

    stop_event = install_signal_handlers()
    logger.info("xbee-gateway running, press Ctrl+C to stop")
    stop_event.wait()

    logger.info("Shutting down")
    mqtt.publish_availability(online=False)
    coordinator.close()
    mqtt.disconnect()


if __name__ == "__main__":
    main()
