"""Contrôle qualité des enregistrements : les défauts doivent être détectés, jamais masqués."""

import numpy as np

from tinyml2027 import recording as R
from tinyml2027 import simulate


def test_clean_simulated_recording_is_valid():
    df = simulate.recording("stationary", duration_s=20, seed=0)
    qc = R.quality(df, min_windows=3)
    assert qc.valid, qc.reasons
    assert 110 < qc.measured_fs_hz < 118
    assert qc.n_windows_possible >= 3


def test_dropped_samples_are_detected():
    rng = np.random.default_rng(0)
    df = simulate.inject_faults(simulate.recording("periodic", seed=1), rng, n_drop=3)
    qc = R.quality(df)
    assert qc.n_seq_errors == 3 and not qc.valid


def test_duplicates_and_swapped_timestamps_are_detected():
    rng = np.random.default_rng(0)
    df = simulate.inject_faults(simulate.recording("impact", seed=2), rng, n_dup=2, n_swap=1)
    qc = R.quality(df)
    assert qc.n_seq_errors >= 2 and qc.n_time_errors >= 1 and not qc.valid


def test_too_short_recording_is_invalid():
    df = simulate.recording("stationary", duration_s=2, seed=0)
    qc = R.quality(df, min_windows=1)
    assert not qc.valid and qc.n_windows_possible == 0


def test_parse_lines_rejects_garbage():
    df, rejected = R.parse_lines(["0,0,0.1,0.2,1.0", "1,8700,0.1,0.2", "2,17400,0.1,x,1.0", "3,26100,0,0,1"])
    assert list(df.seq) == [0, 3] and len(rejected) == 2


def test_saturation_and_nan_flagged():
    df = simulate.recording("stationary", duration_s=5, seed=0)
    df.loc[10, "ax_g"] = 4.0
    df.loc[20, "ay_g"] = np.nan
    qc = R.quality(df, min_windows=0)
    assert qc.n_saturated == 1 and qc.n_nan == 1 and not qc.valid


def test_csv_roundtrip(tmp_path):
    df = simulate.recording("periodic", duration_s=3, seed=5)
    R.write_csv(df, tmp_path / "r.csv")
    back = R.read_csv(tmp_path / "r.csv")
    assert (back.seq == df.seq).all() and (back.t_us == df.t_us).all()
    assert np.abs(back.ax_g - df.ax_g).max() <= 5e-6
