"""Outils communs pour inspecter, exécuter et exporter un modèle .tflite.

Utilisés par python/convert.py, python/verify.py et les TP. Le moteur desktop
est ai_edge_litert avec les noyaux de référence (BUILTIN_REF), plus proches de
TensorFlow Lite Micro que les noyaux optimisés XNNPACK. Il n'est pas pour autant
bit-exact avec TFLM : voir docs/AUDIT.md §11.4.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

# Version du schéma FlatBuffer attendue par Arduino_TensorFlowLite @7948b85e
# (TFLITE_SCHEMA_VERSION dans tensorflow/lite/schema/schema_generated.h).
TFLM_SCHEMA_VERSION = 3

# Opérateurs pour lesquels le firmware enregistre explicitement un noyau.
# Toute autre valeur provoque un refus à la conversion plutôt qu'un échec sur la carte.
SUPPORTED_OPS = {"FULLY_CONNECTED", "SOFTMAX", "RELU", "RESHAPE", "QUANTIZE", "DEQUANTIZE"}


@dataclass
class TensorInfo:
    name: str
    dtype: str
    shape: tuple
    scale: float
    zero_point: int


@dataclass
class ModelReport:
    size_bytes: int
    sha256: str
    schema_version: int
    file_identifier: str
    ops: list[str]
    inputs: list[TensorInfo]
    outputs: list[TensorInfo]
    tensor_dtypes: dict[str, str]
    per_channel_tensors: list[str]


def _interpreter(model_bytes: bytes):
    from ai_edge_litert.interpreter import Interpreter, OpResolverType

    it = Interpreter(model_content=model_bytes, experimental_op_resolver_type=OpResolverType.BUILTIN_REF)
    it.allocate_tensors()
    return it


def schema_version(model_bytes: bytes) -> int:
    """Lit le champ `version` du FlatBuffer (table Model, premier champ)."""
    from tensorflow.lite.python import schema_py_generated as schema

    return int(schema.Model.GetRootAsModel(model_bytes, 0).Version())


def _info(d) -> TensorInfo:
    scale, zp = d["quantization"]
    return TensorInfo(d["name"], np.dtype(d["dtype"]).name, tuple(int(v) for v in d["shape"]), float(scale), int(zp))


def inspect(model_bytes: bytes) -> ModelReport:
    it = _interpreter(model_bytes)
    return ModelReport(
        size_bytes=len(model_bytes),
        sha256=hashlib.sha256(model_bytes).hexdigest(),
        schema_version=schema_version(model_bytes),
        file_identifier=model_bytes[4:8].decode("ascii", "replace"),
        ops=[o["op_name"] for o in it._get_ops_details()],
        inputs=[_info(d) for d in it.get_input_details()],
        outputs=[_info(d) for d in it.get_output_details()],
        tensor_dtypes={t["name"]: np.dtype(t["dtype"]).name for t in it.get_tensor_details()},
        per_channel_tensors=[t["name"] for t in it.get_tensor_details()
                             if len(t["quantization_parameters"]["scales"]) > 1],
    )


def check_tflm_compatible(report: ModelReport, allowed_ops: set[str] = SUPPORTED_OPS) -> None:
    """Lève ValueError si le modèle ne peut pas tourner avec le firmware du cours."""
    if report.file_identifier != "TFL3":
        raise ValueError(f"identifiant de fichier inattendu : {report.file_identifier!r}")
    if report.schema_version != TFLM_SCHEMA_VERSION:
        raise ValueError(f"schéma {report.schema_version}, TFLM attend {TFLM_SCHEMA_VERSION}")
    unknown = sorted(set(report.ops) - allowed_ops)
    if unknown:
        raise ValueError(f"opérateurs non enregistrés dans le firmware : {unknown}")


def quantize(x: np.ndarray, scale: float, zero_point: int) -> np.ndarray:
    """float -> int8, arrondi au plus proche et saturation explicite à [-128, 127]."""
    return np.clip(np.round(np.asarray(x, np.float64) / scale + zero_point), -128, 127).astype(np.int8)


def dequantize(q: np.ndarray, scale: float, zero_point: int) -> np.ndarray:
    return (np.asarray(q, np.float32) - zero_point) * np.float32(scale)


def run(model_bytes: bytes, x: np.ndarray) -> dict:
    """Exécute le modèle échantillon par échantillon (batch 1, comme sur la carte).

    `x` est en unités physiques (float). Pour un modèle INT8, l'entrée est quantifiée
    avec les paramètres du tenseur d'entrée, et la sortie est rendue à la fois en
    codes int8 (`q`) et dé-quantifiée (`y`).
    """
    it = _interpreter(model_bytes)
    inp, out = it.get_input_details()[0], it.get_output_details()[0]
    x = np.asarray(x, np.float32).reshape((-1, *inp["shape"][1:]))
    s_in, z_in = inp["quantization"]
    s_out, z_out = out["quantization"]
    ys, qs = [], []
    for row in x:
        if inp["dtype"] == np.int8:
            it.set_tensor(inp["index"], quantize(row, s_in, z_in)[None])
        else:
            it.set_tensor(inp["index"], row[None].astype(np.float32))
        it.invoke()
        o = it.get_tensor(out["index"])[0]
        if out["dtype"] == np.int8:
            qs.append(o.copy())
            ys.append(dequantize(o, s_out, z_out))
        else:
            ys.append(o.astype(np.float32))
    res = {"y": np.array(ys)}
    if qs:
        res["q"] = np.array(qs)
    return res


def c_array(model_bytes: bytes, symbol: str, source: str) -> str:
    """Génère un en-tête C++ autonome contenant le modèle (aligné sur 16 octets)."""
    digest = hashlib.sha256(model_bytes).hexdigest()
    lines = [
        "// Fichier généré automatiquement : ne pas modifier à la main.",
        f"// Source : {source}",
        f"// Taille : {len(model_bytes)} octets",
        f"// SHA-256 : {digest}",
        "#pragma once",
        "#include <stdint.h>",
        "",
        f'constexpr char {symbol}_sha256[] = "{digest}";',
        f"constexpr unsigned int {symbol}_len = {len(model_bytes)};",
        f"alignas(16) const unsigned char {symbol}[] = {{",
    ]
    for i in range(0, len(model_bytes), 12):
        chunk = model_bytes[i : i + 12]
        lines.append("  " + ", ".join(f"0x{b:02x}" for b in chunk) + ",")
    lines += ["};", ""]
    return "\n".join(lines)


def check_int8(report: ModelReport) -> None:
    """Lève ValueError si le modèle n'est pas INT8 complet et par tenseur (exigence de la bibliothèque Arduino)."""
    bad = {n: d for n, d in report.tensor_dtypes.items() if d not in ("int8", "int32")}
    if bad:
        raise ValueError(f"tenseurs non entiers dans le modèle INT8 : {bad}")
    for t in report.inputs + report.outputs:
        if t.dtype != "int8" or t.scale <= 0:
            raise ValueError(f"entrée/sortie non int8 ou échelle invalide : {t}")
    if report.per_channel_tensors:
        raise ValueError("quantification par canal non supportée par la bibliothèque Arduino : "
                         f"{report.per_channel_tensors}")


def convert_int8(keras_model, calibration: np.ndarray) -> bytes:
    """Conversion INT8 complète, calibrée sur `calibration` (données d'ENTRAÎNEMENT uniquement),
    quantification par tenseur pour les couches denses."""
    import tensorflow as tf

    def representative_dataset():
        for row in calibration:
            yield [np.asarray(row, np.float32)[None, ...]]

    conv = tf.lite.TFLiteConverter.from_keras_model(keras_model)
    conv.optimizations = [tf.lite.Optimize.DEFAULT]
    conv.representative_dataset = representative_dataset
    conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    conv.inference_input_type = tf.int8
    conv.inference_output_type = tf.int8
    conv._experimental_disable_per_channel_quantization_for_dense_layers = True
    return conv.convert()
