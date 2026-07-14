# Configuration Reference

Two JSON files plus optional environment variable overrides. Real config files
(`config.json`, `devices.json`, `.env`) are gitignored — only the `*.example.json` /
`.env.example` templates are tracked, and they contain placeholder values only.

## `config.json`

Copy from `config/config.example.json`. Path via `--config` CLI flag or
`XBEE_GATEWAY_CONFIG` env var.

| Key | Description |
|---|---|
| `mqtt.host` / `mqtt.port` | MQTT broker address. |
| `mqtt.username` / `mqtt.password` | Leave blank in the file; prefer the env var overrides below for real deployments. |
| `mqtt.base_topic` | Prefix for state/availability topics, e.g. `xbeegateway`. |
| `mqtt.discovery_prefix` | Home Assistant MQTT discovery prefix, normally `homeassistant`. |
| `mqtt.availability_topic` | Gateway-wide online/offline topic (LWT). |
| `coordinator.serial_port` / `baud_rate` | Serial connection to the local XBee coordinator radio. |
| `coordinator.reset_gpio_pin` / `status_led_gpio_pin` | GPIO pin numbers, `-1` to disable. |
| `coordinator.gpio_backend` | `"pigpio"` or `"none"` — explicit choice, never auto-detected. |
| `coordinator.at_settings.*` | AT-command parameters applied to the coordinator at startup. Each entry has `at` (command mnemonic), `value`, `verify_before_write` (read back and compare before writing, where the radio supports it), and optionally `secret: true` (e.g. the network encryption key) to flag it for redaction in logs and the future web UI. |
| `logging.level` | Standard Python logging level name. |

## `devices.json`

Copy from `config/devices.example.json`. Path via `--devices` CLI flag or
`XBEE_GATEWAY_DEVICES` env var.

- `auto_register_unknown_devices` — if `true`, any XBee device that sends an IO sample but
  isn't listed here gets a synthesized entry with generic channels and is published to HA
  immediately (with a `WARNING` logged). Set `false` to require explicit configuration.
- `devices[]` — one entry per remote XBee end device (`address`, `name`, `manufacturer`,
  `model`, `channels[]`). All channels on a device share one Home Assistant device page
  (grouped by `address`) — see `config/devices.example.json`'s "Shower Monitor" for an
  example of one XBee node exposing several rooms' worth of entities under one device.
- Multiple `channels[]` entries may share the same `io_line` — every IO sample on that
  line is fanned out to each configured channel, so one physical reading can back more
  than one HA entity (e.g. a raw `analog` sensor for tuning, alongside an
  `analog_threshold_binary` derived state for automations). Each channel still needs a
  distinct `name` — entity topics/IDs are derived from `name`, and the gateway refuses to
  start (raises at config load) if two channels on the same device resolve to the same
  slug.
- `channels[].kind` — drives the Home Assistant component type:
  - `analog` → HA `sensor` (`unit_of_measurement`, `device_class`, optional
    `value_template` for scaling raw ADC readings). Publishes on every sample.
  - `analog_threshold_binary` → HA `binary_sensor` derived from an ADC value crossing
    `threshold`. Publishes only on a debounced state change.
    - `hysteresis` (default `0`) — once the value crosses above `threshold` (entity
      turns ON), it must drop back below `threshold - hysteresis` to turn OFF again.
      Use this to stop a reading that hovers near `threshold` from flapping the entity
      state. `0` reproduces the old hard-threshold behavior.
  - `digital_binary` → HA `binary_sensor` from a true digital IO line.

## Environment variable overrides

Format: `XBEE_GATEWAY_<SECTION>__<KEY>` (double underscore = nesting). Always wins over
the file. This is the intended way to supply secrets — never put a real broker password
in `config.json`.

```
XBEE_GATEWAY_MQTT__HOST=mqtt.example.local
XBEE_GATEWAY_MQTT__USERNAME=someuser
XBEE_GATEWAY_MQTT__PASSWORD=somepassword
XBEE_GATEWAY_COORDINATOR__SERIAL_PORT=/dev/ttyUSB0
```

Under systemd, set these via `/etc/xbee-gateway/xbee-gateway.env`, referenced by the unit
file's `EnvironmentFile=-...` directive (copy from `.env.example`).
