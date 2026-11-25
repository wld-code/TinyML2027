import argparse
import json
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "advanced/edge-impulse-mlops/scripts"
ROOT = SCRIPTS.parents[2]
EVIDENCE = ROOT / "evidence/edge-impulse-mlops"


@pytest.fixture
def release_tool(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import release_kws
    return release_kws


@pytest.fixture
def archived(tmp_path, monkeypatch, release_tool):
    artifacts = tmp_path / "inputs"
    artifacts.mkdir()
    export = artifacts / "arduino-int8.zip"
    export.write_bytes(b"simulated library")
    dataset = artifacts / "manifest.csv"
    dataset.write_text("sample_id\nexample\n", encoding="utf-8", newline="\n")
    digest = release_tool.file_sha256(export)
    metrics = json.loads((EVIDENCE / "kws-v2-promotion.json").read_text(encoding="utf-8"))
    metrics["manifest_sha256"] = release_tool.file_sha256(dataset)
    (artifacts / "experiment.json").write_text(json.dumps({
        "name": "kws-v2", "project_id": 1, "arduino_export_sha256": digest,
        "manifest_sha256": metrics["manifest_sha256"],
    }), encoding="utf-8", newline="\n")
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8", newline="\n")
    hardware = tmp_path / "hardware.json"
    hardware.write_text('{"firmware_compile": true}', encoding="utf-8", newline="\n")
    binary = tmp_path / "image.bin"
    binary.write_bytes(f"kws_nano 0.1.1\0kws-v2\0{digest}\0".encode())
    monkeypatch.setattr(release_tool, "validate_zip", lambda _: "#define EI_CLASSIFIER_PROJECT_ID 1\n")
    args = argparse.Namespace(
        destination=tmp_path / "kws-v2", artifacts=artifacts, binary=binary,
        metrics=metrics_path, baseline=metrics_path, hardware=hardware,
    )
    manifest = release_tool.archive(args)
    return args, manifest


def test_archive_detects_modification_and_refuses_overwrite(release_tool, archived):
    args, manifest = archived
    assert release_tool.validate(args.destination) == manifest
    with pytest.raises(release_tool.ReleaseError, match="existe déjà"):
        release_tool.archive(args)
    (args.destination / "kws_nano.ino.bin").write_bytes(b"changed")
    with pytest.raises(release_tool.ReleaseError, match="Intégrité invalide"):
        release_tool.validate(args.destination)


@pytest.mark.parametrize("operation", ["flash", "restore"])
def test_rejected_candidate_cannot_access_usb(release_tool, archived, monkeypatch, operation):
    args, manifest = archived

    def unexpected_port(_):
        pytest.fail("Un candidat refusé ne doit pas ouvrir le port.")

    monkeypatch.setattr(release_tool, "pick_port", unexpected_port)
    with pytest.raises(release_tool.ReleaseError):
        release_tool.upload(args.destination, manifest, operation, None, True)
