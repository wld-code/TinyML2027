"""Archive, contrôle et déploiement USB supervisé d’une release vocale."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from tinyml2027.capture import CaptureError, open_port
from tinyml2027.release import ReleaseError, arduino_cli, pick_port

from build_firmware import LAB, ROOT
from monitor import MonitorError, handshake
from pipeline import PipelineError, file_sha256, gate_report, read_json, validate_zip

TARGET = {"board": "ABX00031", "fqbn": "arduino:mbed_nano:nano33ble", "core": "arduino:mbed_nano@4.6.0"}
FILES = {
    "arduino-int8.zip", "kws_nano.ino.bin", "experiment.json", "manifest.csv",
    "metrics.json", "baseline.json", "hardware.json", "model.json",
    "quality-gates.json", "gates.json", "kws_nano.ino", "versions.lock",
}
MANIFEST = "release_manifest.json"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def checks(folder):
    baseline, metrics, policy, hardware = [
        read_json(folder / name) for name in ("baseline.json", "metrics.json", "quality-gates.json", "hardware.json")
    ]
    return gate_report(baseline, metrics, policy, hardware)


def validate(folder):
    if (folder / MANIFEST).is_symlink():
        raise ReleaseError("Le manifeste doit être un fichier local.")
    release = read_json(folder / MANIFEST)
    if (release["schema_version"] != 1 or release["target"] != TARGET
            or release["version"] != folder.name or not re.fullmatch(r"kws-v[1-9][0-9]*", folder.name)):
        raise ReleaseError("Cible ou version incompatible.")
    if set(release["files"]) != FILES or {entry.name for entry in folder.iterdir()} != FILES | {MANIFEST}:
        raise ReleaseError("Contenu de la release incomplet ou inattendu.")
    for name, expected in release["files"].items():
        path = folder / name
        if path.is_symlink() or not path.is_file() or file_sha256(path) != expected:
            raise ReleaseError(f"Intégrité invalide pour {name}.")

    experiment = read_json(folder / "experiment.json")
    export_sha = release["files"]["arduino-int8.zip"]
    dataset_sha = release["files"]["manifest.csv"]
    if (experiment["name"] != release["version"] or experiment["arduino_export_sha256"] != export_sha
            or experiment["manifest_sha256"] != dataset_sha
            or read_json(folder / "metrics.json")["manifest_sha256"] != dataset_sha):
        raise ReleaseError("Provenance de l’export, des métriques ou du dataset incohérente.")
    header = validate_zip((folder / "arduino-int8.zip").read_bytes())
    if not re.search(rf"^#define\s+EI_CLASSIFIER_PROJECT_ID\s+{int(experiment['project_id'])}\s*$", header, re.M):
        raise ReleaseError("Le projet Studio annoncé diffère de celui du ZIP.")
    image = (folder / "kws_nano.ino.bin").read_bytes()
    for value in (release["version"], release["firmware"], export_sha):
        if value.encode("ascii") + b"\0" not in image and ('"' + value + '"').encode("ascii") not in image:
            raise ReleaseError(f"Identité absente du firmware : {value}.")
    if read_json(folder / "gates.json") != checks(folder):
        raise ReleaseError("Le rapport des critères diffère du calcul sur les données archivées.")
    return release


def archive(args):
    target = args.destination
    if target.exists() or target.is_symlink():
        raise ReleaseError(f"La release {target} existe déjà.")
    sources = {name: args.artifacts / name for name in ("arduino-int8.zip", "experiment.json", "manifest.csv")}
    sources.update({
        "kws_nano.ino.bin": args.binary,
        "metrics.json": args.metrics,
        "baseline.json": args.baseline,
        "hardware.json": args.hardware,
        "model.json": LAB / "config/model.json",
        "quality-gates.json": LAB / "config/quality-gates.json",
        "kws_nano.ino": LAB / "firmware/kws_nano/kws_nano.ino",
        "versions.lock": ROOT / "config/versions.lock",
    })
    revision = re.search(r'"firmware\\":\\"(kws_nano [0-9.]+)', sources["kws_nano.ino"].read_text(encoding="utf-8"))
    if not revision:
        raise ReleaseError("Version du sketch introuvable.")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as work:
        staged = Path(work) / target.name
        staged.mkdir()
        for name, source in sources.items():
            shutil.copyfile(source, staged / name)
        write_json(staged / "gates.json", checks(staged))
        manifest = {
            "schema_version": 1,
            "version": target.name,
            "firmware": revision[1],
            "target": TARGET,
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
            "files": {name: file_sha256(staged / name) for name in sorted(FILES)},
        }
        write_json(staged / MANIFEST, manifest)
        validate(staged)
        staged.rename(target)
    return manifest


def upload(folder, manifest, operation, port, yes):
    decision = read_json(folder / "gates.json")["decision"]
    if operation == "flash" and decision != "accepted":
        raise ReleaseError(f"{manifest['version']} est {decision}. Téléversement bloqué avant l’ouverture du port.")
    if operation == "restore" and decision != "accepted":
        hardware = read_json(folder / "hardware.json")
        if (manifest["version"] != "kws-v1" or hardware.get("firmware_init") is not True
                or hardware.get("verified_binary_sha256") != manifest["files"]["kws_nano.ino.bin"]):
            raise ReleaseError("La restauration exige une release acceptée ou la référence v1 vérifiée sur la Nano.")
    port = pick_port(port)
    binary = folder / "kws_nano.ino.bin"
    print(f"{operation} {manifest['version']} sur {port}\nBinaire {binary}\nSHA-256 {file_sha256(binary)}", flush=True)
    if not yes and input("Confirmer le téléversement USB [o/N] ").lower().strip() not in ("o", "oui"):
        raise ReleaseError("Téléversement annulé.")
    result = arduino_cli("upload", "-p", port, "--fqbn", TARGET["fqbn"], "--input-file", str(binary.resolve()))
    print(result.stdout, end="")
    if result.returncode:
        raise ReleaseError(result.stderr.strip() or "Téléversement en échec.")
    time.sleep(2)
    with open_port(port) as device:
        identity = handshake(device, manifest["files"]["arduino-int8.zip"])
    if identity["release"] != manifest["version"] or identity["firmware"] != manifest["firmware"]:
        raise ReleaseError("Version du firmware différente de la release demandée.")
    return {
        "utc": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "binary_sha256": manifest["files"]["kws_nano.ino.bin"],
        "identity": identity,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("archive")
    create.add_argument("destination", type=Path)
    for name in ("artifacts", "binary", "metrics", "baseline", "hardware"):
        create.add_argument("--" + name, type=Path, required=True)
    for name in ("verify", "flash", "restore"):
        command = commands.add_parser(name)
        command.add_argument("folder", type=Path)
        if name != "verify":
            command.add_argument("--port")
            command.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "archive":
            result = archive(args)
        else:
            result = validate(args.folder)
            if args.command != "verify":
                result = upload(args.folder, result, args.command, args.port, args.yes)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ReleaseError, PipelineError, CaptureError, MonitorError, OSError, ValueError,
            KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
