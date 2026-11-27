#!/usr/bin/env bash
# Lance arduino-cli dans l'environnement isolé du dépôt (macOS, Linux, Windows via Git Bash).
# Exemple : ./scripts/arduino.sh board list
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ "${1:-}" = monitor ]; then
  args=("$@")
  for ((i = 1; i < $#; i++)); do
    case "${args[i]}" in
      --) break ;;
      -p|--port)
        i=$((i + 1))
        case "${args[i]:-}" in
          PORT)
            source "$ROOT/scripts/nano-port.sh"
            args[i]="$(nano_port)" || {
              echo 'Indiquez le port de la carte après -p.' >&2
              exit 1
            }
            ;;
          PORT=*) args[i]="${args[i]#PORT=}" ;;
        esac
        ;;
    esac
  done
  set -- "${args[@]}"
fi
# Git Bash : arduino-cli.exe attend des chemins Windows (C:/...)
EXE=""
if command -v cygpath >/dev/null 2>&1; then ROOT="$(cygpath -m "$ROOT")"; EXE=".exe"; fi
export ARDUINO_DIRECTORIES_DATA="$ROOT/.arduino/data"
export ARDUINO_DIRECTORIES_DOWNLOADS="$ROOT/.arduino/staging"
export ARDUINO_DIRECTORIES_USER="$ROOT/.arduino/user"
CLI="$ROOT/.arduino/bin/arduino-cli$EXE"
[ -x "$CLI" ] || { echo "ERREUR : $CLI absent. Lancez ./scripts/setup.sh" >&2; exit 1; }
exec "$CLI" --config-file "$ROOT/arduino-cli.yaml" "$@"
