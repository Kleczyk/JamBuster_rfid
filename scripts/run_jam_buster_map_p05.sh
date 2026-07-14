#!/usr/bin/env bash
# Uruchom mapę Rzeszów (JamBuster map_p05) z katalogu głównego JamBuster_rfid.
# Nie rób `cd JamBuster/src/map_p05` jeśli już tam jesteś — używaj tego skryptu z roota repo.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NET="$ROOT/JamBuster/src/map_p05/map.net.xml"
CFG="$ROOT/JamBuster/src/map_p05/sim.sumocfg"

if [[ ! -f "$NET" ]]; then
  echo "Brak $NET — sklonuj JamBuster do $ROOT/JamBuster (np. git clone … JamBuster)."
  exit 1
fi

echo "== Poprawa faz sygnalizacji (uv run) =="
(cd "$ROOT" && uv run python scripts/fix_sumo_tl_phases.py "$NET")

MODE="${1:-gui}"
if [[ "$MODE" == "gui" ]]; then
  echo "== SUMO GUI =="
  exec sumo-gui -c "$CFG"
else
  echo "== SUMO headless (--end ${2:-300}) =="
  exec sumo -c "$CFG" --no-step-log --end "${2:-300}"
fi
