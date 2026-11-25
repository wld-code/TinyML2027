import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "advanced/edge-impulse-mlops/scripts/score_studio.py"
spec = importlib.util.spec_from_file_location("kws_score", SCRIPT)
studio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studio)


def test_studio_predictions_are_joined_by_id_and_condition():
    manifest, results, predictions = [], [], []
    for split in studio.SPLITS:
        for label in studio.LABELS:
            sample_id = len(manifest)
            name = f"{label}.{split}"
            manifest.append({"sample_id": name, "split": split, "label": label})
            results.append({"sampleId": sample_id, "sample": {"filename": name}})
            prediction = "uncertain" if label == "go" else label
            predictions.append({"sampleId": sample_id, "label": label, "prediction": prediction})
    response = {"success": True, "result": results, "predictions": predictions[::-1], "totalCount": 6}
    rows, metrics = studio.score(manifest, response)
    assert len(rows) == 6
    for split in studio.SPLITS:
        assert metrics["splits"][split]["accuracy"] == pytest.approx(2 / 3)
        assert metrics["splits"][split]["recall_go"] == 0
        assert metrics["splits"][split]["uncertain"] == 1

    with pytest.raises(ValueError, match="ne couvre pas"):
        studio.score(manifest, dict(response, predictions=predictions[:-1]))
    with pytest.raises(ValueError, match="en double"):
        studio.score(manifest, dict(response, predictions=predictions + [predictions[0]]))
