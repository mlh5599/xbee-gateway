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
| `mqtt.availability_reassert_interval` | Seconds between re-publishing retained `online` while connected, as a safeguard beyond the on-connect birth message. `0` disables. Default `3600` (hourly). |
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
    two independent setpoints. Publishes only on a debounced state change.
    - `direction` (default `"above"`) — which side is the "triggered"/hotter side.
      `"above"`: higher raw value → ON (most sensors — moisture, current clamps).
      `"below"`: lower raw value → ON. Use this for NTC thermistors, where resistance
      (and so the raw ADC reading) *drops* as the monitored condition heats up.
    - `on_threshold` — the state goes **ON** when the raw value passes this in the
      triggered direction (`>= on_threshold` for `"above"`, `<= on_threshold` for
      `"below"`). Set it close to the resting reading so a slow ramp trips the state
      early, with a little margin so quiet-period noise doesn't false-trigger.
    - `off_threshold` — the state goes back **OFF** when the raw value comes back past
      this (`<= off_threshold` for `"above"`, `>= off_threshold` for `"below"`). Between
      the two setpoints the state is held, so the gap acts as an anti-flap band; a wider
      gap also keeps the state ON longer into the tail (e.g. a pipe cooling down after a
      shower). Both setpoints are on the same side of the resting level.
    - `band_timeout_seconds` (optional) — failsafe against a latch that never clears.
      Once the state is ON, if the raw value sits *in the hold band* (past `on_threshold`
      but not yet back to `off_threshold`) for this many seconds without ever reaching
      `off_threshold`, the state is forced back **OFF** and logged as a false trigger.
      A real event slams the reading well past `on_threshold` and holds it there, so it
      never lingers in the band; crosstalk, sensor drift, or a since-silent end device
      only nudge the reading into the band, and this releases them. The timer starts at
      the OFF→ON transition and is not reset by the reading going deeper; reaching
      `off_threshold` always releases immediately regardless of the timer. Omit it (the
      default) for pure two-setpoint hysteresis with no time limit. The failsafe is also
      re-evaluated on a periodic internal tick, so it still fires when the end device has
      stopped sending samples.
      After a timeout release the channel is **suppressed**: the reading is still past
      `on_threshold`, and if it wobbles across the setpoint (crosstalk plus ADC noise)
      each re-cross would re-trip ON, time out again, and flap the state on a
      ~`band_timeout_seconds` cycle. While suppressed a lone sample back past
      `on_threshold` is ignored; it takes **two consecutive** on-side samples to re-arm
      (a real event holds the reading there), or one sample back past `off_threshold`
      to clear the suppression with the state left OFF.
    - Example (shower-pipe NTC, resting ADC ~660): `"direction": "below"`,
      `"on_threshold": 620`, `"off_threshold": 640`, `"band_timeout_seconds": 60` — ON
      once the pipe warms enough to pull the reading to 620, OFF once it cools back to
      640, or forced OFF if it just hovers between 620 and 640 for a minute (a nearby
      pipe warming this one, not a shower). If a channel is missing `on_threshold` it
      never turns on; missing `off_threshold`, it never turns off (unless
      `band_timeout_seconds` is set).
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
