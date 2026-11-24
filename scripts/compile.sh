#!/usr/bin/env bash
# Compile un sketch pour la Nano 33 BLE Sense avec l'environnement figé du projet.
#
#   ./scripts/compile.sh <dossier_sketch> [options arduino-cli supplémentaires]
#   REV=rev2 ./scripts/compile.sh <dossier_sketch>    # Nano 33 BLE Sense Rev2 (BMI270)
#
# REV vaut `original` (défaut, LSM9DS1) ou `rev2` (BMI270). Pour rev2, la macro
# NANO_REV2 est définie, exactement comme si l'on décommentait `#define NANO_REV2`
# en tête du sketch.
# Le binaire est écrit dans build/<nom>[-rev2]/ et la sortie complète dans build/<nom>[-rev2].log
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKETCH="${1:?usage: compile.sh <dossier_sketch> [options]}"; shift
REV="${REV:-original}"
NAME="$(basename "$SKETCH")"
EXTRA=()
case "$REV" in
  original) ;;
  rev2) NAME="$NAME-rev2"; EXTRA=(--build-property "compiler.cpp.extra_flags=-DNANO_REV2") ;;
  *) echo "REV doit valoir original ou rev2 (reçu : $REV)" >&2; exit 2 ;;
esac
FQBN="$(grep -E '^ARDUINO_FQBN=' "$ROOT/config/versions.lock" | cut -d= -f2 | tr -d '\r')"
mkdir -p "$ROOT/build"
echo "# compile.sh REV=$REV sketch=$SKETCH" > "$ROOT/build/$NAME.log"
"$ROOT/scripts/arduino.sh" compile --fqbn "$FQBN" --build-path "$ROOT/build/$NAME" \
  ${EXTRA[@]+"${EXTRA[@]}"} "$@" "$SKETCH" 2>&1 \
  | tee -a "$ROOT/build/$NAME.log"
exit "${PIPESTATUS[0]}"
