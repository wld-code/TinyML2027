"""Rejeu numérique C++ AVANT la carte : features.h compilé sur le poste, comparé à Python.

Nécessite un compilateur C++ (clang++ ou g++) et les en-têtes générés par
`python -m tinyml2027.quantize_motion` ; sinon le test est ignoré.
"""

import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "labs/03-embedded-inference/firmware/infer_nano"
GOLD = ROOT / "artifacts/motion/golden_vectors.npz"


@pytest.mark.skipif(not (FW / "golden.h").exists() or not GOLD.exists(), reason="golden vectors non générés")
def test_cpp_features_match_python(tmp_path):
    cxx = shutil.which("clang++") or shutil.which("g++")
    if not cxx:
        pytest.skip("pas de compilateur C++")
    exe = tmp_path / "features_host"
    tflm = ROOT / ".arduino/user/libraries/Arduino_TensorFlowLite/src"   # kissfft officielle
    if not tflm.exists():
        pytest.skip("Arduino_TensorFlowLite non installée (./scripts/setup.sh)")
    subprocess.run([cxx, "-std=c++14", "-O2", "-ffp-contract=off", f"-I{tflm}",
                    str(ROOT / "tests/cpp/features_host.cpp"), str(FW / "kissfft_float.cpp"),
                    "-o", str(exe)], check=True)
    out = subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout.split("\n")
    gold = np.load(GOLD)
    for i, line in enumerate(l for l in out if l):
        name, *vals = line.split()
        assert name == gold["names"][i]
        rms, crest, dom, band, fs = map(float, vals)
        ref = gold["feat"][i]
        df = fs / 256
        if ref[0] < 1e-6:            # fenêtre « rms_zero » : les deux côtés doivent la reconnaître
            assert rms < 1e-6 and crest == dom == band == 0.0, name
            continue
        for got, exp in ((rms, ref[0]), (crest, ref[1]), (band, ref[3])):
            assert got == pytest.approx(exp, rel=1e-4), name
        assert abs(dom - ref[2]) <= df * 1.0001, name
