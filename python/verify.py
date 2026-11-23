"""Phases 5 et 7 — compare Keras, LiteRT desktop et la Nano sur les mêmes entrées.

Usage :
  uv run python python/verify.py --mode fp32 --port /dev/cu.usbmodemXXXX
  uv run python python/verify.py --mode int8 --port /dev/cu.usbmodemXXXX
  uv run python python/verify.py --mode fp32            # sans carte : Keras vs LiteRT seulement

Le firmware (examples/03_custom_model ou 05_int8_model) doit être téléversé.
Le script envoie un retour chariot, lit la série de tests complète jusqu'à la
ligne STATUT, puis refait toutes les comparaisons de son côté à partir des
valeurs brutes reçues (il ne se contente pas du statut annoncé par la carte).
Le journal brut est enregistré dans --log s'il est fourni.

Code de sortie : 0 si tout est dans la tolérance, 1 sinon, 2 si la carte ne répond pas.
"""

from __future__ import annotations

import argparse
import re
import struct
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from convert import TEST_X, TOL_FP32_ABS, TOL_INT8_LSB  # noqa: E402

from tinyml2027 import tflite_tools as tt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def read_board(port: str, timeout_s: float = 15.0) -> list[str]:
    import serial

    lines: list[str] = []
    with serial.Serial(port, 115200, timeout=0.5) as ser:
        time.sleep(0.5)
        ser.reset_input_buffer()
        ser.write(b"\n")
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout_s:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            lines.append(line)
            if line.startswith("STATUT") or line.startswith("ERREUR init"):
                break
    return lines


def parse(lines: list[str], mode: str) -> tuple[dict, np.ndarray, dict]:
    header = {}
    rows = []
    summary = {}
    for line in lines:
        if line.startswith("#"):
            header.update(dict(re.findall(r"(\w+)=(\S+)", line)))
        elif line.startswith("RESUME"):
            summary = dict(re.findall(r"(\w+)=(\S+)", line))
        elif re.match(r"^\d+,", line):
            rows.append(line.split(","))
    if mode == "fp32":
        # i,x,y,y_hex,y_attendu,ecart_abs,us,statut -> y exact via ses bits IEEE-754
        y = np.array([struct.unpack("<f", struct.pack("<I", int(r[3], 16)))[0] for r in rows], np.float32)
        us = np.array([int(r[6]) for r in rows])
    else:
        # i,x,x_q,y_q,y,attendu_q,ecart_lsb,us,statut
        y = np.array([int(r[3]) for r in rows], np.int32)
        us = np.array([int(r[7]) for r in rows])
    return header, y, {"us": us, **summary}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=("fp32", "int8"), required=True)
    ap.add_argument("--port")
    ap.add_argument("--artifacts", default=ROOT / "artifacts/sine", type=Path)
    ap.add_argument("--log", type=Path, help="fichier où enregistrer la sortie brute de la carte")
    args = ap.parse_args()

    import keras

    flat = (args.artifacts / f"model_{args.mode}.tflite").read_bytes()
    report = tt.inspect(flat)
    keras_y = keras.models.load_model(args.artifacts / "model.keras").predict(TEST_X[:, None], verbose=0)[:, 0]
    lite = tt.run(flat, TEST_X[:, None])
    lite_y = lite["y"][:, 0]

    print(f"modèle {args.mode} : {report.size_bytes} octets, sha256 {report.sha256}")
    print(f"Keras vs LiteRT ({args.mode}) : écart max {np.abs(keras_y - lite_y).max():.3g} "
          f"(sur [0, 2π] : {np.abs(keras_y - lite_y)[:21].max():.3g})")
    if args.mode == "int8":
        s, z = report.outputs[0].scale, report.outputs[0].zero_point
        print(f"  1 LSB de sortie = {s:.4g} ; erreur de quantification attendue ≤ ~{s / 2:.3g} + erreur d'entrée")

    if not args.port:
        print("Pas de --port : comparaison avec la carte non effectuée.")
        return 0

    lines = read_board(args.port)
    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        args.log.write_text("\n".join(lines) + "\n")
    if not any(l.startswith("STATUT") for l in lines):
        print("ERREUR : la carte n'a pas renvoyé de série de tests complète.", *lines[-5:], sep="\n  ")
        return 2

    header, board, info = parse(lines, args.mode)
    if header.get("model_sha256") != report.sha256:
        print(f"ERREUR : la carte exécute un autre modèle ({header.get('model_sha256')}).")
        return 1
    if len(board) != len(TEST_X):
        print(f"ERREUR : {len(board)} lignes reçues, {len(TEST_X)} attendues.")
        return 1

    if args.mode == "fp32":
        err = np.abs(board - lite_y)
        ok = err <= TOL_FP32_ABS
        print(f"Nano vs LiteRT : écart max {err.max():.3g} (tolérance {TOL_FP32_ABS:g}), "
              f"{int((board == lite_y).sum())}/{len(board)} sorties identiques au bit près")
        print(f"Nano vs Keras  : écart max {np.abs(board - keras_y).max():.3g}")
    else:
        err = np.abs(board - lite["q"][:, 0].astype(np.int32))
        ok = err <= TOL_INT8_LSB
        s, z = report.outputs[0].scale, report.outputs[0].zero_point
        board_y = (board - z) * s
        print(f"Nano vs LiteRT : écart max {err.max()} LSB (tolérance {TOL_INT8_LSB}), "
              f"{int((err == 0).sum())}/{len(board)} codes identiques")
        print(f"Nano INT8 vs Keras FP32 sur [0, 2π] : écart max {np.abs(board_y - keras_y)[:21].max():.4f}")
        print(f"  hors domaine x=-0,5 : {board_y[21]:+.4f} (Keras {keras_y[21]:+.4f}) ; "
              f"x=7,0 : {board_y[22]:+.4f} (Keras {keras_y[22]:+.4f}) <- saturation de l'entrée")
    us = info["us"]
    print(f"Invoke() sur la Nano : min {us.min()} µs, médiane {int(np.median(us))} µs, max {us.max()} µs")
    print(f"arena : {header.get('arena_used')} / {header.get('arena_size')} octets utilisés")
    print("RÉSULTAT :", "OK" if ok.all() else f"ÉCHEC ({int((~ok).sum())} écarts hors tolérance)")
    return 0 if ok.all() else 1


if __name__ == "__main__":
    sys.exit(main())
