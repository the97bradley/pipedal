#!/usr/bin/env bash
# Build an arm64 PiPedal .deb in Docker (linux/arm64) and copy it to dist-deb/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is not installed (Docker Desktop on Mac)." >&2
    exit 1
fi

if ! git submodule update --init --recursive; then
    echo "Failed to update git submodules." >&2
    exit 1
fi

mkdir -p dist-deb

echo "Building linux/arm64 .deb (Apple Silicon is native; Intel Mac uses qemu and is slow)."
docker buildx build \
    --platform linux/arm64 \
    -f docker/Dockerfile.deb \
    --target export \
    --output type=local,dest="$ROOT/dist-deb" \
    .

echo
echo "Debs:"
ls -lh dist-deb/*.deb
echo
echo "Copy to the Pi and install (package version may be older than 2.0.111):"
echo "  scp dist-deb/*.deb the97bradley@pipedal:~/"
echo "  ssh the97bradley@pipedal 'sudo apt-get install --allow-downgrades -y ./pipedal_*.deb'"
