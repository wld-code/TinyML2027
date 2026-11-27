#!/usr/bin/env bash
# Téléverse un sketch déjà compilé par scripts/compile.sh.
#
#   ./scripts/upload.sh examples/03_custom_model            # port détecté automatiquement
#   ./scripts/upload.sh examples/03_custom_model /dev/cu.usbmodem1101
#   REV=rev2 ./scripts/upload.sh labs/01-sensor-data/firmware/imu_capture   # build Rev2
#
# Sans port, le script cherche UNE carte arduino:mbed_nano:nano33ble. S'il en trouve
# zéro ou plusieurs, il s'arrête et affiche la liste : aucun port n'est supposé.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKETCH="${1:?usage: upload.sh <dossier_du_sketch> [port]}"
NAME="$(basename "$SKETCH")"
[ "${REV:-original}" = "rev2" ] && NAME="$NAME-rev2"
FQBN="$(grep -E '^ARDUINO_FQBN=' "$ROOT/config/versions.lock" | cut -d= -f2 | tr -d '\r')"
BUILD="$ROOT/build/$NAME"
[ -d "$BUILD" ] || { echo "Pas de build pour $NAME : lancez d'abord ./scripts/compile.sh $SKETCH" >&2; exit 1; }

PORT="${2:-}"
if [ -z "$PORT" ]; then
  source "$ROOT/scripts/nano-port.sh"
  PORT="$(nano_port)" || {
    echo "Relancez avec le port en second argument." >&2
    exit 1
  }
fi
echo "Téléversement de $NAME sur $PORT"
"$ROOT/scripts/arduino.sh" upload -p "$PORT" --fqbn "$FQBN" --input-dir "$BUILD"
echo "PORT=$PORT"
