"""Outil d'acquisition du TP01 (ligne de commande).

  uv run python -m tinyml2027.capture ports
  uv run python -m tinyml2027.capture info    [--port PORT]
  uv run python -m tinyml2027.capture record  --session s01 --condition stationary --trial 1 [--port PORT]
  uv run python -m tinyml2027.capture guided  --session s01 [--port PORT]

Sans --port, l'outil choisit la carte Arduino (VID 0x2341) si elle est SEULE ;
sinon il s'arrête et liste les ports. Aucun nom de port n'est supposé.

Après chaque enregistrement, le contrôle qualité s'affiche et l'on accepte (o) ou
refuse (n) l'essai. Les essais refusés sont conservés dans data/rejected/ et
tracés dans le manifest avec valid=0 : on ne les efface pas, on les met de côté.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import dataset, recording

ARDUINO_VID = 0x2341
INSTRUCTIONS = {
    "stationary": "Posez la carte à plat sur la table et NE LA TOUCHEZ PLUS (câble immobile aussi).",
    "periodic": "Faites glisser la carte en avant et en arrière DANS LE SENS DU CÂBLE (axe x), régulièrement "
                "(environ 1 aller-retour par seconde), sans la tourner.",
    "impact": "Carte posée à plat. Tapotez doucement la table à côté de la carte, 1 à 2 fois par seconde, "
              "pendant TOUT l'enregistrement. Ne frappez jamais la carte.",
}


class CaptureError(RuntimeError):
    pass


def list_ports():
    from serial.tools import list_ports as lp

    return list(lp.comports())


def pick_port(port: str | None):
    """Renvoie (device, numéro de série USB)."""
    ports = list_ports()
    if port:
        for p in ports:
            if p.device == port:
                return p.device, p.serial_number
        return port, None
    arduinos = [p for p in ports if p.vid == ARDUINO_VID]
    if len(arduinos) != 1:
        listing = "\n".join(f"  {p.device}  {p.description}  VID:PID={p.vid}:{p.pid}" for p in ports) or "  (aucun)"
        raise CaptureError(f"{len(arduinos)} carte(s) Arduino détectée(s) ; précisez --port.\nPorts :\n{listing}")
    return arduinos[0].device, arduinos[0].serial_number


def open_port(device: str):
    import serial

    try:
        ser = serial.Serial(device, 115200, timeout=0.2)
    except serial.SerialException as e:
        raise CaptureError(f"impossible d'ouvrir {device} : {e}\n"
                           "Le port est-il déjà ouvert (moniteur série, IDE, notebook) ?") from e
    time.sleep(0.3)
    ser.reset_input_buffer()
    return ser


def _readline(ser) -> str | None:
    raw = ser.readline()
    if not raw:
        return None
    return raw.decode("utf-8", "replace").rstrip("\r\n")


def command(ser, cmd: str, expect: str, timeout_s: float = 3.0) -> str:
    ser.write((cmd + "\n").encode())
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        line = _readline(ser)
        if line is None:
            continue
        if line.startswith("ERREUR"):
            raise CaptureError(f"la carte répond : {line}")
        if line.startswith(expect):
            return line
    raise CaptureError(f"pas de réponse « {expect} » à « {cmd} » en {timeout_s} s. "
                       "Le firmware imu_capture est-il téléversé ?")


def parse_fields(line: str) -> dict:
    return dict(item.split("=", 1) for item in line.split()[1:] if "=" in item)


def acquire(ser, rid: str, duration_s: float):
    """Lance START, lit pendant duration_s, envoie STOP et attend END. Renvoie (info, lignes, n_annoncé)."""
    begin = command(ser, f"START {rid}", "BEGIN")
    info = parse_fields(begin)
    lines: list[str] = []
    t0 = time.monotonic()
    last_print = 0.0
    while time.monotonic() - t0 < duration_s:
        line = _readline(ser)
        if line is None:
            continue
        if line.startswith("ERREUR"):
            raise CaptureError(f"la carte répond : {line}")
        if line and line[0].isdigit():
            lines.append(line)
        el = time.monotonic() - t0
        if el - last_print >= 1.0:
            last_print = el
            print(f"\r  enregistrement… {el:4.0f} / {duration_s:.0f} s   ({len(lines)} échantillons)", end="", flush=True)
    print()
    ser.write(b"STOP\n")
    t1 = time.monotonic()
    n_announced = None
    while time.monotonic() - t1 < 5.0:
        line = _readline(ser)
        if line is None:
            continue
        if line.startswith("END"):
            n_announced = int(parse_fields(line)["n"])
            break
        if line and line[0].isdigit():
            lines.append(line)
    if n_announced is None:
        raise CaptureError("la carte n'a pas confirmé la fin (END) : déconnexion ?")
    return info, lines, n_announced


def ask(prompt: str, default_yes: bool) -> bool:
    try:
        ans = input(prompt).strip().lower()
    except EOFError:
        return default_yes
    if not ans:
        return default_yes
    return ans in ("o", "oui", "y", "yes")


def record_one(ser, usb_serial, args, condition: str, trial: int) -> bool:
    rid = dataset.recording_id(args.session, condition, trial)
    root = Path(args.data)
    if any(r["recording_id"] == rid for r in dataset.read_manifest(root)):
        raise CaptureError(f"{rid} existe déjà dans {root / 'manifest.csv'} : utilisez --trial {trial + 1}")
    print(f"\n=== {rid} ===\n{INSTRUCTIONS[condition]}")
    if not args.yes:
        input("Appuyez sur Entrée pour lancer le compte à rebours… ")
    for i in range(args.countdown, 0, -1):
        print(f"  départ dans {i}…", flush=True)
        time.sleep(1)
    if condition != "stationary":
        # Le geste doit être déjà en cours quand l'enregistrement commence : sinon les
        # premières fenêtres, étiquetées « periodic » ou « impact », seraient immobiles.
        print("  COMMENCEZ LE GESTE MAINTENANT — l'enregistrement démarre dans 2 s, continuez jusqu'à la fin")
        time.sleep(2)
    print("  ENREGISTREMENT EN COURS")
    info, lines, n_announced = acquire(ser, rid, args.duration)
    df, rejected = recording.parse_lines(lines)
    qc = recording.quality(df, min_windows=args.min_windows)
    notes = []
    if rejected:
        notes.append(f"{len(rejected)} ligne(s) illisible(s)")
    if n_announced != len(df):
        notes.append(f"carte: {n_announced} échantillons envoyés, PC: {len(df)} reçus")
        qc.valid = False
        qc.reasons.append("échantillons perdus entre la carte et le PC")
    print(recording.format_report(qc))
    for n in notes:
        print("  note :", n)

    if args.yes:
        accepted = qc.valid
    else:
        accepted = ask(f"Accepter cet essai ? [{'O/n' if qc.valid else 'o/N'}] ", qc.valid)
    if accepted and not qc.valid:
        notes.append("accepté malgré un QC invalide (décision opérateur)")
    if not accepted:
        notes.append("refusé par l'opérateur" if qc.valid else "refusé (QC invalide)")

    path = dataset.recording_path(root, args.session, rid, accepted)
    recording.write_csv(df, path)
    meta = {
        "recording_id": rid, "session_id": args.session, "condition": condition, "trial": trial,
        "source": "hardware", "firmware": info.get("firmware"), "board_revision": info.get("board_revision"),
        "imu": info.get("imu"), "odr_nominal_hz": float(info.get("odr_nominal_hz", "nan")),
        "board_id": dataset.board_id(usb_serial), "requested_duration_s": args.duration,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "os": f"{platform.system()} {platform.release()}", "python": platform.python_version(),
        "protocol": INSTRUCTIONS[condition], "quality": qc.to_dict(), "notes": notes, "accepted": accepted,
    }
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    dataset.append_manifest(root, {
        "recording_id": rid, "session_id": args.session, "condition": condition, "trial": trial,
        "board_revision": info.get("board_revision"), "board_id": meta["board_id"], "source": "hardware",
        "requested_fs_hz": info.get("odr_nominal_hz"), "measured_fs_hz": f"{qc.measured_fs_hz:.3f}",
        "valid": int(accepted), "notes": "; ".join(notes),
    })
    print(f"  -> {'ACCEPTÉ' if accepted else 'REFUSÉ'} : {path}")
    return accepted


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tinyml2027.capture", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ports", help="liste les ports série")
    p_info = sub.add_parser("info", help="interroge le firmware")
    p_info.add_argument("--port")
    for name in ("record", "guided"):
        p = sub.add_parser(name)
        p.add_argument("--port")
        p.add_argument("--session", required=True, help="identifiant de session, ex. s01")
        p.add_argument("--duration", type=float, default=20.0, help="durée en secondes (défaut 20)")
        p.add_argument("--countdown", type=int, default=3)
        p.add_argument("--min-windows", type=int, default=3, help="fenêtres de 256 sans lacune exigées")
        p.add_argument("--data", default="data", help="dossier du dataset (défaut data/)")
        p.add_argument("--yes", action="store_true", help="sans question : accepte si le QC est valide")
        if name == "record":
            p.add_argument("--condition", required=True, choices=dataset.CONDITIONS)
            p.add_argument("--trial", type=int, default=1)
        else:
            p.add_argument("--trial", type=int, default=1, help="numéro d'essai pour les 3 conditions")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "ports":
            for p in list_ports():
                tag = "  <- Arduino" if p.vid == ARDUINO_VID else ""
                print(f"{p.device}  {p.description}  VID:PID={p.vid}:{p.pid}{tag}")
            return 0
        device, usb_serial = pick_port(args.port)
        with open_port(device) as ser:
            info = command(ser, "INFO", "INFO")
            print(f"{device} : {info}")
            if args.cmd == "info":
                return 0
            if args.cmd == "record":
                ok = record_one(ser, usb_serial, args, args.condition, args.trial)
                return 0 if ok else 1
            results = {}
            for cond in dataset.CONDITIONS:
                trial = args.trial
                while True:
                    ok = record_one(ser, usb_serial, args, cond, trial)
                    results[cond] = ok
                    if ok or args.yes or not ask("Recommencer cette condition ? [O/n] ", True):
                        break
                    trial += 1
            print("\nBilan session", args.session, ":", ", ".join(f"{c}={'OK' if v else 'refusé'}" for c, v in results.items()))
            return 0 if all(results.values()) else 1
    except CaptureError as e:
        print(f"ERREUR : {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
