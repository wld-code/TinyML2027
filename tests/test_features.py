"""Caractéristiques du contrat v0.2 : vérifications numériques indépendantes."""

import numpy as np
import pytest
from scipy import signal

from tinyml2027 import features as F


def test_psd_equals_scipy_welch_single_segment():
    rng = np.random.default_rng(1)
    x = rng.normal(size=F.N)
    c = x - x.mean()
    fs = 114.2
    f, P = F.psd_one_sided(c, fs)
    fw, Pw = signal.welch(c, fs, window="hann", nperseg=F.N, scaling="density", detrend=False)
    np.testing.assert_allclose(f, fw, rtol=0, atol=1e-12)
    np.testing.assert_allclose(P, Pw, rtol=1e-12, atol=1e-15)


def test_constant_window_gives_zeros_and_flag():
    ft = F.compute(np.full(F.N, 0.98), 114.0)
    # mean(x) n'est pas exact en flottant : rms vaut ~1e-16 (float64) ou ~1e-8 (float32),
    # sous le seuil de 1e-6 g ; les trois autres features valent alors 0 (contrat v0.3).
    assert ft.rms_g < F.RMS_EPS_G and ft.rms_zero
    assert ft.crest_factor == ft.dominant_hz == ft.band_power_g2 == 0.0
    assert not np.isnan(ft.vector()).any()


@pytest.mark.parametrize("f0", [1.0, 2.5, 7.0])
def test_sine_on_bin_dominant_rms_crest_band_power(f0):
    fs = 128.0                       # f0 tombe exactement sur un bin : k = f0·N/fs
    n = np.arange(F.N)
    amp = 0.3
    x = 1.0 + amp * np.sin(2 * np.pi * f0 * n / fs)
    ft = F.compute(x, fs)
    assert ft.dominant_hz == pytest.approx(f0)
    assert ft.rms_g == pytest.approx(amp / np.sqrt(2), rel=1e-9)
    assert ft.crest_factor == pytest.approx(np.sqrt(2), rel=1e-3)
    # Hann : puissance répartie sur 3 bins, tous dans la bande -> ≈ A²/2 (théorème de Parseval)
    assert ft.band_power_g2 == pytest.approx(amp ** 2 / 2, rel=1e-6)


def test_out_of_band_sine_not_dominant_and_low_band_power():
    fs = 128.0
    n = np.arange(F.N)
    x = 0.3 * np.sin(2 * np.pi * 30.0 * n / fs) + 1e-4 * np.sin(2 * np.pi * 2.0 * n / fs)
    ft = F.compute(x, fs)
    assert ft.dominant_hz == pytest.approx(2.0)
    assert ft.band_power_g2 < 1e-6


def test_near_tie_is_flagged_ambiguous():
    # Deux raies de même amplitude : les bins ne sont égaux qu'à l'arrondi flottant près.
    fs = 128.0
    n = np.arange(F.N)
    x = np.sin(2 * np.pi * 2.0 * n / fs) + np.sin(2 * np.pi * 5.0 * n / fs)
    ft = F.compute(x, fs)
    assert ft.dominant_hz in (pytest.approx(2.0), pytest.approx(5.0))
    assert ft.ambiguous_peak


def test_exact_tie_takes_smallest_index(monkeypatch):
    fs = 128.0
    f = np.arange(F.N // 2 + 1) * fs / F.N
    P = np.zeros_like(f)
    P[[4, 10]] = 1.0                                 # égalité exacte à 2 Hz et 5 Hz
    monkeypatch.setattr(F, "psd_one_sided", lambda c, fs_: (f, P))
    ft = F.compute(np.random.default_rng(0).normal(size=F.N), fs)
    assert ft.dominant_hz == pytest.approx(2.0)


def test_fs_window_formula():
    t = np.arange(F.N, dtype=np.int64) * 8750      # 8,75 ms -> 114,2857 Hz
    assert F.fs_window(t) == pytest.approx(1e6 / 8750)


@pytest.mark.parametrize("fault,reason", [
    ("seq", "seq_non_consecutif"), ("time", "t_us_non_croissant"), ("gap", "lacune")])
def test_window_validity(fault, reason):
    seq = np.arange(F.N)
    t = np.arange(F.N, dtype=np.int64) * 8750
    if fault == "seq":
        seq = seq.copy(); seq[100:] += 1
    elif fault == "time":
        t = t.copy(); t[[50, 51]] = t[[51, 50]]
    else:
        t = t.copy(); t[200:] += 8750
    assert F.window_is_valid(seq, t) == (False, reason)
    assert F.window_is_valid(np.arange(F.N), np.arange(F.N) * 8750) == (True, "")


def test_extract_skips_windows_with_gap_only():
    from tinyml2027 import simulate
    df = simulate.recording("periodic", duration_s=10, seed=3)
    df.loc[600:, "t_us"] += 20000                   # une lacune de 20 ms vers l'échantillon 600
    out = F.extract(df)
    bad = out[~out.valid]
    assert set(bad.reason) == {"lacune"}
    assert all((bad.start <= 600) & (bad.end > 599))
    assert out.valid.sum() == len(out) - len(bad) > 0
