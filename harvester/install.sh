#!/usr/bin/env bash
set -euo pipefail

HARVESTER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$HARVESTER_DIR/mpk-harvester.service"
SERVICE_LINK="/etc/systemd/system/mpk-harvester.service"

echo "Setting up venv..."
python -m venv "$HARVESTER_DIR/.venv"
"$HARVESTER_DIR/.venv/bin/pip" install -r "$HARVESTER_DIR/requirements.txt"

echo "Starting postgres..."
docker compose -f "$HARVESTER_DIR/docker-compose.yml" up -d

echo "Linking systemd unit..."
sudo ln -sf "$SERVICE_FILE" "$SERVICE_LINK"
sudo systemctl daemon-reload
sudo systemctl enable --now mpk-harvester

echo "Done. Check status with: systemctl status mpk-harvester"
echo "Logs: journalctl -u mpk-harvester -f"