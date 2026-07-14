# Changelog

## Unreleased

- Added `direction` (`"above"` | `"below"`, default `"above"`) to `analog_threshold_binary`
  channels: NTC thermistors read *lower* as temperature rises, so the shower-monitor use
  case needs "ON when raw value drops below threshold" rather than the original
  above-threshold-only comparison. Hysteresis now applies symmetrically in either
  direction. Default preserves existing above-threshold behavior.
- Fixed IO sample channel lookups using `str(line)` (e.g. `"IOLine.DIO3_AD3"`) instead of
  `line.name` (`"DIO3_AD3"`), which meant configured channels never matched incoming
  samples — entities were discovered in Home Assistant but never received a state update
  and stayed "Unknown". Also fixed digital-channel state always evaluating truthy
  (`digi.xbee.io.IOValue.LOW` is a nonzero, truthy enum member) by comparing explicitly
  against `IOValue.HIGH`.
- Added `hysteresis` to `analog_threshold_binary` channels: once triggered ON, the
  reading must drop below `threshold - hysteresis` to go OFF again, instead of a single
  hard threshold that can flap.
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
