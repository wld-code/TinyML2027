#!/usr/bin/env bash
# Installe ESP-IDF (version et commit de config/versions.lock) dans .esp/ du projet,
# avec ses outils pour la seule cible ESP32-S3. N'utilise ni ne modifie ~/esp ni ~/.espressif.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
while IFS='=' read -r key value; do
  case "$key" in ''|\#*) continue ;; esac
  printf -v "$key" '%s' "$value"
done < "$ROOT/config/versions.lock"
IDF="$ROOT/.esp/esp-idf"
export IDF_TOOLS_PATH="$ROOT/.esp/tools"
if [ ! -d "$IDF/.git" ]; then
  git clone --depth 1 --branch "$ESP_IDF_VERSION" --recursive --shallow-submodules \
    https://github.com/espressif/esp-idf.git "$IDF"
fi
test "$(git -C "$IDF" rev-parse HEAD)" = "$ESP_IDF_COMMIT" || { echo "ERREUR : commit ESP-IDF inattendu"; exit 1; }
"$IDF/install.sh" "$ESP_IDF_TARGET"
# shellcheck disable=SC1091
. "$IDF/export.sh" >/dev/null
idf.py --version
xtensa-esp32s3-elf-gcc --version | head -1
