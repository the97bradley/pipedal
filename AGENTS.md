# Agent notes (the97bradley/pipedal)

This is Bradley’s fork. The Raspberry Pi (`pipedal.local`) runs **this fork**, never stock/upstream `rerdavies/pipedal` 2.0.111.

## Deploy

- **Default:** `./docker/push-pi.sh` — Vite UI + Bluetooth scripts to the Pi in seconds.
- **Full arm64 `.deb`:** `./docker/build-deb.sh` **only** if `pipedald` / `pipedaladmind` / `pipedalconfig` C++ changed, or the Pi is still stock.

Do not full-build “to be safe.” See `.cursor/rules/pi-deploy.mdc` and `.cursor/rules/load-our-fork.mdc`.
