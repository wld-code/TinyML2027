import argparse
import importlib.util
import io
import json
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest
import requests

SCRIPT = Path(__file__).resolve().parents[1] / "advanced/edge-impulse-mlops/scripts/pipeline.py"
spec = importlib.util.spec_from_file_location("kws_pipeline", SCRIPT)
pipeline = importlib.util.module_from_spec(spec)
original_path = sys.path[:]
try:
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(pipeline)
finally:
    sys.path[:] = original_path


class Response:
    def __init__(self, value, status=200):
        self.value = value
        self.status_code = status
        self.headers = {}

    def json(self):
        return self.value


class Session:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        result = next(self.responses)
        if isinstance(result, Exception):
            raise result
        return result


def client(session):
    return pipeline.EdgeImpulse(42, "Lab privé", "secret-fictif", session)


def test_project_identity_and_pagination():
    session = Session(
        Response({"success": True, "project": {"id": 42, "name": "Lab privé", "isPublic": False}}),
        Response({"success": True, "samples": [{"id": 1}], "totalCount": 2}),
        Response({"success": True, "samples": [{"id": 2}], "totalCount": 2}),
    )
    api = client(session)
    assert api.check_project() == {"id": 42, "name": "Lab privé", "private": True}
    assert api.inventory("training") == [{"id": 1}, {"id": 2}]
    assert session.calls[-1][2]["params"]["offset"] == 1
    bad = Response({"success": True, "project": {"id": 42, "name": "Lab privé", "isPublic": True}})
    with pytest.raises(pipeline.PipelineError, match="projet privé"):
        client(Session(bad)).check_project()


def test_http_200_per_file_failure_and_no_write_retry(tmp_path):
    audio = tmp_path / "go.train-v1.train-0000.wav"
    audio.write_bytes(b"test")
    row = dict.fromkeys(("sample_id", "label", "split", "speaker_id", "source_file", "source_noise",
                        "augmentation", "snr_db", "sha256"), "go")
    session = Session(Response({"files": [{"success": False, "error": "erreur distante"}]}))
    with pytest.raises(pipeline.PipelineError, match="Import refusé"):
        client(session).upload(audio, row, "training")
    assert session.calls[0][1].endswith("/api/training/files")
    assert session.calls[0][2]["headers"]["x-label"] == "go"

    session = Session(requests.Timeout("secret-fictif"))
    with pytest.raises(pipeline.PipelineError, match="Vérifiez l’inventaire") as error:
        client(session).upload(audio, row, "training")
    assert "secret-fictif" not in str(error.value)
    assert len(session.calls) == 1


def test_job_success_failure_and_dry_run(monkeypatch, capsys):
    session = Session(Response({"job": {}}), Response({"job": {"finished": "now", "finishedSuccessful": True}}))
    client(session).wait(11, interval=0)
    with pytest.raises(pipeline.PipelineError, match="échec ou annulé"):
        client(Session(Response({"job": {"finished": "now", "finishedSuccessful": False}}))).wait(12)
    monkeypatch.delenv("EI_API_KEY", raising=False)
    args = argparse.Namespace(command="classify", project=42, name="Lab privé", impulse=1, apply=False)
    assert pipeline.run(args) == 0
    assert "Dry-run" in capsys.readouterr().out


def test_existing_import_verified_only_by_metadata(capsys):
    row = {"sample_id": "go.train-v1.train-0000", "label": "go", "sha256": "digest"}
    expected = {"filename": row["sample_id"], "label": row["label"], "metadata": {"sha256": "digest"}}
    empty = {"samples": [], "totalCount": 0}
    session = Session(Response({"samples": [expected], "totalCount": 1}), Response(empty))
    pipeline.send_samples(client(session), [(Path("unused.wav"), row)], "training")
    assert "1 clips déjà vérifiés, 0 à importer" in capsys.readouterr().out
    assert all(call[0] == "GET" for call in session.calls)
    conflict = dict(expected, metadata={})
    with pytest.raises(pipeline.PipelineError, match="non réconcilié"):
        pipeline.send_samples(client(Session(Response({"samples": [conflict], "totalCount": 1}), Response(empty))),
                              [(Path("unused.wav"), row)], "training")


def test_gate_and_arduino_zip():
    policy = json.loads((SCRIPT.parents[1] / "config/quality-gates.json").read_text(encoding="utf-8"))
    clean = {"n": 150, "accuracy": 0.8, "macro_f1": 0.8, "recall_go": 0.8,
             "recall_stop": 0.8, "false_trigger_rate": 0.05}
    baseline = {"manifest_sha256": "same", "splits": {pipeline.SPLITS[0]: clean,
                pipeline.SPLITS[1]: dict(clean, macro_f1=0.7)}}
    candidate = {"manifest_sha256": "same", "splits": {split: clean for split in pipeline.SPLITS}}
    hardware = {"firmware_compile": True, "firmware_init": True, "measured_acquisition_budget": True}
    assert pipeline.gate_report(baseline, candidate, policy)["decision"] == "pending"
    assert pipeline.gate_report(baseline, candidate, policy, hardware)["decision"] == "accepted"
    hardware["firmware_init"] = False
    assert pipeline.gate_report(baseline, candidate, policy, hardware)["decision"] == "rejected"
    with pytest.raises(pipeline.PipelineError, match="manifestes différents"):
        pipeline.gate_report(baseline, dict(candidate, manifest_sha256="other"), policy)
    blob = io.BytesIO()
    with ZipFile(blob, "w") as archive:
        archive.writestr("lab/library.properties", "name=lab")
        archive.writestr("lab/model_metadata.h", "\n".join(
            f"#define EI_CLASSIFIER_TFLITE_{kind}_DATATYPE EI_CLASSIFIER_DATATYPE_INT8"
            for kind in ("INPUT", "OUTPUT")
        ))
    pipeline.validate_zip(blob.getvalue())
    with pytest.raises(pipeline.PipelineError, match="illisible"):
        pipeline.validate_zip(b"pas un zip")


def test_rate_limit_retries_reads_without_repeating_writes(monkeypatch):
    monkeypatch.setattr(pipeline.time, "sleep", lambda _: None)
    limited = Response({"success": False}, 429)
    limited.headers["Retry-After"] = "2"
    session = Session(limited, Response({"success": True}))
    assert client(session).studio("GET")["success"] is True
    assert len(session.calls) == 2
    session = Session(limited)
    with pytest.raises(pipeline.PipelineError, match="HTTP 429"):
        client(session).start("generate-features", {"dspId": 1})
    assert len(session.calls) == 1
