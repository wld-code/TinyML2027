"""Phases 4 et 7 — convertit le modèle sinus en .tflite et en tableau C++.

Usage :
  uv run python python/convert.py --mode fp32   # -> examples/03_custom_model/model_data.h
  uv run python python/convert.py --mode int8   # -> examples/05_int8_model/model_data.h

Contrôles bloquants (le script s'arrête en erreur sinon) :
  - identifiant de fichier TFL3 et schéma 3, attendu par Arduino_TensorFlowLite @7948b85e ;
  - uniquement des opérateurs enregistrés dans le firmware ;
  - en INT8 : entrée, sortie et activations int8, biais int32, aucun tenseur float.

INT8 : la calibration utilise exclusivement x_train. La quantification par canal
des couches denses est désactivée, car le noyau FULLY_CONNECTED de la
bibliothèque Arduino de 2023 ne la prend pas en charge (une seule échelle par tenseur
de poids). Voir docs/AUDIT.md §12.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from tinyml2027 import tflite_tools as tt

ROOT = Path(__file__).resolve().parents[1]
HEADER = {"fp32": ROOT / "examples/03_custom_model/model_data.h",
          "int8": ROOT / "examples/05_int8_model/model_data.h"}

# Entrées de test, identiques pour FP32 et INT8 : 21 points réguliers sur [0, 2π]
# et deux points hors du domaine d'entraînement (-0,5 et 7,0) pour observer
# l'extrapolation et la saturation de la quantification d'entrée.
TEST_X = np.concatenate([np.linspace(0.0, 2 * np.pi, 21), [-0.5, 7.0]]).astype(np.float32)

# Tolérances a priori, vérifiées par python/verify.py sur la carte :
#  - FP32 : mêmes noyaux de référence et mêmes données float32 ; seules l'ordre
#    des additions et la contraction FMA peuvent différer -> 1e-5 en absolu ;
#  - INT8 : quantification par tenseur, arithmétique entière identique en théorie
#    -> au plus 1 LSB sur le code de sortie.
TOL_FP32_ABS = 1e-5
TOL_INT8_LSB = 1


def _cf(v: float) -> str:
    """Littéral float C++ relisible à l'identique (9 chiffres significatifs)."""
    t = f"{float(v):.9g}"
    if not any(c in t for c in ".en"):
        t += ".0"
    return t + "f"


def test_vectors_header(mode: str, flat: bytes, model, report) -> str:
    keras_y = model.predict(TEST_X[:, None], verbose=0)[:, 0]
    ref = tt.run(flat, TEST_X[:, None])
    lines = [
        "// Fichier généré par python/convert.py : ne pas modifier à la main.",
        "// Valeurs attendues = interpréteur LiteRT desktop (noyaux de référence).",
        "#pragma once",
        f"constexpr int kNumTests = {len(TEST_X)};",
        "const float kTestX[kNumTests] = {" + ", ".join(_cf(v) for v in TEST_X) + "};",
        "const float kKerasY[kNumTests] = {" + ", ".join(_cf(v) for v in keras_y) + "};",
    ]
    if mode == "int8":
        lines += [
            f"constexpr int kTolLsb = {TOL_INT8_LSB};",
            "const signed char kExpectedQ[kNumTests] = {" + ", ".join(str(int(v)) for v in ref["q"][:, 0]) + "};",
        ]
    else:
        lines += [
            f"constexpr float kTolAbs = {_cf(TOL_FP32_ABS)};",
            "const float kExpectedY[kNumTests] = {" + ", ".join(_cf(v) for v in ref["y"][:, 0]) + "};",
        ]
    return "\n".join(lines) + "\n"


def convert(model, mode: str, x_calib: np.ndarray | None = None) -> bytes:
    import tensorflow as tf

    conv = tf.lite.TFLiteConverter.from_keras_model(model)
    if mode == "int8":
        def representative_dataset():
            for v in x_calib:
                yield [np.array([[v]], dtype=np.float32)]

        conv.optimizations = [tf.lite.Optimize.DEFAULT]
        conv.representative_dataset = representative_dataset
        conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        conv.inference_input_type = tf.int8
        conv.inference_output_type = tf.int8
        conv._experimental_disable_per_channel_quantization_for_dense_layers = True
    with tt.quiet():
        return conv.convert()


def check_int8(report: tt.ModelReport) -> None:
    bad = {n: d for n, d in report.tensor_dtypes.items() if d not in ("int8", "int32")}
    if bad:
        raise ValueError(f"tenseurs non entiers dans le modèle INT8 : {bad}")
    for t in report.inputs + report.outputs:
        if t.dtype != "int8" or t.scale <= 0:
            raise ValueError(f"entrée/sortie non int8 ou échelle invalide : {t}")
    if report.per_channel_tensors:
        raise ValueError(f"quantification par canal non supportée par la bibliothèque Arduino : "
                         f"{report.per_channel_tensors}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=("fp32", "int8"), required=True)
    ap.add_argument("--artifacts", default=ROOT / "artifacts/sine", type=Path)
    args = ap.parse_args()

    import keras

    model = keras.models.load_model(args.artifacts / "model.keras")
    data = np.load(args.artifacts / "data.npz")
    flat = convert(model, args.mode, data["x_train"])

    report = tt.inspect(flat)
    tt.check_tflm_compatible(report)
    if args.mode == "int8":
        check_int8(report)

    out = args.artifacts / f"model_{args.mode}.tflite"
    out.write_bytes(flat)
    (args.artifacts / f"model_{args.mode}.report.json").write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8", newline="\n")
    HEADER[args.mode].write_text(tt.c_array(flat, "g_model", f"artifacts/sine/{out.name} (python/convert.py --mode {args.mode})"), encoding="utf-8", newline="\n")
    (HEADER[args.mode].parent / "test_vectors.h").write_text(test_vectors_header(args.mode, flat, model, report), encoding="utf-8", newline="\n")

    print(f"{out.relative_to(ROOT)} : {report.size_bytes} octets, sha256 {report.sha256[:16]}…")
    print(f"schéma {report.schema_version}, opérateurs {report.ops}")
    for t in report.inputs:
        print(f"entrée  {t.dtype} {t.shape} scale={t.scale:.9g} zero_point={t.zero_point}")
    for t in report.outputs:
        print(f"sortie  {t.dtype} {t.shape} scale={t.scale:.9g} zero_point={t.zero_point}")
    print(f"en-tête C++ : {HEADER[args.mode].relative_to(ROOT)}")


if __name__ == "__main__":
    main()
