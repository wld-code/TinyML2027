"""TP03 — quantification INT8, comparaison FP32/INT8, golden vectors et en-têtes du firmware.

  uv run python -m tinyml2027.quantize_motion [--artifacts artifacts/motion] [--data data]

Entrées : artefacts du TP02 (model.keras, calibration_train.npy, preprocessing.json,
labels.json, training_config.json) et les enregistrements bruts (pour les golden vectors).

Sorties :
  artifacts/motion/model_int8.tflite, comparison.json, golden_vectors.npz, release_manifest.json
  labs/03-embedded-inference/firmware/infer_nano/{model_data.h, model_params.h, golden.h}

Golden vectors = fenêtres BRUTES (ax_g, t_us) de la session de test, plus deux cas
limites synthétiques (fenêtre constante, sinusoïde pure). Pour chacune : features
Python (float64), entrées standardisées, codes int8 d'entrée, codes int8 de sortie
et scores attendus selon LiteRT desktop. Le firmware les rejoue AVANT le mode live.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from . import dataset, features as F, recording, tflite_tools as tt
from .train_motion import LABELS, Scaler, transform

ROOT = Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "labs/03-embedded-inference/firmware/infer_nano"

# Tolérances de parité Python (float64) / Nano (float32), déclarées AVANT la mesure sur carte.
TOL = {"rel_feature": 1e-4, "dominant_bins": 1, "input_lsb": 1, "output_lsb": 2}


def _cf(v: float) -> str:
    t = f"{float(v):.9g}"
    if not any(c in t for c in ".en"):
        t += ".0"
    return t + "f"


def golden_windows(data_root: Path, test_session: str, per_class: int = 2) -> list[dict]:
    rows = [r for r in dataset.read_manifest(data_root) if r["session_id"] == test_session and r["valid"] == "1"]
    out = []
    for r in sorted(rows, key=lambda r: LABELS.index(r["condition"])):
        df = recording.read_csv(dataset.recording_path(data_root, r["session_id"], r["recording_id"], True))
        valid = [(s, e) for s, e, ok, _ in F.windows(df) if ok]
        picks = [valid[0], valid[len(valid) // 2]][:per_class]
        for s, e in picks:
            w = df.iloc[s:e]
            out.append({"name": f"{r['recording_id']}@{s}", "label": r["condition"],
                        "ax": w.ax_g.to_numpy(np.float64), "t_us": (w.t_us - w.t_us.iloc[0]).to_numpy(np.int64)})
    t = (np.arange(F.N) * 8600).astype(np.int64)
    out.append({"name": "synthetique_constante", "label": "stationary", "ax": np.full(F.N, 0.01), "t_us": t})
    fs = (F.N - 1) / (t[-1] * 1e-6)
    out.append({"name": "synthetique_sinus_2hz", "label": "periodic",
                "ax": 0.1 * np.sin(2 * np.pi * 2.0 * np.arange(F.N) / fs), "t_us": t})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--artifacts", default=ROOT / "artifacts/motion", type=Path)
    ap.add_argument("--data", default=ROOT / "data", type=Path)
    ap.add_argument("--model-version", default="motion-v1", help="nom de version annoncé par la carte")
    args = ap.parse_args(argv)
    A = args.artifacts

    import keras
    model = keras.models.load_model(A / "model.keras")
    prep = json.loads((A / "preprocessing.json").read_text())
    cfg = json.loads((A / "training_config.json").read_text())
    scaler = Scaler(np.array(prep["standardize"]["mean"]), np.array(prep["standardize"]["std"]))
    calib = np.load(A / "calibration_train.npy")

    flat8 = tt.convert_int8(model, calib)
    rep8 = tt.inspect(flat8)
    tt.check_tflm_compatible(rep8)
    tt.check_int8(rep8)
    (A / "model_int8.tflite").write_bytes(flat8)
    flat32 = (A / "model_fp32.tflite").read_bytes()
    print(f"FP32 {len(flat32)} octets, INT8 {len(flat8)} octets ; opérateurs {rep8.ops}")
    qi, qo = rep8.inputs[0], rep8.outputs[0]
    print(f"entrée int8 scale={qi.scale:.6g} zp={qi.zero_point} ; sortie int8 scale={qo.scale:.6g} zp={qo.zero_point}")

    # Comparaison FP32 / INT8 sur les MÊMES fenêtres de test
    feats = pd.read_csv(ROOT / cfg["features_file"]) if not Path(cfg["features_file"]).is_absolute() \
        else pd.read_csv(cfg["features_file"])
    feats = feats[feats.valid & (feats.session_id == cfg["test_session"])]
    X = scaler(transform(feats)).astype(np.float32)
    y = feats.condition.map(LABELS.index).to_numpy()
    p32 = tt.run(flat32, X)["y"]
    r8 = tt.run(flat8, X)
    p8 = r8["y"]
    comp = {
        "n_windows": int(len(X)), "test_session": cfg["test_session"],
        "size_bytes": {"fp32": len(flat32), "int8": len(flat8)},
        "accuracy": {"fp32": float((p32.argmax(1) == y).mean()), "int8": float((p8.argmax(1) == y).mean())},
        "agreement_fp32_int8": float((p32.argmax(1) == p8.argmax(1)).mean()),
        "max_abs_score_diff": float(np.abs(p32 - p8).max()),
        "disagreements": [
            {"window": f"{r.recording_id}@{r.start}", "fp32": p32[i].round(4).tolist(), "int8": p8[i].round(4).tolist()}
            for i, r in enumerate(feats.itertuples()) if p32[i].argmax() != p8[i].argmax()],
        "input_saturation": int(((tt.quantize(X, qi.scale, qi.zero_point) == 127) |
                                 (tt.quantize(X, qi.scale, qi.zero_point) == -128)).sum()),
    }
    (A / "comparison.json").write_text(json.dumps(comp, indent=2) + "\n")
    print(f"test {cfg['test_session']} : accuracy FP32 {comp['accuracy']['fp32']:.3f}, INT8 {comp['accuracy']['int8']:.3f}, "
          f"accord {comp['agreement_fp32_int8']:.3f}, écart max de score {comp['max_abs_score_diff']:.4f}, "
          f"entrées saturées {comp['input_saturation']}")

    # Golden vectors
    gold = golden_windows(args.data, cfg["test_session"])
    G = {k: [] for k in ("feat", "x", "xq", "yq", "scores")}
    for g in gold:
        fs = F.fs_window(g["t_us"])
        ft = F.compute(g["ax"], fs)
        df1 = pd.DataFrame([dict(zip(F.FEATURES, ft.vector()))])
        x = scaler(transform(df1))[0].astype(np.float32)
        r = tt.run(flat8, x[None])
        G["feat"].append(ft.vector())
        G["x"].append(x)
        G["xq"].append(tt.quantize(x, qi.scale, qi.zero_point))
        G["yq"].append(r["q"][0])
        G["scores"].append(r["y"][0])
    np.savez(A / "golden_vectors.npz", names=[g["name"] for g in gold], labels=[g["label"] for g in gold],
             ax=np.array([g["ax"] for g in gold]), t_us=np.array([g["t_us"] for g in gold]),
             **{k: np.array(v) for k, v in G.items()})

    # En-têtes du firmware
    FIRMWARE.mkdir(parents=True, exist_ok=True)
    (FIRMWARE / "model_data.h").write_text(tt.c_array(flat8, "g_model", "artifacts/motion/model_int8.tflite "
                                                                        "(python -m tinyml2027.quantize_motion)"))
    mean, std = prep["standardize"]["mean"], prep["standardize"]["std"]
    (FIRMWARE / "model_params.h").write_text("\n".join([
        "// Généré par python -m tinyml2027.quantize_motion : ne pas modifier à la main.",
        "// Prétraitement appris sur les sessions " + ", ".join(prep["fitted_on_sessions"]) + " (artifacts/motion/preprocessing.json).",
        "#pragma once",
        f'constexpr char kModelVersion[] = "{args.model_version}";',
        'constexpr char kFeatureSchema[] = "' + ";".join(prep["inputs"]) + '";',
        "constexpr int kNumClasses = 3;",
        'const char* const kLabels[kNumClasses] = {' + ", ".join(f'"{l}"' for l in LABELS) + "};",
        f"constexpr float kLogEpsRms = {_cf(prep['log_eps']['rms_g'])};",
        f"constexpr float kLogEpsBand = {_cf(prep['log_eps']['band_power_g2'])};",
        "const float kMean[4] = {" + ", ".join(_cf(v) for v in mean) + "};",
        "const float kStd[4] = {" + ", ".join(_cf(v) for v in std) + "};",
        "",
    ]))
    lines = [
        "// Généré par python -m tinyml2027.quantize_motion : ne pas modifier à la main.",
        "// Golden vectors : fenêtres brutes de la session de test et cas synthétiques,",
        "// avec les valeurs attendues calculées en Python (float64) et par LiteRT desktop.",
        "#pragma once",
        f"constexpr int kNumGolden = {len(gold)};",
        f"constexpr float kTolRelFeature = {_cf(TOL['rel_feature'])};",
        f"constexpr int kTolDominantBins = {TOL['dominant_bins']};",
        f"constexpr int kTolInputLsb = {TOL['input_lsb']};",
        f"constexpr int kTolOutputLsb = {TOL['output_lsb']};",
        "const char* const kGoldenName[kNumGolden] = {" + ", ".join(f'"{g["name"]}"' for g in gold) + "};",
        "const int kGoldenLabel[kNumGolden] = {" + ", ".join(str(LABELS.index(g["label"])) for g in gold) + "};",
        "const float kGoldenAx[kNumGolden][256] = {",
        *["  {" + ", ".join(_cf(v) for v in g["ax"]) + "}," for g in gold], "};",
        "const unsigned long kGoldenT[kNumGolden][256] = {",
        *["  {" + ", ".join(str(int(v)) for v in g["t_us"]) + "}," for g in gold], "};",
        "const float kGoldenFeat[kNumGolden][4] = {",
        *["  {" + ", ".join(_cf(v) for v in f) + "}," for f in G["feat"]], "};",
        "const signed char kGoldenXq[kNumGolden][4] = {",
        *["  {" + ", ".join(str(int(v)) for v in q) + "}," for q in G["xq"]], "};",
        "const signed char kGoldenYq[kNumGolden][3] = {",
        *["  {" + ", ".join(str(int(v)) for v in q) + "}," for q in G["yq"]], "};",
        "",
    ]
    (FIRMWARE / "golden.h").write_text("\n".join(lines))

    sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
    (A / "release_manifest.json").write_text(json.dumps({
        "model_version": args.model_version,
        "model_int8_sha256": sha(flat8), "model_fp32_sha256": sha(flat32),
        "labels": LABELS, "feature_schema": prep["inputs"], "contract": prep["contract"],
        "train_sessions": cfg["train_sessions"], "test_session": cfg["test_session"],
        "runtime": "Arduino_TensorFlowLite @7948b85e (per-tensor INT8)",
        "board": "arduino:mbed_nano:nano33ble@4.6.0", "board_revision": "original (LSM9DS1)",
        "tolerances": TOL, "int8_input": asdict(qi), "int8_output": asdict(qo),
        "acceptance_status": "non testé sur carte",
    }, indent=2) + "\n")
    print(f"{len(gold)} golden vectors ; en-têtes écrits dans {FIRMWARE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
