"""Contrôle guidé de l'IMU (phase 6 / tutoriel 02), avec le firmware examples/04_imu.

  uv run python -m tinyml2027.imu_check [--port PORT] [--log fichier.txt]

On pose la carte successivement dans 6 positions. Pour chacune, l'outil lit 2 s de
mesures, puis vérifie que :
  - la carte est immobile (écart-type de |a| < 0,05 g, la carte peut être tenue à la main) ;
  - la norme de l'accélération vaut 1 g à ±0,1 g près (seule la gravité agit) ;
  - un seul axe porte la gravité.
Il ne suppose PAS l'orientation des axes : il la découvre et vérifie que les 6
positions donnent bien les 6 directions ±X, ±Y, ±Z, chacune une seule fois.
Enfin, on fait tourner la carte dans tous les sens pendant 4 s : chaque axe du
gyroscope doit dépasser 30 °/s.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .capture import CaptureError, open_port, pick_port

POSITIONS = [
    "à plat sur la table, puces vers le HAUT",
    "à plat, retournée : puces contre la table",
    "debout devant vous, puces face à vous, câble USB vers le BAS",
    "debout devant vous, puces face à vous, câble USB vers le HAUT",
    "debout devant vous, puces face à vous, câble USB vers la GAUCHE",
    "debout devant vous, puces face à vous, câble USB vers la DROITE",
]


def read_block(ser, seconds: float) -> np.ndarray:
    """Lit les lignes CSV de 04_imu pendant `seconds` ; renvoie un tableau (n, 6)."""
    rows = []
    t0 = time.monotonic()
    ser.reset_input_buffer()
    while time.monotonic() - t0 < seconds:
        raw = ser.readline()
        if not raw:
            continue
        parts = raw.decode("utf-8", "replace").strip().split(",")
        if parts[0].startswith("ERREUR"):
            raise CaptureError(",".join(parts))
        if len(parts) == 10 and parts[0].isdigit():
            try:
                rows.append([float(v) for v in parts[1:7]])
            except ValueError:
                pass
    if len(rows) < 5:
        raise CaptureError("pas de données : le firmware examples/04_imu est-il téléversé ?")
    return np.array(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tinyml2027.imu_check", description=__doc__.splitlines()[0])
    ap.add_argument("--port")
    ap.add_argument("--log", type=Path)
    args = ap.parse_args(argv)
    out: list[str] = [f"# imu_check {datetime.now(timezone.utc).isoformat(timespec='seconds')}"]

    def say(s: str = ""):
        print(s)
        out.append(s)

    try:
        device, _ = pick_port(args.port)
        with open_port(device) as ser:
            ser.write(b"\n")
            time.sleep(0.5)
            head = [ser.readline().decode("utf-8", "replace").strip() for _ in range(6)]
            for h in head:
                if h.startswith("#") or h.startswith("ERREUR"):
                    say(h)
            seen = {}
            ok_all = True
            for i, pos in enumerate(POSITIONS, 1):
                input(f"\n[{i}/6] Mettez la carte {pos}.\n"
                      "      Quand elle est EN PLACE et immobile, appuyez sur Entrée avec l'autre main… ")
                print("      mesure en cours (2 s), ne bougez pas…")
                time.sleep(1.0)
                a = read_block(ser, 2.0)[:, :3]
                norm = np.linalg.norm(a, axis=1)
                mean = a.mean(axis=0)
                k = int(np.argmax(np.abs(mean)))
                label = ("+" if mean[k] > 0 else "-") + "XYZ"[k]
                others = np.delete(np.abs(mean), k).max()
                checks = {
                    "immobile": norm.std() < 0.05,   # tenue à la main : tolérance plus large que sur table
                    "norme≈1g": abs(norm.mean() - 1.0) < 0.1,
                    "un_seul_axe": abs(mean[k]) > 0.8 and others < 0.3,
                    "direction_nouvelle": label not in seen.values(),
                }
                seen[pos] = label
                ok = all(checks.values())
                ok_all &= ok
                say(f"position {i} ({pos}) : gravité sur {label}, a moyen = "
                    f"({mean[0]:+.3f}, {mean[1]:+.3f}, {mean[2]:+.3f}) g, |a| = {norm.mean():.3f} g "
                    f"± {norm.std():.3f} -> {'OK' if ok else 'ÉCHEC ' + str([c for c, v in checks.items() if not v])}")
            covered = sorted(seen.values()) == sorted(["+X", "-X", "+Y", "-Y", "+Z", "-Z"])
            say(f"\n6 directions couvertes (±X, ±Y, ±Z) : {'OUI' if covered else 'NON'}")
            ok_all &= covered

            input("\n[gyroscope] Prenez la carte en main. Après Entrée, faites-la TOURNER dans tous les sens "
                  "pendant 4 s (sans tirer sur le câble)… ")
            g = read_block(ser, 4.0)[:, 3:6]
            peak = np.abs(g).max(axis=0)
            gyro_ok = bool((peak > 30).all())
            ok_all &= gyro_ok
            say(f"gyroscope : pic |gx|, |gy|, |gz| = {peak[0]:.0f}, {peak[1]:.0f}, {peak[2]:.0f} °/s "
                f"-> {'OK' if gyro_ok else 'ÉCHEC (un axe ne dépasse pas 30 °/s)'}")
            say(f"\nRÉSULTAT IMU : {'OK' if ok_all else 'ÉCHEC'}")
    except (CaptureError, KeyboardInterrupt, EOFError) as e:
        say(f"ERREUR : {e}")
        ok_all = False
    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        args.log.write_text("\n".join(out) + "\n")
        print(f"journal : {args.log}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())


def snap(seconds: float = 3.0, port: str | None = None) -> dict:
    """Mesure non interactive : moyenne de l'accélération et pics du gyroscope sur `seconds`."""
    device, _ = pick_port(port)
    with open_port(device) as ser:
        d = read_block(ser, seconds)
    a, g = d[:, :3], d[:, 3:6]
    norm = np.linalg.norm(a, axis=1)
    k = int(np.argmax(np.abs(a.mean(axis=0))))
    return {"n": len(d), "a_mean": a.mean(axis=0).round(3).tolist(), "a_norm": round(float(norm.mean()), 3),
            "a_norm_std": round(float(norm.std()), 4),
            "gravity": ("+" if a.mean(axis=0)[k] > 0 else "-") + "XYZ"[k],
            "gyro_peak_dps": np.abs(g).max(axis=0).round(0).tolist()}
