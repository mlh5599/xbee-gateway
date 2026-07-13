# xbee-gateway

An XBee/Zigbee to MQTT gateway for Home Assistant. A Raspberry Pi (or similar) with an
XBee coordinator radio attached relays sensor readings from remote XBee end devices to
an MQTT broker, publishing Home Assistant MQTT discovery so devices show up automatically.

MQTT is the transport for everything — no dependency on Home Assistant's native API/ESPHome
integration. Designed to run on low-resource hardware (e.g. an original Raspberry Pi
Model B, 512MB RAM) via a plain systemd service; a Docker deployment path is also provided
for beefier hosts.

This project is under active development — see the [Milestones](../../milestones) for the
current roadmap.

## Status

- **Milestone 1 — Core Gateway**: in progress. Raw XBee IO sample relay to MQTT with
  correct Home Assistant discovery typing (`sensor` for analog values, `binary_sensor`
  for digital/thresholded values).
- **Milestone 2 — Local Web UI**: planned. A small local web UI for editing device/channel
  and XBee coordinator configuration, instead of hand-editing JSON over SSH.
- **Milestone 3 — ESPHome Smart End Device**: roadmap only. A more capable, two-way
  microcontroller-based end device running ESPHome firmware in MQTT mode.

## Quick start (raw hardware — Raspberry Pi / Debian)

```bash
git clone https://github.com/mlh5599/xbee-gateway.git
cd xbee-gateway
sudo deploy/scripts/install.sh
```

This creates a dedicated `xbeegateway` system user, a Python venv under
`/opt/xbee-gateway`, seeds `/etc/xbee-gateway/config.json` and `devices.json` from the
example templates (never overwriting an existing config), and installs+starts the
`xbee-gateway` systemd service. Edit the seeded config files for your MQTT broker,
XBee coordinator serial port, and devices, then `sudo systemctl restart xbee-gateway`.

See [docs/configuration.md](docs/configuration.md) for the full config reference.

## Quick start (Docker — secondary path)

See [deploy/docker](deploy/docker). Requires passing through the serial device the XBee
coordinator is attached to; GPIO-based coordinator reset is not available in a standard
container.

## Configuration

All configuration is via `config.json` + `devices.json` (never committed — only
`config.example.json`/`devices.example.json` templates are tracked) plus environment
variable overrides for secrets (`XBEE_GATEWAY_MQTT__PASSWORD`, etc.). Nothing in this
repo references any specific real hostname, IP, or credential — every example uses
placeholder values so it can be deployed in any homelab. See
[docs/configuration.md](docs/configuration.md).

## Development

```bash
pip install -e ".[dev]"
pytest
flake8 src tests
```

## Documentation

- [docs/architecture.md](docs/architecture.md)
- [docs/configuration.md](docs/configuration.md)
- [docs/mqtt-topics.md](docs/mqtt-topics.md)
- [docs/milestone-2-web-ui.md](docs/milestone-2-web-ui.md)
- [docs/milestone-3-esphome-roadmap.md](docs/milestone-3-esphome-roadmap.md)
- [docs/migration-from-legacy.md](docs/migration-from-legacy.md)

## License

MIT — see [LICENSE](LICENSE).
