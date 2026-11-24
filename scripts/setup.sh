#!/usr/bin/env bash
# Installe l'environnement figé de TinyML2027 dans le dossier du projet.
# macOS Apple Silicon : vérifié sur poste réel. Linux et Windows (Git Bash) : voir docs/VALIDATION.md.
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
done < <(tr -d '\r' < "$ROOT/config/versions.lock")  # \r : fichier en CRLF sous Windows
A="$ROOT/scripts/arduino.sh"

step() { printf '\n=== %s\n' "$*"; }

step "Arduino CLI $ARDUINO_CLI_VERSION"
# Archive officielle selon le système ; Windows : lancer ce script dans Git Bash.
case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)              PKG=macOS_ARM64;   EXT=tar.gz; SHA=$ARDUINO_CLI_MACOS_ARM64_SHA256 ;;
  Darwin-x86_64)             PKG=macOS_64bit;   EXT=tar.gz; SHA=$ARDUINO_CLI_MACOS_64BIT_SHA256 ;;
  Linux-x86_64)              PKG=Linux_64bit;   EXT=tar.gz; SHA=$ARDUINO_CLI_LINUX_64BIT_SHA256 ;;
  Linux-aarch64|Linux-arm64) PKG=Linux_ARM64;   EXT=tar.gz; SHA=$ARDUINO_CLI_LINUX_ARM64_SHA256 ;;
  MINGW64*-x86_64|MSYS*-x86_64|CYGWIN*-x86_64) PKG=Windows_64bit; EXT=zip; SHA=$ARDUINO_CLI_WINDOWS_64BIT_SHA256 ;;
  *) echo "ERREUR : système $(uname -s)-$(uname -m) non prévu (voir docs/installation.md)"; exit 1 ;;
esac
EXE=""; [ "$EXT" = zip ] && EXE=".exe"
sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }
BIN="$ROOT/.arduino/bin/arduino-cli$EXE"
if ! { [ -x "$BIN" ] && "$BIN" version | grep -q "Version: $ARDUINO_CLI_VERSION "; }; then
  mkdir -p "$ROOT/.arduino/dl" "$ROOT/.arduino/bin"
  ARC="arduino-cli_${ARDUINO_CLI_VERSION}_${PKG}.${EXT}"
  curl -fsSL -o "$ROOT/.arduino/dl/$ARC" "https://downloads.arduino.cc/arduino-cli/$ARC"
  GOT="$(sha256 "$ROOT/.arduino/dl/$ARC")"
  [ "$GOT" = "$SHA" ] || { echo "ERREUR : SHA-256 de $ARC = $GOT, attendu $SHA"; exit 1; }
  echo "$ARC : SHA-256 OK"
  if [ "$EXT" = zip ]; then
    powershell -NoProfile -Command "Expand-Archive -Force '$(cygpath -w "$ROOT/.arduino/dl/$ARC")' '$(cygpath -w "$ROOT/.arduino/bin")'"
  else
    tar -xzf "$ROOT/.arduino/dl/$ARC" -C "$ROOT/.arduino/bin" arduino-cli
  fi
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
command -v uv >/dev/null || { echo "ERREUR : uv absent (https://docs.astral.sh/uv/getting-started/installation/)"; exit 1; }
uv sync --frozen

step "Récapitulatif"
"$A" core list
"$A" lib list
uv run python -c "import sys, numpy, tensorflow as tf; print('Python', sys.version.split()[0], '| TensorFlow', tf.__version__, '| NumPy', numpy.__version__)"
