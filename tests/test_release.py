"""Edge MLOps : une release incohérente doit être refusée AVANT tout téléversement."""

import json
import shutil

import pytest

from tinyml2027 import release as R


@pytest.fixture
def good_release(tmp_path):
    d = tmp_path / "motion-vX"
    (d / "firmware").mkdir(parents=True)
    (d / "model_int8.tflite").write_bytes(b"TFL3 faux modele")
    (d / "golden_vectors.npz").write_bytes(b"golden")
    (d / "firmware" / "infer_nano.ino.bin").write_bytes(b"\x00binaire")
    lock = R.versions_lock()
    files = {str(p.relative_to(d)): R.sha256(p) for p in d.rglob("*") if p.is_file()}
    man = {"model_version": "motion-vX", "firmware_version": "infer_nano 0.1.0",
           "model_int8_sha256": R.sha256(d / "model_int8.tflite"), "firmware_bin": "infer_nano.ino.bin",
           "files": files, "board": lock["ARDUINO_FQBN"], "board_core": lock["ARDUINO_CORE"],
           "board_revision": "original", "runtime": "x", "feature_schema": R.EXPECTED_SCHEMA,
           "labels": R.EXPECTED_LABELS, "tested_os": [], "acceptance_status": "candidate"}
    (d / "release_manifest.json").write_text(json.dumps(man), encoding="utf-8", newline="\n")
    return d


def _edit(d, **changes):
    m = json.loads((d / "release_manifest.json").read_text(encoding="utf-8"))
    m.update(changes)
    (d / "release_manifest.json").write_text(json.dumps(m), encoding="utf-8", newline="\n")


def test_good_release_is_valid(good_release):
    assert R.validate(good_release)["model_version"] == "motion-vX"


def test_corrupted_json_refused(good_release):
    (good_release / "release_manifest.json").write_text("{pas du json", encoding="utf-8", newline="\n")
    with pytest.raises(R.ReleaseError, match="illisible"):
        R.validate(good_release)


def test_modified_model_refused(good_release):
    (good_release / "model_int8.tflite").write_bytes(b"autre modele")
    with pytest.raises(R.ReleaseError, match="modifié"):
        R.validate(good_release)


def test_wrong_label_order_refused(good_release):
    _edit(good_release, labels=["periodic", "stationary", "impact"])
    with pytest.raises(R.ReleaseError, match="labels"):
        R.validate(good_release)


def test_other_feature_schema_refused(good_release):
    _edit(good_release, feature_schema=["rms_g", "crest_factor", "dominant_hz", "band_power_g2"])
    with pytest.raises(R.ReleaseError, match="schéma"):
        R.validate(good_release)


def test_missing_field_and_missing_file_refused(good_release, tmp_path):
    other = tmp_path / "copie"
    shutil.copytree(good_release, other)
    m = json.loads((other / "release_manifest.json").read_text(encoding="utf-8"))
    del m["board_revision"]
    (other / "release_manifest.json").write_text(json.dumps(m), encoding="utf-8", newline="\n")
    with pytest.raises(R.ReleaseError, match="champs absents"):
        R.validate(other)
    (good_release / "golden_vectors.npz").unlink()
    with pytest.raises(R.ReleaseError, match="manquant"):
        R.validate(good_release)


def test_wrong_board_core_refused(good_release):
    _edit(good_release, board_core="arduino:mbed_nano@4.0.0")
    with pytest.raises(R.ReleaseError, match="core"):
        R.validate(good_release)
