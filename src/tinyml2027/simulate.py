"""Générateur d'enregistrements SIMULÉS pour travailler sans carte.

Ces signaux servent aux tests automatiques, au tutoriel 01 et à l'exercice du TP02
quand aucune acquisition réelle n'est disponible. Ils ne prouvent RIEN sur le
matériel : toute donnée produite ici porte `source=simulated` dans le manifest.

Modèle volontairement simple (documenté pour que l'on puisse en discuter les limites) :
- cadence nominale 114 Hz avec gigue gaussienne de 3 % sur les intervalles
  (ordre de grandeur mesuré sur une Nano V1, evidence/lot0) ;
- gravité ≈ +1 g sur z, petit biais sur x et y, bruit blanc gaussien σ = 2 mg ;
- stationary : bruit seul ;
- periodic : sinusoïde de 1 à 2 Hz, amplitude 0,15 à 0,4 g sur x, plus une
  harmonique faible ;
- impact : impulsions amorties (≈ 30 Hz, décroissance 20 ms) de 0,1 à 0,3 g,
  1 à 2 par seconde, à intervalles irréguliers.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CONDITIONS = ("stationary", "periodic", "impact")
FS_NOMINAL_HZ = 114.0


def timestamps(n: int, rng: np.random.Generator, fs: float = FS_NOMINAL_HZ, jitter_cv: float = 0.03) -> np.ndarray:
    dt = 1e6 / fs * (1 + jitter_cv * rng.standard_normal(n - 1))
    dt = np.clip(dt, 0.5e6 / fs, 1.4e6 / fs)          # pas de lacune simulée par défaut
    return np.concatenate([[0], np.cumsum(np.round(dt))]).astype(np.int64)


def recording(condition: str, duration_s: float = 20.0, seed: int = 0, fs: float = FS_NOMINAL_HZ) -> pd.DataFrame:
    if condition not in CONDITIONS:
        raise ValueError(f"condition inconnue : {condition}")
    rng = np.random.default_rng(seed)
    n = int(duration_s * fs)
    t_us = timestamps(n, rng, fs)
    t = t_us * 1e-6
    noise = 0.002
    ax = rng.normal(0.0, 0.01) + noise * rng.standard_normal(n)
    ay = rng.normal(0.0, 0.01) + noise * rng.standard_normal(n)
    az = 1.0 + rng.normal(0.0, 0.01) + noise * rng.standard_normal(n)

    if condition == "periodic":
        f0 = rng.uniform(1.0, 2.0)
        amp = rng.uniform(0.15, 0.4)
        phase = rng.uniform(0, 2 * np.pi)
        ax = ax + amp * np.sin(2 * np.pi * f0 * t + phase) + 0.1 * amp * np.sin(4 * np.pi * f0 * t)
        ay = ay + 0.05 * amp * np.sin(2 * np.pi * f0 * t)
    elif condition == "impact":
        t_evt = 0.3
        while t_evt < t[-1]:
            a = rng.uniform(0.1, 0.3) * rng.choice([-1, 1])
            m = t >= t_evt
            tau = t[m] - t_evt
            pulse = a * np.exp(-tau / 0.02) * np.cos(2 * np.pi * 30 * tau)
            ax[m] += pulse
            az[m] += 0.5 * pulse
            t_evt += rng.uniform(0.5, 1.0)

    return pd.DataFrame({"seq": np.arange(n, dtype=np.int64), "t_us": t_us,
                         "ax_g": ax, "ay_g": ay, "az_g": az})


def inject_faults(df: pd.DataFrame, rng: np.random.Generator, n_drop: int = 0, n_dup: int = 0,
                  n_swap: int = 0) -> pd.DataFrame:
    """Dégrade un enregistrement pour les exercices et tests : pertes (lignes supprimées),
    doublons (ligne répétée) et timestamps inversés."""
    df = df.copy()
    if n_drop:
        idx = rng.choice(np.arange(10, len(df) - 10), n_drop, replace=False)
        df = df.drop(df.index[idx])
    if n_dup:
        idx = rng.choice(np.arange(10, len(df) - 10), n_dup, replace=False)
        df = pd.concat([df, df.iloc[idx]]).sort_index(kind="stable")
    df = df.reset_index(drop=True)
    if n_swap:
        for i in rng.choice(np.arange(10, len(df) - 10), n_swap, replace=False):
            df.loc[[i, i + 1], "t_us"] = df.loc[[i + 1, i], "t_us"].to_numpy()
    return df
