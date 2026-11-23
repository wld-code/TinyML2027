"""TP02 — entraîner et évaluer le classifieur de mouvements, sans fuite entre sessions.

  uv run python -m tinyml2027.train_motion [--features results/tp01/features.csv]
                                           [--test-session s03] [--out artifacts/motion]

Démarche (docs/DATA_CONTRACT.md) :
1. Partition PAR SESSION : la session de test est mise de côté avant toute autre
   opération ; toutes les autres sessions forment l'entraînement.
2. Prétraitement appris sur l'entraînement uniquement : passage en log10 de rms_g et
   band_power_g2 (valeurs étalées sur plusieurs ordres de grandeur), puis
   standardisation (moyenne et écart-type du train).
3. Choix du modèle par validation croisée « une session laissée de côté » sur les
   sessions d'entraînement (avec 2 sessions : entraîner sur l'une, valider sur l'autre,
   puis l'inverse). Le test n'intervient pas.
4. Réentraînement sur toutes les sessions d'entraînement, puis UNE évaluation sur le test.
5. Export du contrat pour le TP03.
"""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd

from . import features as F

LABELS = ["stationary", "periodic", "impact"]
SEED = 2027
EPOCHS = 300
LOG_EPS = {"rms_g": 1e-6, "band_power_g2": 1e-12}


# ---------- prétraitement (doit être reproduit à l'identique en C++) ----------

def transform(df: pd.DataFrame) -> np.ndarray:
    """Les 4 entrées du réseau, avant standardisation, dans l'ordre du contrat."""
    return np.column_stack([
        np.log10(df["rms_g"].to_numpy() + LOG_EPS["rms_g"]),
        df["crest_factor"].to_numpy(),
        df["dominant_hz"].to_numpy(),
        np.log10(df["band_power_g2"].to_numpy() + LOG_EPS["band_power_g2"]),
    ]).astype(np.float64)


class Scaler:
    def __init__(self, mean=None, std=None):
        self.mean, self.std = mean, std

    def fit(self, X):
        self.mean, self.std = X.mean(axis=0), X.std(axis=0)
        self.std[self.std < 1e-12] = 1.0
        return self

    def __call__(self, X):
        return (X - self.mean) / self.std


# ---------- modèles ----------

HIDDEN = 8


def make_dense():
    import tensorflow as tf

    return tf.keras.Sequential([
        tf.keras.Input(shape=(4,), name="features"),
        tf.keras.layers.Dense(HIDDEN, activation="relu"),
        tf.keras.layers.Dense(3, activation="softmax", name="scores"),
    ])


def fit_predict(kind: str, Xtr, ytr, Xev):
    """Entraîne un modèle sur (Xtr, ytr) normalisés et renvoie (probas sur Xev, modèle)."""
    if kind == "dummy":
        from sklearn.dummy import DummyClassifier
        m = DummyClassifier(strategy="most_frequent").fit(Xtr, ytr)
        return m.predict_proba(Xev), m
    if kind == "logistic":
        from sklearn.linear_model import LogisticRegression
        m = LogisticRegression(max_iter=2000).fit(Xtr, ytr)
        return m.predict_proba(Xev), m
    import tensorflow as tf
    tf.keras.utils.set_random_seed(SEED)
    m = make_dense()
    m.compile(optimizer=tf.keras.optimizers.Adam(0.01), loss="sparse_categorical_crossentropy")
    m.fit(Xtr, ytr, epochs=EPOCHS, batch_size=16, verbose=0)
    return m.predict(Xev, verbose=0), m


def metrics(y, proba) -> dict:
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support

    pred = proba.argmax(axis=1)
    p, r, f, _ = precision_recall_fscore_support(y, pred, labels=range(3), zero_division=0)
    return {
        "accuracy": float(accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, labels=range(3), average="macro", zero_division=0)),
        "per_class": {LABELS[i]: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i])} for i in range(3)},
        "confusion": confusion_matrix(y, pred, labels=range(3)).tolist(),
        "n": int(len(y)),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--features", default="results/tp01/features.csv", type=Path)
    ap.add_argument("--test-session", default="s03")
    ap.add_argument("--out", default="artifacts/motion", type=Path)
    ap.add_argument("--hidden", type=int, default=8, help="neurones de la couche cachée (défaut 8)")
    args = ap.parse_args(argv)
    global HIDDEN
    HIDDEN = args.hidden

    table = pd.read_csv(args.features)
    table = table[table.valid].copy()
    table["y"] = table.condition.map({c: i for i, c in enumerate(LABELS)})
    if table.y.isna().any():
        raise SystemExit(f"condition inconnue dans {args.features}")
    test = table[table.session_id == args.test_session]
    train = table[table.session_id != args.test_session]
    if test.empty or train.session_id.nunique() < 2:
        raise SystemExit("il faut une session de test et au moins 2 sessions d'entraînement")
    for part, d in (("train", train), ("test", test)):
        missing = set(LABELS) - set(d.condition)
        if missing:
            raise SystemExit(f"{part} : aucune fenêtre pour {missing}")
    assert not set(train.session_id) & set(test.session_id), "fuite : session commune"
    train_sessions = sorted(train.session_id.unique())
    print(f"train : sessions {train_sessions}, {len(train)} fenêtres ; test : {args.test_session}, {len(test)} fenêtres")

    # 3. validation croisée par session, sur le train seulement
    cv = {}
    for kind in ("dummy", "logistic", "dense"):
        folds = []
        for held in train_sessions:
            tr, va = train[train.session_id != held], train[train.session_id == held]
            sc = Scaler().fit(transform(tr))            # normalisation apprise sur le pli d'entraînement
            proba, _ = fit_predict(kind, sc(transform(tr)), tr.y.to_numpy(), sc(transform(va)))
            m = metrics(va.y.to_numpy(), proba)
            folds.append({"validation_session": held, **{k: m[k] for k in ("accuracy", "macro_f1")}})
        cv[kind] = {"folds": folds, "macro_f1_mean": float(np.mean([f["macro_f1"] for f in folds]))}
        print(f"  CV {kind:8s} : macro-F1 par pli {[round(f['macro_f1'], 3) for f in folds]}, "
              f"moyenne {cv[kind]['macro_f1_mean']:.3f}")

    # 4. réentraînement sur tout le train, une seule évaluation sur le test
    scaler = Scaler().fit(transform(train))
    Xtr, ytr = scaler(transform(train)), train.y.to_numpy()
    Xte, yte = scaler(transform(test)), test.y.to_numpy()
    results, dense = {}, None
    for kind in ("dummy", "logistic", "dense"):
        proba, model = fit_predict(kind, Xtr, ytr, Xte)
        results[kind] = metrics(yte, proba)
        if kind == "dense":
            dense, dense_test_proba = model, proba
        print(f"  TEST {kind:8s} : accuracy {results[kind]['accuracy']:.3f}, macro-F1 {results[kind]['macro_f1']:.3f}")

    # 5. export
    import tensorflow as tf
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    dense.save(out / "model.keras")
    conv = tf.lite.TFLiteConverter.from_keras_model(dense)
    (out / "model_fp32.tflite").write_bytes(conv.convert())
    np.save(out / "calibration_train.npy", Xtr.astype(np.float32))
    (out / "labels.json").write_text(json.dumps(LABELS) + "\n")
    (out / "preprocessing.json").write_text(json.dumps({
        "contract": "docs/DATA_CONTRACT.md v0.2",
        "window": {"n": F.N, "hop": F.HOP, "axis": "ax_g", "band_hz": list(F.BAND_HZ)},
        "inputs": ["log10(rms_g + 1e-6)", "crest_factor", "dominant_hz", "log10(band_power_g2 + 1e-12)"],
        "log_eps": LOG_EPS,
        "standardize": {"mean": scaler.mean.tolist(), "std": scaler.std.tolist()},
        "fitted_on_sessions": train_sessions,
    }, indent=2) + "\n")
    (out / "training_config.json").write_text(json.dumps({
        "seed": SEED, "epochs": EPOCHS, "optimizer": "adam lr=0.01", "batch_size": 16,
        "architecture": f"4 -> Dense {HIDDEN} ReLU -> Dense 3 softmax", "params": int(dense.count_params()),
        "train_sessions": train_sessions, "test_session": args.test_session,
        "features_file": str(args.features),
        "versions": {"python": platform.python_version(), "tensorflow": tf.__version__, "numpy": np.__version__},
    }, indent=2) + "\n")
    (out / "metrics.json").write_text(json.dumps({"cv_train": cv, "test": results}, indent=2) + "\n")
    test_out = test[["recording_id", "session_id", "condition", "start", "end", *F.FEATURES]].copy()
    test_out["pred"] = [LABELS[i] for i in dense_test_proba.argmax(axis=1)]
    for i, lab in enumerate(LABELS):
        test_out[f"p_{lab}"] = dense_test_proba[:, i]
    test_out.to_csv(out / "test_predictions.csv", index=False, float_format="%.6g")
    print(f"matrice de confusion du réseau sur le test (lignes = vrai, colonnes = prédit, ordre {LABELS}) :")
    for lab, row in zip(LABELS, results["dense"]["confusion"]):
        print(f"  {lab:10s} {row}")
    print(f"artefacts : {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
