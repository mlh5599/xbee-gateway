"""Load/save AppConfig and DevicesConfig, with environment variable overrides.

Env override convention: XBEE_GATEWAY_<SECTION>__<KEY> (double underscore = nesting),
e.g. XBEE_GATEWAY_MQTT__HOST, XBEE_GATEWAY_MQTT__PASSWORD. Always wins over the file —
this is the mechanism that keeps secrets out of committed/example config entirely.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from xbee_gateway.config.schema import (
    ATSetting,
    AppConfig,
    ChannelConfig,
    CoordinatorConfig,
    DeviceConfig,
    DevicesConfig,
    LoggingConfig,
    MqttConfig,
)

ENV_PREFIX = "XBEE_GATEWAY_"


def _apply_env_overrides(data: dict[str, Any], prefix: str = ENV_PREFIX) -> dict[str, Any]:
    """Overlay matching XBEE_GATEWAY_<SECTION>__<KEY> env vars onto a nested dict."""
    for env_key, env_value in os.environ.items():
        if not env_key.startswith(prefix):
            continue
        path = env_key[len(prefix):].lower().split("__")
        target = data
        for part in path[:-1]:
            target = target.setdefault(part, {})
        target[path[-1]] = env_value
    return data


def _load_json(path: Path) -> dict[str, Any]:
    with open(path, "r") as fh:
        return json.load(fh)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
        os.replace(tmp_path, path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def _app_config_from_dict(data: dict[str, Any]) -> AppConfig:
    mqtt_data = data.get("mqtt", {})
    coordinator_data = data.get("coordinator", {})
    logging_data = data.get("logging", {})

    at_settings = {
        name: ATSetting(**settings)
        for name, settings in coordinator_data.get("at_settings", {}).items()
    }

    coordinator = CoordinatorConfig(
        **{k: v for k, v in coordinator_data.items() if k != "at_settings"},
        at_settings=at_settings,
    )

    return AppConfig(
        mqtt=MqttConfig(**mqtt_data),
        coordinator=coordinator,
        logging=LoggingConfig(**logging_data),
    )


def _devices_config_from_dict(data: dict[str, Any]) -> DevicesConfig:
    devices = []
    for device_data in data.get("devices", []):
        channels = [ChannelConfig(**c) for c in device_data.get("channels", [])]
        devices.append(
            DeviceConfig(
                **{k: v for k, v in device_data.items() if k != "channels"},
                channels=channels,
            )
        )
    return DevicesConfig(
        devices=devices,
        auto_register_unknown_devices=data.get("auto_register_unknown_devices", True),
    )


class ConfigStore:
    """Loads/saves AppConfig + DevicesConfig from JSON files plus env overrides."""

    @staticmethod
    def load_app_config(config_path: str | Path) -> AppConfig:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Config file not found: {path}. Copy config/config.example.json to get started."
            )
        data = _apply_env_overrides(_load_json(path))
        return _app_config_from_dict(data)

    @staticmethod
    def load_devices_config(devices_path: str | Path) -> DevicesConfig:
        path = Path(devices_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Devices file not found: {path}. Copy config/devices.example.json to get started."
            )
        return _devices_config_from_dict(_load_json(path))

    @staticmethod
    def save_devices_config(devices_path: str | Path, devices: DevicesConfig) -> None:
        _atomic_write_json(Path(devices_path), asdict(devices))
