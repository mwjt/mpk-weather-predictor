#!/usr/bin/env bash
set -euo pipefail

HARVESTER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="$HARVESTER_DIR/mpk-harvester.service.template"
GENERATED_FILE="$HARVESTER_DIR/mpk-harvester.service"
SERVICE_LINK="/etc/systemd/system/mpk-harvester.service"
SERVICE_NAME="mpk-harvester"

DASHBOARD_TEMPLATE="$HARVESTER_DIR/dashboard.service.template"
DASHBOARD_GENERATED="$HARVESTER_DIR/dashboard.service"
DASHBOARD_LINK="/etc/systemd/system/mpk-dashboard.service"

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

echo "Waiting for postgres to be ready..."
until docker exec $(docker ps --filter "name=postgres" -q) pg_isready -U mpk -d mpk_harvester >/dev/null 2>&1; do
    sleep 1
done

echo "Ensuring reader user and permissions..."
PASSWORD_FILE="$HARVESTER_DIR/.reader_password"
if [ -f "$PASSWORD_FILE" ]; then
    READER_PASSWORD=$(cat "$PASSWORD_FILE")
    IS_NEW_PASSWORD=false
else
    READER_PASSWORD=$(openssl rand -hex 16)
    echo "$READER_PASSWORD" > "$PASSWORD_FILE"
    IS_NEW_PASSWORD=true
fi

docker exec -i $(docker ps --filter "name=postgres" -q) \
    psql -U mpk -d mpk_harvester -v reader_password="'$READER_PASSWORD'" \
    < "$HARVESTER_DIR/db/init_reader.sql"

if [ "$IS_NEW_PASSWORD" = true ]; then
    echo "Reader password generated: $READER_PASSWORD"
    echo "Saved to $PASSWORD_FILE — copy it into your main PC's DATABASE_URL now."
else
    echo "Reader password unchanged (loaded from $PASSWORD_FILE)."
fi

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

if systemctl list-unit-files | grep -q "^mpk-dashboard.service"; then
    sudo systemctl stop mpk-dashboard 2>/dev/null || true
    sudo systemctl disable mpk-dashboard 2>/dev/null || true
    sudo rm -f "$DASHBOARD_LINK"
    sudo systemctl daemon-reload
fi

sed -e "s|__USER__|$USER|g" \
    -e "s|__HARVESTER_DIR__|$HARVESTER_DIR|g" \
    "$DASHBOARD_TEMPLATE" > "$DASHBOARD_GENERATED"

sudo ln -sf "$DASHBOARD_GENERATED" "$DASHBOARD_LINK"
sudo systemctl daemon-reload
sudo systemctl enable mpk-dashboard
sudo systemctl stop mpk-dashboard 2>/dev/null || true
sudo systemctl start mpk-dashboard

echo "Dashboard available at: http://$(hostname -I | awk '{print $1}'):8080 (or via Tailscale IP)"