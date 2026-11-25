"""Calcule les métriques de promotion à partir des prédictions INT8 de Studio."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from sklearn.metrics import confusion_matrix, f1_score

LABELS = ["bruit", "go", "stop"]
PREDICTIONS = [*LABELS, "uncertain"]
SPLITS = ("evaluation-clean", "evaluation-shifted")


def score(manifest, response):
    if response.get("success") is not True:
        raise ValueError("Réponse Studio en échec")
    expected = {row["sample_id"]: row for row in manifest if row["split"] in SPLITS}
    returned = {row["sampleId"]: row["sample"]["filename"] for row in response["result"]}
    records = {}
    for prediction in response["predictions"]:
        name = returned[prediction["sampleId"]]
        source = expected[name]
        if name in records or source["label"] != prediction["label"]:
            raise ValueError(f"Prédiction en double ou étiquette incohérente pour {name}")
        if prediction["prediction"] not in PREDICTIONS:
            raise ValueError(f"Classe prédite inconnue pour {name}")
        records[name] = {"sample_id": name, "split": source["split"], "label": source["label"],
                         "prediction": prediction["prediction"]}
    if records.keys() != expected.keys() or response["totalCount"] != len(expected):
        raise ValueError("La réponse ne couvre pas tout le jeu de promotion")
    rows = sorted(records.values(), key=lambda row: row["sample_id"])
    metrics = {}
    for split in SPLITS:
        subset = [row for row in rows if row["split"] == split]
        truth = [row["label"] for row in subset]
        predicted = [row["prediction"] for row in subset]
        matrix = confusion_matrix(truth, predicted, labels=PREDICTIONS)[:len(LABELS)]
        noise, go, stop = matrix
        metrics[split] = {
            "n": len(subset),
            "accuracy": float(matrix.trace() / len(subset)),
            "macro_f1": f1_score(truth, predicted, labels=LABELS, average="macro", zero_division=0),
            "recall_go": float(go[1] / go.sum()),
            "recall_stop": float(stop[2] / stop.sum()),
            "false_trigger_rate": float(noise[1:3].sum() / noise.sum()),
            "uncertain": int(matrix[:, -1].sum()),
            "confusion": matrix.tolist(),
        }
    return rows, {"labels": LABELS, "predictions": PREDICTIONS, "splits": metrics}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    with args.manifest.open(encoding="utf-8", newline="") as stream:
        rows, metrics = score(list(csv.DictReader(stream)), json.loads(args.results.read_text(encoding="utf-8")))
    with args.manifest.open("rb") as stream:
        metrics["manifest_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "predictions.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("sample_id", "split", "label", "prediction"), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (args.out / "promotion-metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8", newline="\n",
    )


if __name__ == "__main__":
    main()
