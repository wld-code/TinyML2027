#!/usr/bin/env bash
# Lance idf.py avec l'ESP-IDF isolé du projet. Exemple : ./scripts/esp.sh -C <projet> build
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export IDF_TOOLS_PATH="$ROOT/.esp/tools"
[ -f "$ROOT/.esp/esp-idf/export.sh" ] || { echo "ERREUR : lancez ./scripts/setup_esp.sh" >&2; exit 1; }
# shellcheck disable=SC1091
. "$ROOT/.esp/esp-idf/export.sh" >/dev/null
exec idf.py "$@"
