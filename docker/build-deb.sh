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

mkdir -p dist-deb .docker-cache

echo "Building linux/arm64 .deb (Apple Silicon is native; Intel Mac qemu is slow)."
echo "Bluetooth/UI-only? Use docker/push-pi.sh instead."
export DOCKER_BUILDKIT=1
docker buildx build \
    --platform linux/arm64 \
    -f docker/Dockerfile.deb \
    --target export \
    --cache-from type=local,src="$ROOT/.docker-cache" \
    --cache-to type=local,dest="$ROOT/.docker-cache",mode=max \
    --output type=local,dest="$ROOT/dist-deb" \
    .

echo
echo "Debs:"
ls -lh dist-deb/*.deb
echo
echo "Install on the Pi:"
echo "  scp dist-deb/*.deb pipedal.local:~/"
echo "  ssh -t pipedal.local 'sudo apt-get install -y ./pipedal_*.deb'"
