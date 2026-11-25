import importlib.util
import sys
from wave import open as open_wave
from pathlib import Path

import numpy as np
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "advanced/edge-impulse-mlops/scripts/prepare_dataset.py"
spec = importlib.util.spec_from_file_location("kws_prepare", SCRIPT)
dataset = importlib.util.module_from_spec(spec)
original_path = sys.path[:]
try:
    spec.loader.exec_module(dataset)
finally:
    sys.path[:] = original_path


def test_preparation_reproducible(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    rng = np.random.default_rng(11)
    for word in ("go", "stop", "yes"):
        (source / word).mkdir()
        for index in range(12):
            dataset.write_wav(source / word / f"speaker{index}_nohash_0.wav",
                              rng.integers(-4000, 4000, 14000, dtype=np.int16))
    (source / "validation_list.txt").write_text("go/speaker10_nohash_0.wav\n", encoding="utf-8", newline="\n")
    (source / "testing_list.txt").write_text("go/speaker11_nohash_0.wav\n", encoding="utf-8", newline="\n")
    noise = source / "_background_noise_"
    noise.mkdir()
    for index in range(4):
        dataset.write_wav(noise / f"noise{index}.wav", rng.integers(-2000, 2000, 16000, dtype=np.int16))
    counts = dict.fromkeys(dataset.GROUPS, 1)
    first, second = tmp_path / "first", tmp_path / "second"
    rows = dataset.prepare(source, first, counts=counts)
    assert dataset.prepare(source, second, counts=counts) == rows
    assert (first / "manifest.csv").read_bytes() == (second / "manifest.csv").read_bytes()
    assert len(rows) == 18
    for row in rows:
        wav = first / row["split"] / (row["sample_id"] + ".wav")
        with open_wave(str(wav), "rb") as clip:
            assert (clip.getnchannels(), clip.getsampwidth(), clip.getframerate(), clip.getnframes()) == (1, 2, 16000, 16000)
        assert dataset.digest(wav) == row["sha256"]
    clean = next(row for row in rows if row["split"] == "evaluation-clean")
    shifted = next(row for row in rows if row["split"] == "evaluation-shifted" and row["pair_id"] == clean["pair_id"])
    assert clean["base_pcm_sha256"] == shifted["base_pcm_sha256"]
    assert clean["pcm_sha256"] != shifted["pcm_sha256"]


def test_manifest_rejects_duplicate_and_leak():
    row = dict(sample_id="one", sha256="wav-1", pcm_sha256="pcm-1", base_pcm_sha256="base-1",
               speaker_id="a", source_file="go/a.wav", source_noise="background/a.wav", partition="train")
    with pytest.raises(ValueError, match="Doublon pcm_sha256"):
        dataset.check_manifest([row, dict(row, sample_id="two", sha256="wav-2")])
    other = dict(row, sample_id="two", sha256="wav-2", pcm_sha256="pcm-2",
                 base_pcm_sha256="base-2", speaker_id="b", source_file="stop/b.wav", partition="final")
    with pytest.raises(ValueError, match="Fuite.*background/a.wav"):
        dataset.check_manifest([row, other])
    with pytest.raises(ValueError, match="Fuite.*speaker"):
        dataset.check_manifest([row, dict(other, source_noise="", speaker_id="a")])
