"""Fenêtrage et caractéristiques de référence (docs/DATA_CONTRACT.md, version 0.2).

Implémentation de RÉFÉRENCE en float64. Le firmware du TP03 doit reproduire ces
calculs en float32 ; les golden vectors comparent les deux.

Notations : fenêtre de N = 256 échantillons x[n] de l'axe ax_g (en g), n = 0..N-1 ;
fs = fs_win, cadence mesurée de la fenêtre (Hz).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

N = 256
HOP = 128
BAND_HZ = (0.5, 10.0)
RMS_EPS_G = 1e-6   # v0.3 : 1e-9 était sous le résidu d'arrondi float32 (voir DATA_CONTRACT)
GAP_FACTOR = 1.5
FEATURES = ["rms_g", "crest_factor", "dominant_hz", "band_power_g2"]


def fs_window(t_us: np.ndarray) -> float:
    """fs_win = (N − 1) / ((t_us[N−1] − t_us[0]) · 1e−6), en Hz."""
    t_us = np.asarray(t_us, np.int64)
    return (len(t_us) - 1) / ((t_us[-1] - t_us[0]) * 1e-6)


def window_is_valid(seq: np.ndarray, t_us: np.ndarray) -> tuple[bool, str]:
    """Règle du contrat : seq consécutif, t_us strictement croissant, aucun intervalle
    supérieur à 1,5 × la médiane des intervalles de la fenêtre."""
    dseq = np.diff(np.asarray(seq, np.int64))
    dt = np.diff(np.asarray(t_us, np.int64))
    if (dseq != 1).any():
        return False, "seq_non_consecutif"
    if (dt <= 0).any():
        return False, "t_us_non_croissant"
    if (dt > GAP_FACTOR * np.median(dt)).any():
        return False, "lacune"
    return True, ""


def hann_periodic(n: int = N) -> np.ndarray:
    """w[n] = 0,5 − 0,5·cos(2πn/N), n = 0..N−1 (fenêtre de Hann « périodique »)."""
    return 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / n)


def psd_one_sided(c: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    """PSD une face d'un seul segment, en g²/Hz. Renvoie (f en Hz, P).

    X[k] = Σ c[n]·w[n]·e^(−2iπkn/N) ; P[k] = a_k·|X[k]|² / (fs·Σw²),
    a_k = 1 pour k = 0 et k = N/2, 2 sinon ; f[k] = k·fs/N, k = 0..N/2.
    """
    n = len(c)
    w = hann_periodic(n)
    X = np.fft.rfft(c * w)
    a = np.full(len(X), 2.0)
    a[0] = 1.0
    if n % 2 == 0:
        a[-1] = 1.0
    P = a * np.abs(X) ** 2 / (fs * np.sum(w ** 2))
    f = np.arange(len(X)) * fs / n
    return f, P


@dataclass
class Features:
    rms_g: float
    crest_factor: float
    dominant_hz: float
    band_power_g2: float
    rms_zero: bool
    ambiguous_peak: bool
    fs_win_hz: float

    def vector(self) -> np.ndarray:
        return np.array([self.rms_g, self.crest_factor, self.dominant_hz, self.band_power_g2])


def compute(x: np.ndarray, fs: float) -> Features:
    """Les quatre caractéristiques du contrat sur une fenêtre x (g) échantillonnée à fs (Hz)."""
    x = np.asarray(x, np.float64)
    c = x - x.mean()
    rms = float(np.sqrt(np.mean(c ** 2)))
    rms_zero = rms < RMS_EPS_G
    crest = float(np.max(np.abs(c)) / rms) if not rms_zero else 0.0

    if rms_zero:
        # Fenêtre constante (au bruit d'arrondi près) : pas de spectre exploitable.
        return Features(rms, 0.0, 0.0, 0.0, True, False, fs)
    f, P = psd_one_sided(c, fs)
    band = np.flatnonzero((f >= BAND_HZ[0]) & (f <= BAND_HZ[1]))
    pb = P[band]
    k = int(np.argmax(pb))                   # argmax renvoie le plus petit indice en cas d'égalité
    dominant = float(f[band[k]])
    band_power = float(np.sum(pb) * fs / len(x))
    top2 = np.sort(pb)[-2:]
    ambiguous = bool(top2[1] > 0 and (top2[1] - top2[0]) / top2[1] < 1e-4)
    return Features(rms, crest, dominant, band_power, rms_zero, ambiguous, fs)


def windows(df: pd.DataFrame, n: int = N, hop: int = HOP):
    """Génère (début, fin, valide, raison) pour chaque fenêtre [début, début+n) d'un enregistrement."""
    seq = df["seq"].to_numpy(np.int64)
    t = df["t_us"].to_numpy(np.int64)
    for s in range(0, len(df) - n + 1, hop):
        ok, why = window_is_valid(seq[s:s + n], t[s:s + n])
        yield s, s + n, ok, why


def extract(df: pd.DataFrame, axis: str = "ax_g") -> pd.DataFrame:
    """Une ligne par fenêtre : position, validité, fs_win et les quatre features (NaN si invalide)."""
    rows = []
    t = df["t_us"].to_numpy(np.int64)
    x = df[axis].to_numpy(np.float64)
    for s, e, ok, why in windows(df):
        row = {"start": s, "end": e, "t_start_us": int(t[s]), "valid": ok, "reason": why}
        if ok:
            fs = fs_window(t[s:e])
            ft = compute(x[s:e], fs)
            row.update(fs_win_hz=fs, rms_g=ft.rms_g, crest_factor=ft.crest_factor,
                       dominant_hz=ft.dominant_hz, band_power_g2=ft.band_power_g2,
                       rms_zero=ft.rms_zero, ambiguous_peak=ft.ambiguous_peak)
        rows.append(row)
    return pd.DataFrame(rows)
