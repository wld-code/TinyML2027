"""Edge MLOps — construire, valider, téléverser et vérifier une release du modèle de mouvements.

  uv run python -m tinyml2027.release build    --version motion-v1 [--artifacts artifacts/motion]
  uv run python -m tinyml2027.release validate releases/motion-v1
  uv run python -m tinyml2027.release flash    releases/motion-v1 [--port PORT] [--yes]
  uv run python -m tinyml2027.release status   [--port PORT]

Une release est un dossier IMMUABLE : releases/<version>/ contient le firmware compilé,
le modèle, le prétraitement, les labels, les golden vectors, les métriques et un
release_manifest.json qui liste le SHA-256 de chaque fichier.

`validate` refuse une release AVANT tout téléversement si : un fichier manque ou a
changé (SHA-256), le manifest est incomplet, les labels ou le schéma de features
diffèrent du contrat attendu, ou la carte/le core visés ne sont pas ceux du dépôt.

`flash` = validate, puis affichage du plan, confirmation, téléversement USB supervisé
(ce n'est PAS une mise à jour à distance), puis vérification de ce que la carte annonce
réellement (version, SHA-256 du modèle) et du rejeu des golden vectors. L'état
« souhaité » (ce qu'on a voulu installer) n'est « confirmé » qu'après ces contrôles.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKETCH = ROOT / "labs/03-embedded-inference/firmware/infer_nano"
EXPECTED_LABELS = ["stationary", "periodic", "impact"]
EXPECTED_SCHEMA = ["log10(rms_g + 1e-6)", "crest_factor", "dominant_hz", "log10(band_power_g2 + 1e-12)"]
REQUIRED = ["model_version", "firmware_version", "model_int8_sha256", "files", "board", "board_core",
            "board_revision", "runtime", "feature_schema", "labels", "tested_os", "acceptance_status"]
STATE = ROOT / "releases/device_state.json"


class ReleaseError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def arduino_cli(*args: str) -> subprocess.CompletedProcess:
    """arduino-cli isolé du dépôt, comme scripts/arduino.sh, mais sans bash.

    Windows ne peut pas exécuter un .sh via subprocess (WinError 193, constaté le 2026-11-24),
    et le « bash » du PATH peut y être celui de WSL : on appelle donc l'exécutable directement.
    """
    import os
    exe = ROOT / ".arduino/bin" / ("arduino-cli.exe" if os.name == "nt" else "arduino-cli")
    if not exe.exists():
        raise ReleaseError(f"{exe} absent : lancez ./scripts/setup.sh")
    env = dict(os.environ,
               ARDUINO_DIRECTORIES_DATA=str(ROOT / ".arduino/data"),
               ARDUINO_DIRECTORIES_DOWNLOADS=str(ROOT / ".arduino/staging"),
               ARDUINO_DIRECTORIES_USER=str(ROOT / ".arduino/user"))
    return subprocess.run([str(exe), "--config-file", str(ROOT / "arduino-cli.yaml"), *args],
                          capture_output=True, text=True, env=env)


def versions_lock() -> dict:
    out = {}
    for line in (ROOT / "config/versions.lock").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k] = v
    return out


def firmware_version() -> str:
    m = re.search(r'kFirmware\[\] = "([^"]+)"', (SKETCH / "infer_nano.ino").read_text(encoding="utf-8"))
    return m.group(1) if m else "inconnu"


# ------------------------------------------------------------------ build

def build(version: str, artifacts: Path, build_dir: Path, sketch: Path, out_root: Path) -> Path:
    params = (sketch / "model_params.h").read_text(encoding="utf-8")
    m = re.search(r'kModelVersion\[\] = "([^"]+)"', params)
    if not m or m.group(1) != version:
        raise ReleaseError(f"model_params.h annonce {m.group(1) if m else '?'} et non {version} : "
                           f"relancez quantize_motion --model-version {version}, puis compilez")
    model_h = (sketch / "model_data.h").read_text(encoding="utf-8")
    sha_h = re.search(r'g_model_sha256\[\] = "([0-9a-f]{64})"', model_h).group(1)
    if sha_h != sha256(artifacts / "model_int8.tflite"):
        raise ReleaseError("model_data.h ne correspond pas à model_int8.tflite : régénérez les en-têtes")
    bins = sorted(build_dir.glob("*.ino.bin"))
    if not bins:
        raise ReleaseError(f"pas de firmware compilé dans {build_dir} : lancez scripts/compile.sh")
    if bins[0].stat().st_mtime < (sketch / "model_data.h").stat().st_mtime:
        raise ReleaseError("le firmware compilé est plus ancien que les en-têtes du modèle : recompilez")

    dest = out_root / version
    if dest.exists():
        raise ReleaseError(f"{dest} existe déjà : une release est immuable, choisissez une autre version")
    (dest / "firmware").mkdir(parents=True)
    for f in ("model_int8.tflite", "model_fp32.tflite", "preprocessing.json", "labels.json", "metrics.json",
              "golden_vectors.npz", "training_config.json", "comparison.json"):
        shutil.copy2(artifacts / f, dest / f)
    for f in build_dir.iterdir():
        if f.suffix in (".bin", ".hex", ".elf", ".map") or f.name.endswith(".with_bootloader.hex"):
            shutil.copy2(f, dest / "firmware" / f.name)
    for f in ("model_data.h", "model_params.h", "golden.h"):
        shutil.copy2(sketch / f, dest / "firmware" / f)

    lock = versions_lock()
    prep = json.loads((artifacts / "preprocessing.json").read_text(encoding="utf-8"))
    metrics = json.loads((artifacts / "metrics.json").read_text(encoding="utf-8"))
    files = {str(p.relative_to(dest)): sha256(p) for p in sorted(dest.rglob("*")) if p.is_file()}
    manifest = {
        "model_version": version,
        "firmware_version": firmware_version(),
        "model_int8_sha256": sha256(dest / "model_int8.tflite"),
        "firmware_bin": bins[0].name,
        "files": files,
        "board": lock["ARDUINO_FQBN"],
        "board_core": lock["ARDUINO_CORE"],
        "board_revision": "rev2" if build_dir.name.endswith("-rev2") else "original",
        "runtime": f"Arduino_TensorFlowLite@{lock['TFLM_ARDUINO_COMMIT'][:8]}",
        "feature_schema": prep["inputs"],
        "labels": json.loads((artifacts / "labels.json").read_text(encoding="utf-8")),
        "test_metrics": {"session": json.loads((artifacts / "training_config.json").read_text(encoding="utf-8"))["test_session"],
                         "macro_f1": metrics["test"]["dense"]["macro_f1"]},
        "tested_os": [],
        "acceptance_status": "candidate",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (dest / "release_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return dest


# ------------------------------------------------------------------ validate

def validate(release: Path) -> dict:
    """Renvoie le manifest si la release est acceptable ; lève ReleaseError sinon."""
    mpath = release / "release_manifest.json"
    if not mpath.exists():
        raise ReleaseError(f"{mpath} absent")
    try:
        man = json.loads(mpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ReleaseError(f"manifest illisible (JSON invalide) : {e}") from e
    missing = [k for k in REQUIRED if k not in man]
    if missing:
        raise ReleaseError(f"champs absents du manifest : {missing}")
    for rel, digest in man["files"].items():
        p = release / rel
        if not p.exists():
            raise ReleaseError(f"fichier manquant : {rel}")
        if sha256(p) != digest:
            raise ReleaseError(f"fichier modifié depuis la release (SHA-256 différent) : {rel}")
    if man["model_int8_sha256"] != sha256(release / "model_int8.tflite"):
        raise ReleaseError("model_int8_sha256 ne correspond pas au modèle")
    if man["labels"] != EXPECTED_LABELS:
        raise ReleaseError(f"labels {man['labels']} différents du contrat {EXPECTED_LABELS}")
    if man["feature_schema"] != EXPECTED_SCHEMA:
        raise ReleaseError(f"schéma de features différent du contrat : {man['feature_schema']}")
    lock = versions_lock()
    if man["board"] != lock["ARDUINO_FQBN"] or man["board_core"] != lock["ARDUINO_CORE"]:
        raise ReleaseError(f"carte/core {man['board']} {man['board_core']} différents du dépôt")
    if not (release / "firmware" / man["firmware_bin"]).exists():
        raise ReleaseError("binaire du firmware absent")
    if "golden_vectors.npz" not in man["files"]:
        raise ReleaseError("golden vectors absents : impossible de vérifier la carte après mise à jour")
    return man


# ------------------------------------------------------------------ device

def read_device(port: str, timeout_s: float = 10.0) -> dict:
    """Demande un rejeu (R) et renvoie ce que la carte annonce : version, SHA-256, statut du rejeu."""
    import serial

    info, lines = {}, []
    with serial.Serial(port, 115200, timeout=0.3) as ser:
        time.sleep(0.5)
        ser.reset_input_buffer()
        ser.write(b"R")
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout_s:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", "replace").rstrip()
            lines.append(line)
            info.update(re.findall(r"(\w+)=(\S+)", line) if line.startswith("#") else [])
            if line.startswith("ERREUR"):
                info["erreur"] = line
            if line.startswith("REPLAY STATUT"):
                info["replay"] = line.split()[-1]
                break
    info["log"] = lines
    return info


def pick_port(port: str | None) -> str:
    from .capture import pick_port as pp
    return pp(port)[0]


def flash(release: Path, port: str | None, yes: bool) -> int:
    man = validate(release)
    port = pick_port(port)
    print(f"Release {man['model_version']} VALIDE (fichiers, SHA-256, labels, schéma, carte).")
    print("Plan :")
    print(f"  1. téléverser {release / 'firmware' / man['firmware_bin']} sur {port} (USB, supervisé)")
    print(f"  2. lire ce que la carte annonce et exiger model_version={man['model_version']}, "
          f"model_sha256={man['model_int8_sha256'][:16]}…")
    print("  3. exiger REPLAY STATUT OK sur les golden vectors")
    if not yes and input("Continuer ? [o/N] ").strip().lower() not in ("o", "oui", "y"):
        print("Annulé : rien n'a été téléversé.")
        return 1
    _write_state({"desired": man["model_version"], "confirmed": None, "port": port})
    r = arduino_cli("upload", "-p", port, "--fqbn", man["board"],
                    "--input-file", str(release / "firmware" / man["firmware_bin"]))
    if r.returncode != 0:
        print(r.stdout[-500:], r.stderr[-500:])
        print("ÉCHEC DU TÉLÉVERSEMENT. La carte peut être dans l'ancien état ou sans programme : "
              "double-cliquez sur RESET puis relancez flash avec la release précédente.")
        return 2
    time.sleep(2.0)
    dev = read_device(port)
    print(f"La carte annonce : model_version={dev.get('model_version')} "
          f"model_sha256={str(dev.get('model_sha256'))[:16]}… replay={dev.get('replay')}")
    checks = {
        "version": dev.get("model_version") == man["model_version"],
        "sha256": dev.get("model_sha256") == man["model_int8_sha256"],
        "replay": dev.get("replay") == "OK",
    }
    ok = all(checks.values())
    log = release.parent / f"flash-{man['model_version']}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.log"
    log.write_text("\n".join(dev["log"]) + f"\n# contrôles {checks}\n", encoding="utf-8", newline="\n")
    if ok:
        _write_state({"desired": man["model_version"], "confirmed": man["model_version"], "port": port})
        print(f"CONFIRMÉ : la carte exécute {man['model_version']} et rejoue ses golden vectors. Journal : {log.name}")
        return 0
    _write_state({"desired": man["model_version"], "confirmed": None, "port": port,
                  "failed_checks": [k for k, v in checks.items() if not v]})
    print(f"ACCEPTATION REFUSÉE {[k for k, v in checks.items() if not v]}. Journal : {log.name}")
    print("Revenez à la dernière release confirmée : python -m tinyml2027.release flash releases/<version précédente>")
    return 3


def _write_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    state["updated_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tinyml2027.release", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--version", required=True)
    b.add_argument("--artifacts", type=Path, default=ROOT / "artifacts/motion")
    b.add_argument("--build-dir", type=Path, default=ROOT / "build/infer_nano")
    b.add_argument("--sketch", type=Path, default=SKETCH)
    b.add_argument("--out", type=Path, default=ROOT / "releases")
    v = sub.add_parser("validate")
    v.add_argument("release", type=Path)
    f = sub.add_parser("flash")
    f.add_argument("release", type=Path)
    f.add_argument("--port")
    f.add_argument("--yes", action="store_true")
    s = sub.add_parser("status")
    s.add_argument("--port")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "build":
            dest = build(args.version, args.artifacts, args.build_dir, args.sketch, args.out)
            print(f"release écrite : {dest}")
            validate(dest)
            print("validation : OK")
            return 0
        if args.cmd == "validate":
            man = validate(args.release)
            print(f"VALIDE : {man['model_version']} (firmware {man['firmware_version']}, "
                  f"modèle {man['model_int8_sha256'][:16]}…, {len(man['files'])} fichiers vérifiés)")
            return 0
        if args.cmd == "flash":
            return flash(args.release, args.port, args.yes)
        dev = read_device(pick_port(args.port))
        state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
        print(f"état souhaité  : {state.get('desired')}")
        print(f"état confirmé  : {state.get('confirmed')}")
        print(f"la carte annonce : {dev.get('model_version')} / {str(dev.get('model_sha256'))[:16]}… / replay {dev.get('replay')}")
        return 0
    except ReleaseError as e:
        print(f"REFUSÉ : {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
