"""Essai E4 : la chaîne Python du cours fonctionne sur ce poste.

Vérifie (sans carte) que :
1. la version de Python est dans la plage supportée par TensorFlow ;
2. un réseau dense 4 -> 8 -> 3 s'entraîne avec Keras ;
3. le convertisseur TensorFlow produit un modèle **full INT8** (entrée, sortie et
   poids int8, biais int32) avec une calibration fournie explicitement ;
4. l'interpréteur desktop ai_edge_litert l'exécute, et ses scores dé-quantifiés
   restent proches des scores FP32 sur les mêmes entrées.

Les données sont synthétiques et ne servent qu'à tester la chaîne d'outils.
"""

import sys

import numpy as np
import pytest

tf = pytest.importorskip("tensorflow")
from ai_edge_litert.interpreter import Interpreter, OpResolverType  # noqa: E402

SEED = 2027


def test_python_version_supported_by_tensorflow():
    assert (3, 12) <= sys.version_info[:2] <= (3, 13)


def _tiny_dataset(n_per_class=200):
    rng = np.random.default_rng(SEED)
    centers = np.array([[0, 0, 0, 0], [3, 1, 0, -1], [-2, 2, 3, 1]], dtype=np.float32)
    x = np.concatenate([c + rng.normal(0, 0.6, (n_per_class, 4)) for c in centers]).astype(np.float32)
    y = np.repeat(np.arange(3), n_per_class)
    return x, y


@pytest.fixture(scope="module")
def trained_model():
    tf.keras.utils.set_random_seed(SEED)
    x, y = _tiny_dataset()
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(4,)),
        tf.keras.layers.Dense(8, activation="relu"),
        tf.keras.layers.Dense(3, activation="softmax"),
    ])
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(x, y, epochs=40, batch_size=32, verbose=0)
    return model, x, y


def _convert_int8(model, calibration):
    def representative_dataset():
        for row in calibration:
            yield [row[None, :]]

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    return converter.convert()


def test_keras_network_learns(trained_model):
    model, x, y = trained_model
    assert model.count_params() == 4 * 8 + 8 + 8 * 3 + 3  # 67 paramètres
    acc = (model.predict(x, verbose=0).argmax(axis=1) == y).mean()
    assert acc > 0.9  # données synthétiques bien séparées : test d'outillage, pas de performance


def test_full_int8_conversion_and_litert_parity(trained_model):
    model, x, _ = trained_model
    flat = _convert_int8(model, x[::5])

    interp = Interpreter(model_content=flat, experimental_op_resolver_type=OpResolverType.BUILTIN_REF)
    interp.allocate_tensors()
    inp, out = interp.get_input_details()[0], interp.get_output_details()[0]
    assert inp["dtype"] == np.int8 and out["dtype"] == np.int8

    for t in interp.get_tensor_details():
        assert t["dtype"] in (np.int8, np.int32), f"tenseur non entier : {t['name']} {t['dtype']}"

    s_in, z_in = inp["quantization"]
    s_out, z_out = out["quantization"]
    fp32 = model.predict(x, verbose=0)
    int8_scores = np.empty_like(fp32)
    for i, row in enumerate(x):
        q = np.clip(np.round(row / s_in + z_in), -128, 127).astype(np.int8)
        interp.set_tensor(inp["index"], q[None, :])
        interp.invoke()
        int8_scores[i] = (interp.get_tensor(out["index"])[0].astype(np.float32) - z_out) * s_out

    agreement = (fp32.argmax(axis=1) == int8_scores.argmax(axis=1)).mean()
    assert agreement > 0.97
    assert np.abs(fp32 - int8_scores).max() < 0.1
