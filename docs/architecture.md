# Architecture

## Overview

A single process (`xbee_gateway.app:main`) composed of small, dependency-injected pieces:

```
XBee coordinator radio  --(IO samples)-->  DeviceRegistry  --(publish)-->  MqttPort  --> broker --> Home Assistant
                                                 |
                                                 v
                                    HomeAssistantDiscoveryPublisher
```

- **`xbee/radio_port.py`** (`XBeeRadioPort` protocol) wraps `digi.xbee.devices.XBeeDevice`.
  This is the only module that talks to the real serial port.
- **`xbee/coordinator.py`** (`CoordinatorService`) applies the configured AT-command
  settings (PAN ID, encryption, channel scan, DIO/ADC pin modes, etc.) to the local
  coordinator radio at startup, with retry/backoff.
- **`xbee/device_registry.py`** (`DeviceRegistry`) maps a remote XBee 64-bit address to a
  `RemoteDevice` (from `devices.json`, or auto-registered on first contact if
  `auto_register_unknown_devices` is set).
- **`xbee/sample_handler.py`** (`IOSampleHandler`) receives IO samples from the coordinator
  callback, resolves the device via the registry, and publishes channel state.
- **`discovery/homeassistant.py`** builds Home Assistant MQTT discovery payloads. Channel
  `kind` determines the HA component: `analog` → `sensor`, `analog_threshold_binary` /
  `digital_binary` → `binary_sensor`. Every payload includes `availability_topic` so HA
  correctly shows devices offline when the gateway stops.
- **`mqtt/client.py`** (`MqttPort` protocol) wraps `paho-mqtt`, sets the Last Will and
  Testament (offline availability) *before* connecting, and is the sole owner of the
  MQTT connection — no module-level global client.
- **`gpio/`** (`GpioController` protocol) wraps `pigpio` for the optional coordinator
  hardware reset line / status LED. Selected explicitly via `coordinator.gpio_backend` in
  config — never inferred from platform detection.

## Why dependency injection

Every module that touches hardware or the network (`XBeeRadioPort`, `MqttPort`,
`GpioController`) is a small protocol/interface passed into constructors, with fake
implementations in `tests/conftest.py`. This means the coordinator setup logic, device
registration, and discovery payload construction can all be unit tested without any real
XBee radio, MQTT broker, or `pigpiod` daemon.

## Config sharing with the future web UI (Milestone 2)

`config/schema.py` and `config/loader.py` are the single source of truth for config
structure and (de)serialization, used by both the CLI app and the planned local web UI.
The web UI will read/write the same `config.json`/`devices.json` files through the same
`ConfigStore.save()` atomic-write path, so there is exactly one way to produce a valid
config file.
