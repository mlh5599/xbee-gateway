# Changelog

## Unreleased

- Added `band_timeout_seconds` (optional) to `analog_threshold_binary` channels: once
  ON, if the reading sits in the hold band that long without ever reaching
  `off_threshold`, it is forced OFF and logged as a false trigger (a nearby hot pipe
  warming the sensor, or an end device going silent mid-band). Re-evaluated on a
  periodic internal tick so it still fires when samples stop. After such a release the
  channel is **suppressed**: a lone sample back past `on_threshold` is ignored, so a
  reading wobbling across the setpoint (crosstalk + ADC noise) no longer flaps the
  state ON/OFF on a ~`band_timeout_seconds` cycle. Re-arming takes two consecutive
  on-side samples (a real event holds the reading there); a sample back past
  `off_threshold` clears the suppression with the state left OFF.
- **Breaking:** `analog_threshold_binary` channels now take two independent setpoints,
  `on_threshold` and `off_threshold`, instead of `threshold` + `hysteresis`. The single
  threshold plus one-sided deadband tripped late and, in practice, missed the many
  showers where the pipe warms but never fully crosses the line — the derived `running`
  state stayed `off` for most real events. With `on_threshold` set just past the resting
  reading, the state turns on as soon as the pipe starts to ramp; `off_threshold` (on
  the same side of resting) sets where it releases, and the gap between the two is the
  anti-flap hold band. Migration: rename `threshold` → `on_threshold` and move it closer
  to the resting level; set `off_threshold` to the old `threshold ± hysteresis` value
  (or wherever you want the release), keeping both setpoints on the resting side of the
  swing. `direction` is unchanged. `config/devices.example.json` shows tuned values for
  the three-room shower monitor.
- Fixed MQTT availability getting stuck retained `offline` after a broker-side
  reconnect (#26): the birth message was only published once, right after the initial
  `connect()`, so paho-mqtt's automatic reconnects (which re-fire `on_connect` but don't
  go through that startup path) never re-announced `online`. The birth-message publish
  now lives in the `on_connect` callback itself, so it fires on every successful
  connect/reconnect, not just process startup. Also added a belt-and-suspenders
  safeguard, `mqtt.availability_reassert_interval` (default 3600s/hourly): while the client
  reports itself connected, retained `online` is periodically re-published even without
  a reconnect event, in case the retained value gets clobbered by anything else. `0`
  disables it.
- Added `direction` (`"above"` | `"below"`, default `"above"`) to `analog_threshold_binary`
  channels: NTC thermistors read *lower* as temperature rises, so the shower-monitor use
  case needs "ON when the raw value drops" rather than the original above-only comparison.
  `direction` picks which side the `on_threshold`/`off_threshold` comparisons face.
  Default preserves existing above-threshold behavior.
- Fixed IO sample channel lookups using `str(line)` (e.g. `"IOLine.DIO3_AD3"`) instead of
  `line.name` (`"DIO3_AD3"`), which meant configured channels never matched incoming
  samples — entities were discovered in Home Assistant but never received a state update
  and stayed "Unknown". Also fixed digital-channel state always evaluating truthy
  (`digi.xbee.io.IOValue.LOW` is a nonzero, truthy enum member) by comparing explicitly
  against `IOValue.HIGH`.
- **Breaking:** a device's `channels[]` may now repeat the same `io_line` (fan-out one
  physical reading to multiple HA entities). As a consequence, entity topic/unique_id
  slugs are now derived from each channel's `name` instead of its `io_line` (previously
  ambiguous once an `io_line` isn't unique per entity) — existing state/discovery topics
  change for any channel where `name` differs from `io_line`. Stale retained discovery
  messages for the old topics should be cleaned up in Home Assistant/the broker after
  upgrading.
- Replaced `config/devices.example.json`'s soil-moisture/door-sensor example with a
  "Shower Monitor" example: one XBee node, three rooms, each exposing both a raw ADC
  `sensor` and a derived `analog_threshold_binary` "running" `binary_sensor` from the same
  `io_line`.
- Initial project scaffold: package layout, config schema/examples, systemd + Docker
  deployment templates, CI workflow.
