#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi

systemctl disable --now xbee-gateway.service 2>/dev/null || true
rm -f /etc/systemd/system/xbee-gateway.service
systemctl daemon-reload

echo "Service removed. /opt/xbee-gateway and /etc/xbee-gateway were left in place (may contain config) — remove manually if no longer needed."
