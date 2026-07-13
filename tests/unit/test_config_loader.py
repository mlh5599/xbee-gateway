import json

import pytest

from xbee_gateway.config.loader import ConfigStore


def _write_json(path, data):
    path.write_text(json.dumps(data))


def test_load_app_config_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        ConfigStore.load_app_config(tmp_path / "missing.json")


def test_load_app_config_parses_sections(tmp_path):
    config_path = tmp_path / "config.json"
    _write_json(
        config_path,
        {
            "mqtt": {"host": "broker.example", "port": 1883},
            "coordinator": {
                "serial_port": "/dev/ttyUSB0",
                "at_settings": {
                    "pan_id": {"at": "ID", "value": "0x2000"},
                },
            },
            "logging": {"level": "DEBUG"},
        },
    )

    config = ConfigStore.load_app_config(config_path)

    assert config.mqtt.host == "broker.example"
    assert config.coordinator.serial_port == "/dev/ttyUSB0"
    assert config.coordinator.at_settings["pan_id"].at == "ID"
    assert config.logging.level == "DEBUG"


def test_env_override_wins_over_file(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    _write_json(config_path, {"mqtt": {"host": "file-value.example"}})

    monkeypatch.setenv("XBEE_GATEWAY_MQTT__HOST", "env-value.example")

    config = ConfigStore.load_app_config(config_path)

    assert config.mqtt.host == "env-value.example"


def test_load_devices_config_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        ConfigStore.load_devices_config(tmp_path / "missing.json")


def test_load_devices_config_parses_channels(tmp_path):
    devices_path = tmp_path / "devices.json"
    _write_json(
        devices_path,
        {
            "auto_register_unknown_devices": False,
            "devices": [
                {
                    "address": "0013A20012345678",
                    "name": "Test Device",
                    "channels": [
                        {"io_line": "AD1", "name": "Moisture", "kind": "analog"},
                    ],
                }
            ],
        },
    )

    devices_config = ConfigStore.load_devices_config(devices_path)

    assert devices_config.auto_register_unknown_devices is False
    assert devices_config.devices[0].address == "0013A20012345678"
    assert devices_config.devices[0].channels[0].kind == "analog"
