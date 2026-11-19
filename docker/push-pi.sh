#!/usr/bin/env bash
# Fast path: copy Bluetooth scripts + web UI to the Pi. Seconds, not a full .deb.
# Use this after 2.0.114+ is already installed. Full package: docker/build-deb.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${PIPEDAL_HOST:-pipedal.local}"
cd "$ROOT"

if [[ ! -f vite/package.json ]]; then
    echo "Run this from the pipedal repo." >&2
    exit 1
fi

echo "Building UI on this machine..."
(
    cd vite
    if [[ ! -d node_modules ]]; then
        npm install
    fi
    npm run build
)

echo "Copying to ${HOST}..."
scp -q \
    src/scripts/pipedal-bt-nap \
    src/scripts/pipedal-bt-agent \
    src/dbus/pipedal-bluetooth.conf \
    "${HOST}:~/"

# scp a directory of hashed assets
scp -q -r vite/dist/. "${HOST}:pipedal-ui/"

echo "Installing (sudo password)..."
ssh -t "$HOST" 'set -e
sudo install -m 755 "$HOME/pipedal-bt-nap" /usr/sbin/pipedal-bt-nap
sudo install -m 755 "$HOME/pipedal-bt-agent" /usr/sbin/pipedal-bt-agent
sudo install -m 644 "$HOME/pipedal-bluetooth.conf" /etc/dbus-1/system.d/pipedal-bluetooth.conf
sudo mkdir -p /etc/pipedal/react
sudo cp -a "$HOME/pipedal-ui/." /etc/pipedal/react/
sudo systemctl restart bluetooth pipedal-bt-nap pipedald
systemctl is-active bluetooth pipedal-bt-nap pipedald
echo OK
'

echo
echo "Done. Hard-refresh http://${HOST}/"
echo "Full .deb is only needed when pipedald itself changes: docker/build-deb.sh"
