#!/usr/bin/env bash
# Étape 14 : release motion-win (build, validate, flash, status) ; chaque commande et son code de sortie.
set -o pipefail
cd "$(dirname "$0")/../.."
export PYTHONIOENCODING=utf-8 TF_CPP_MIN_LOG_LEVEL=2
run() { echo "\$ $*"; "$@" 2>&1 | grep -vE "absl::|^I0000|^WARNING: All log|^\[=* *\] [0-9]+%" ; echo "EXIT=${PIPESTATUS[0]}"; echo; }
run uv run python -m tinyml2027.quantize_motion --data datasets/motion-nano-v1 --model-version motion-win
run ./scripts/compile.sh labs/03-embedded-inference/firmware/infer_nano
run uv run python -m tinyml2027.release build --version motion-win
run uv run python -m tinyml2027.release validate releases/motion-win
run uv run python -m tinyml2027.release flash releases/motion-win
run uv run python -m tinyml2027.release status
