#!/usr/bin/env bash
# Lance arduino-cli dans l'environnement isolé du dépôt (macOS / Linux).
# Exemple : ./scripts/arduino.sh board list
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ARDUINO_DIRECTORIES_DATA="$ROOT/.arduino/data"
export ARDUINO_DIRECTORIES_DOWNLOADS="$ROOT/.arduino/staging"
export ARDUINO_DIRECTORIES_USER="$ROOT/.arduino/user"
CLI="$ROOT/.arduino/bin/arduino-cli"
[ -x "$CLI" ] || { echo "ERREUR : $CLI absent. Lancez ./scripts/setup.sh" >&2; exit 1; }
exec "$CLI" --config-file "$ROOT/arduino-cli.yaml" "$@"
