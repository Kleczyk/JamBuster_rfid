#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
INSTALL_SUMO="${INSTALL_SUMO:-1}"

log() {
  printf "\n[%s] %s\n" "$(date +%H:%M:%S)" "$1"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing dependency: $1"
    return 1
  fi
  return 0
}

log "Working directory: ${ROOT_DIR}"

if [[ "${INSTALL_SUMO}" == "1" ]]; then
  log "Installing SUMO (requires sudo)"
  if command -v sudo >/dev/null 2>&1; then
    sudo add-apt-repository -y ppa:sumo/stable
    sudo apt-get update
    sudo apt-get install -y sumo sumo-tools sumo-doc
  else
    echo "sudo not found. Skipping SUMO install. Set SUMO_HOME manually if SUMO is already installed."
  fi
else
  log "Skipping SUMO install (INSTALL_SUMO=0)"
fi

if ! require_cmd curl; then
  echo "Please install curl first, then re-run this script."
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  log "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Ensure uv is in PATH for this script
  export PATH="${HOME}/.cargo/bin:${PATH}"
fi

log "Installing Python ${PYTHON_VERSION} with uv"
uv python install "${PYTHON_VERSION}"

log "Creating venv at ${ROOT_DIR}/.venv"
cd "${ROOT_DIR}"
uv venv .venv --python "${PYTHON_VERSION}"

log "Installing project dependencies"
source .venv/bin/activate
uv pip install -e .

log "Installation complete"
echo
echo "Next steps (run from ${ROOT_DIR}):"
echo "  source .venv/bin/activate"
echo "  python train.py"
echo "  # or PPO-Transformer:"
echo "  uv run python train_ppo_transformer.py --config configs/ppo_transformer.yaml"
if [[ -z "${SUMO_HOME:-}" ]]; then
  echo
  echo "SUMO_HOME is not set in this shell."
  echo "Example:"
  echo "  export SUMO_HOME=\"/usr/share/sumo\""
fi





