#!/usr/bin/env bash
# Compile tous les croquis du cours (originale + rev2) depuis le dépôt courant ; résumé des tailles.
set -uo pipefail
cd "$(dirname "$0")/../.."
OUT="$1"
: > "$OUT"
SKETCHES=(
  examples/01_blink
  tutorials/02-arduino-nano/sketches/board_identify
  examples/03_custom_model
  examples/04_imu
  examples/05_int8_model
  labs/01-sensor-data/firmware/imu_capture
  labs/03-embedded-inference/firmware/infer_nano
  advanced/edge-impulse/sketches/mic_check
)
for s in "${SKETCHES[@]}"; do
  for rev in original rev2; do
    name="$(basename "$s")"; [ "$rev" = rev2 ] && name="$name-rev2"
    start=$(date +%s)
    if REV=$rev ./scripts/compile.sh "$s" > /dev/null 2>&1; then st=OK; else st="ECHEC($?)"; fi
    flash=$(grep -oE '(Sketch uses|Le croquis utilise) [0-9]+' "build/$name.log" | grep -oE '[0-9]+' | head -1)
    ram=$(grep -oE '(Global variables use|Les variables globales utilisent) [0-9]+' "build/$name.log" | grep -oE '[0-9]+' | head -1)
    printf '%s\t%s\t%s\tflash=%s\tram=%s\t%ss\n' "$s" "$rev" "$st" "${flash:-?}" "${ram:-?}" "$(( $(date +%s) - start ))" | tee -a "$OUT"
  done
done
echo FIN | tee -a "$OUT"
