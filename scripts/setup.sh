#!/usr/bin/env bash
# Installe l'environnement figé de TinyML2027 dans le dossier du projet (macOS Apple Silicon vérifié).
#   - Arduino CLI (version et SHA-256 de config/versions.lock) dans .arduino/bin/
#   - core et bibliothèques Arduino figés dans .arduino/
#   - Arduino_TensorFlowLite au commit figé dans .arduino/user/libraries/
#   - environnement Python verrouillé (.venv, uv.lock)
# Idempotent. Ne modifie ni l'installation Arduino globale, ni le Python système.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Lecture de config/versions.lock (compatible bash 3.2 de macOS)
while IFS='=' read -r key value; do
  case "$key" in ''|\#*) continue ;; esac
  printf -v "$key" '%s' "$value"
done < "$ROOT/config/versions.lock"
A="$ROOT/scripts/arduino.sh"

step() { printf '\n=== %s\n' "$*"; }

step "Arduino CLI $ARDUINO_CLI_VERSION"
if [ "$(uname -s)-$(uname -m)" != "Darwin-arm64" ]; then
  echo "ERREUR : téléchargement figé prévu pour macOS Apple Silicon uniquement (autres OS : non testés, voir docs/installation.md)"; exit 1
fi
BIN="$ROOT/.arduino/bin/arduino-cli"
if ! { [ -x "$BIN" ] && "$BIN" version | grep -q "Version: $ARDUINO_CLI_VERSION "; }; then
  mkdir -p "$ROOT/.arduino/dl" "$ROOT/.arduino/bin"
  TGZ="arduino-cli_${ARDUINO_CLI_VERSION}_macOS_ARM64.tar.gz"
  curl -fsSL -o "$ROOT/.arduino/dl/$TGZ" "https://downloads.arduino.cc/arduino-cli/$TGZ"
  echo "$ARDUINO_CLI_MACOS_ARM64_SHA256  $ROOT/.arduino/dl/$TGZ" | shasum -a 256 -c -
  tar -xzf "$ROOT/.arduino/dl/$TGZ" -C "$ROOT/.arduino/bin" arduino-cli
fi
"$BIN" version

step "Core $ARDUINO_CORE"
"$A" core update-index
"$A" core install "$ARDUINO_CORE"

step "Bibliothèques Arduino"
"$A" lib update-index
"$A" lib install "$LIB_ARDUINO_LSM9DS1" "$LIB_ARDUINO_BMI270_BMM150"

step "Arduino_TensorFlowLite @ $TFLM_ARDUINO_COMMIT"
DEST="$ROOT/.arduino/user/libraries/Arduino_TensorFlowLite"
if [ ! -d "$DEST/.git" ]; then
  git init -q "$DEST"
  git -C "$DEST" remote add origin "$TFLM_ARDUINO_REPO"
fi
git -C "$DEST" fetch -q --depth 1 origin "$TFLM_ARDUINO_COMMIT"
git -C "$DEST" checkout -q --force "$TFLM_ARDUINO_COMMIT"
test "$(git -C "$DEST" rev-parse HEAD)" = "$TFLM_ARDUINO_COMMIT"
echo "Arduino_TensorFlowLite : $(git -C "$DEST" rev-parse HEAD)"

step "Python (uv.lock)"
command -v uv >/dev/null || { echo "ERREUR : uv absent (brew install uv)"; exit 1; }
uv sync --frozen

step "Récapitulatif"
"$A" core list
"$A" lib list
uv run python -c "import sys, numpy, tensorflow as tf; print('Python', sys.version.split()[0], '| TensorFlow', tf.__version__, '| NumPy', numpy.__version__)"
