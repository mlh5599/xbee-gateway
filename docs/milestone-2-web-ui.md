# Milestone 2: Local Web UI — Design Intent

Goal: replace hand-editing `devices.json`/`config.json` over SSH with a small local web UI
for editing device/channel definitions and XBee coordinator AT settings.

## Tech choices

- **Flask + Jinja2**, server-rendered — no SPA build tooling (no node/webpack/vite) given
  the target hardware.
- **HTMX** for inline interactivity (edit/delete without full page reloads) without adopting
  a JS framework.
- **waitress** as the WSGI server (pure Python, no compiled dependency) — important on
  low-resource ARM hardware where wheel availability/build time for compiled deps is a
  real risk.
- Runs as its own systemd unit (`xbee-gateway-web.service`), independent of the sensor
  relay process, so the UI can restart without interrupting sensor data flow.

## Config sharing

Uses the same `xbee_gateway.config.schema` / `loader` module as the CLI app. Forms are
generated from / validated against `config/config.schema.json`. All writes go through
`ConfigStore.save()` (atomic write + file lock) — one code path can produce
`devices.json`, whether from the CLI, hand-editing, or the web UI.

## Live reload

The gateway process polls the config file `mtime` (or reloads on `SIGHUP`) and hot-reloads
the device registry / coordinator AT settings without a full process restart. No RPC/socket
layer for v1 — the web UI and gateway process only communicate via the JSON files on disk.

## Scope

- CRUD for `devices.json`: add/edit/delete devices and channels, `kind` selector driving
  conditional fields (threshold, unit, device_class, templates).
- Editor for `coordinator.at_settings` with hex-format validation and a warning that
  changes require re-applying settings to the radio.
- A way to "claim" an auto-registered device (see `auto_register_unknown_devices` in
  [configuration.md](configuration.md)) — turn it from an implicit synthesized entry into
  an explicit `devices.json` entry.

## Auth

LAN-only by default with a prominent "do not expose this to the internet" banner.
Optional single-admin password (env var, hashed) behind a feature flag. Not in scope for
Milestone 1.
