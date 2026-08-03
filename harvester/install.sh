#!/usr/bin/env bash
set -euo pipefail

HARVESTER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="$HARVESTER_DIR/mpk-harvester.service.template"
GENERATED_FILE="$HARVESTER_DIR/mpk-harvester.service"
SERVICE_LINK="/etc/systemd/system/mpk-harvester.service"
SERVICE_NAME="mpk-harvester"

if [ "$EUID" -eq 0 ]; then
    echo "ERROR: don't run install.sh with sudo. Run it as your normal user;"
    echo "it will call sudo internally only where needed."
    exit 1
fi

# --- check prerequisites ---
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found. Install it first: sudo pacman -S docker docker-compose"; exit 1; }
command -v python >/dev/null 2>&1 || { echo "ERROR: python not found."; exit 1; }
systemctl is-active --quiet docker || { echo "ERROR: docker service not running. Run: sudo systemctl enable --now docker"; exit 1; }

# --- stop/disable existing service if present ---
if systemctl list-unit-files | grep -q "^${SERVICE_NAME}.service"; then
    echo "Existing $SERVICE_NAME service found — stopping and disabling before reinstall..."
    sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    sudo rm -f "$SERVICE_LINK"
    sudo systemctl daemon-reload
    echo "Old service removed."
fi

echo "Rebuilding venv from scratch at $HARVESTER_DIR/.venv..."
rm -rf "$HARVESTER_DIR/.venv"
python -m venv "$HARVESTER_DIR/.venv"
"$HARVESTER_DIR/.venv/bin/pip" install --upgrade pip
"$HARVESTER_DIR/.venv/bin/pip" install --no-cache-dir -r "$HARVESTER_DIR/requirements.txt"

echo "Clearing stale bytecode cache..."
find "$HARVESTER_DIR" -maxdepth 1 -name "__pycache__" -type d -exec rm -rf {} +
find "$HARVESTER_DIR/db" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo "Starting postgres..."
docker compose -f "$HARVESTER_DIR/docker-compose.yml" up -d

echo "Generating systemd unit for user '$USER' at $HARVESTER_DIR..."
sed -e "s|__USER__|$USER|g" \
    -e "s|__HARVESTER_DIR__|$HARVESTER_DIR|g" \
    "$TEMPLATE_FILE" > "$GENERATED_FILE"

echo "Linking systemd unit..."
sudo ln -sf "$GENERATED_FILE" "$SERVICE_LINK"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
sudo systemctl start "$SERVICE_NAME"

echo ""
echo "Done. Verifying..."
sleep 2
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✔ $SERVICE_NAME is running"
else
    echo "✘ $SERVICE_NAME failed to start — check: journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi