# Fonctions de détection du port, chargées par arduino.sh et upload.sh.

nano_port() {
  local fqbn boards ports count
  fqbn="$(awk -F= '$1 == "ARDUINO_FQBN" { sub(/\r$/, "", $2); print $2 }' "$ROOT/config/versions.lock")"
  boards="$("$ROOT/scripts/arduino.sh" board list)" || return
  ports="$(awk -v fqbn="$fqbn" '$0 ~ fqbn {print $1}' <<< "$boards")"
  count="$(grep -c . <<< "$ports" || true)"
  if [ "$count" != 1 ]; then
    printf 'Impossible de choisir un port automatiquement (%s carte(s) %s détectée(s)).\n%s\n' \
      "$count" "$fqbn" "$boards" >&2
    return 1
  fi
  printf '%s\n' "$ports"
}
