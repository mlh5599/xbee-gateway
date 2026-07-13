#!/usr/bin/env bash
# Installs xbee-gateway as a systemd service on Raspberry Pi OS / Debian.
# Intended for low-resource hardware (e.g. Raspberry Pi Model B/Zero) — no Docker required.
set -euo pipefail

INSTALL_DIR="/opt/xbee-gateway"
CONFIG_DIR="/etc/xbee-gateway"
SERVICE_USER="xbeegateway"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi

id -u "$SERVICE_USER" &>/dev/null || useradd --system --home "$INSTALL_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
usermod -aG dialout "$SERVICE_USER" || true

mkdir -p "$INSTALL_DIR" "$CONFIG_DIR"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install "$REPO_ROOT"

# Seed config only if it doesn't already exist — never overwrite a real deployment's config.
[[ -f "$CONFIG_DIR/config.json" ]] || cp "$REPO_ROOT/config/config.example.json" "$CONFIG_DIR/config.json"
[[ -f "$CONFIG_DIR/devices.json" ]] || cp "$REPO_ROOT/config/devices.example.json" "$CONFIG_DIR/devices.json"

chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR" "$CONFIG_DIR"

cp "$REPO_ROOT/deploy/systemd/xbee-gateway.service" /etc/systemd/system/xbee-gateway.service
systemctl daemon-reload
systemctl enable --now xbee-gateway.service

echo "Installed. Edit $CONFIG_DIR/config.json and $CONFIG_DIR/devices.json, then: systemctl restart xbee-gateway"
