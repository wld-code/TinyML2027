"""Phase 4 — entraîne un petit réseau de régression qui approxime y = sin(x).

Usage :  uv run python python/train.py [--out artifacts/sine]

Sorties (dans --out, ignoré par git) :
  model.keras     modèle Keras FP32
  data.npz        x/y de train, validation et test (seed fixe)
  train_log.json  seed, versions, architecture, pertes finales

Le jeu de données est synthétique : x tiré uniformément dans [0, 2π], y = sin(x)
plus un bruit gaussien d'écart-type 0,1. Le test sert uniquement à la mesure
finale ; la calibration INT8 (python/convert.py) utilise exclusivement le train.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform

# Masque les journaux C++ de TensorFlow (inoffensifs mais très verbeux). TINYML_VERBOSE=1 pour les voir.
if not os.environ.get("TINYML_VERBOSE"):
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import sys

# Windows (Git Bash) : sortie en UTF-8, sinon les accents s'affichent mal.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")
from pathlib import Path

import numpy as np

SEED = 2027
N_SAMPLES = 1000
NOISE_STD = 0.1
EPOCHS = 500


def make_dataset(seed: int = SEED):
    rng = np.random.default_rng(seed)
    x = rng.uniform(0.0, 2 * math.pi, N_SAMPLES).astype(np.float32)
    y = (np.sin(x) + rng.normal(0.0, NOISE_STD, N_SAMPLES)).astype(np.float32)
    n_train, n_val = int(0.6 * N_SAMPLES), int(0.2 * N_SAMPLES)
    return {
        "x_train": x[:n_train], "y_train": y[:n_train],
        "x_val": x[n_train:n_train + n_val], "y_val": y[n_train:n_train + n_val],
        "x_test": x[n_train + n_val:], "y_test": y[n_train + n_val:],
    }


def build_model():
    import tensorflow as tf

    return tf.keras.Sequential([
        tf.keras.Input(shape=(1,), name="x"),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(1, name="y"),
    ])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="artifacts/sine", type=Path)
    args = ap.parse_args()

    import keras
    import tensorflow as tf

    tf.keras.utils.set_random_seed(SEED)
    tf.config.experimental.enable_op_determinism()
    data = make_dataset()
    model = build_model()
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    hist = model.fit(
        data["x_train"], data["y_train"], epochs=EPOCHS, batch_size=64, verbose=0,
        validation_data=(data["x_val"], data["y_val"]),
    )

    args.out.mkdir(parents=True, exist_ok=True)
    model.save(args.out / "model.keras")
    np.savez(args.out / "data.npz", **data)

    test_mse = float(model.evaluate(data["x_test"], data["y_test"], verbose=0)[0])
    log = {
        "seed": SEED, "n_samples": N_SAMPLES, "noise_std": NOISE_STD, "epochs": EPOCHS,
        "architecture": "1 -> Dense16 ReLU -> Dense16 ReLU -> 1",
        "params": int(model.count_params()),
        "train_mse": float(hist.history["loss"][-1]),
        "val_mse": float(hist.history["val_loss"][-1]),
        "test_mse": test_mse,
        "noise_floor_mse": NOISE_STD ** 2,
        "versions": {"python": platform.python_version(), "tensorflow": tf.__version__,
                     "keras": keras.__version__, "numpy": np.__version__},
    }
    (args.out / "train_log.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: log[k] for k in ("params", "train_mse", "val_mse", "test_mse", "noise_floor_mse")}, indent=2))
    print(f"modèle écrit dans {args.out / 'model.keras'}")


if __name__ == "__main__":
    main()
