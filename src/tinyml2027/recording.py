"""Enregistrements bruts de l'accéléromètre : lecture, écriture et contrôle qualité.

Format d'un enregistrement (docs/DATA_CONTRACT.md) : CSV `seq,t_us,ax_g,ay_g,az_g`,
où `t_us` est l'instant d'échantillonnage côté carte, relatif au premier échantillon.

Le contrôle qualité ne corrige rien : il mesure et signale. Une lacune n'est jamais
interpolée ; c'est le fenêtrage qui refusera les fenêtres qui la contiennent.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS = ["seq", "t_us", "ax_g", "ay_g", "az_g"]
GAP_FACTOR = 1.5           # intervalle > 1,5 × médiane = lacune (contrat de données)
ACCEL_RANGE_G = 4.0        # pleine échelle configurée par les deux bibliothèques IMU (±4 g)
N_WINDOW = 256             # taille de fenêtre du contrat


@dataclass
class QualityReport:
    n_samples: int
    duration_s: float
    measured_fs_hz: float          # (n-1) / durée, sur tout l'enregistrement
    median_dt_us: float
    jitter_cv: float               # écart-type / moyenne des intervalles
    n_seq_errors: int              # seq non consécutif (saut, doublon, retour arrière)
    n_time_errors: int             # t_us non strictement croissant
    n_gaps: int                    # intervalles > GAP_FACTOR × médiane
    max_gap_us: int
    n_nan: int
    n_saturated: int               # |a| ≥ pleine échelle sur au moins un axe
    n_windows_possible: int        # fenêtres de N échantillons sans lacune (pas = N/2)
    valid: bool
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def read_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path} : colonnes manquantes {missing}")
    return df[COLUMNS]


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df[COLUMNS].to_csv(path, index=False, float_format="%.5f")


def parse_lines(lines: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Convertit les lignes de données reçues du firmware en tableau.

    Renvoie (données, lignes rejetées). Une ligne mal formée (transmission coupée,
    caractère parasite) est rejetée et comptée, jamais réparée.
    """
    rows, rejected = [], []
    for line in lines:
        parts = line.strip().split(",")
        if len(parts) != 5:
            rejected.append(line)
            continue
        try:
            rows.append((int(parts[0]), int(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])))
        except ValueError:
            rejected.append(line)
    df = pd.DataFrame(rows, columns=COLUMNS)
    return df.astype({"seq": "int64", "t_us": "int64"}), rejected


def _windows_without_gap(gap_mask: np.ndarray, n_samples: int, n: int = N_WINDOW) -> int:
    """Nombre de fenêtres [s, s+n) avec un pas de n/2 qui ne contiennent aucune lacune.

    gap_mask[i] est vrai si l'intervalle entre l'échantillon i et i+1 est invalide.
    """
    if n_samples < n:
        return 0
    bad = np.concatenate([[0], np.cumsum(gap_mask.astype(int))])
    return sum(1 for s in range(0, n_samples - n + 1, n // 2) if bad[s + n - 1] - bad[s] == 0)


def quality(df: pd.DataFrame, min_windows: int = 1) -> QualityReport:
    reasons: list[str] = []
    n = len(df)
    if n < 2:
        return QualityReport(n, 0.0, float("nan"), float("nan"), float("nan"), 0, 0, 0, 0, 0, 0, 0, False,
                             ["moins de 2 échantillons"])
    seq = df["seq"].to_numpy(np.int64)
    t = df["t_us"].to_numpy(np.int64)
    acc = df[["ax_g", "ay_g", "az_g"]].to_numpy(np.float64)

    dseq = np.diff(seq)
    dt = np.diff(t)
    n_seq_err = int((dseq != 1).sum())
    n_time_err = int((dt <= 0).sum())
    pos = dt[dt > 0]
    med = float(np.median(pos)) if len(pos) else float("nan")
    gap_mask = (dseq != 1) | (dt <= 0) | (dt > GAP_FACTOR * med)
    n_gaps = int((dt > GAP_FACTOR * med).sum())
    duration = (t[-1] - t[0]) * 1e-6
    fs = (n - 1) / duration if duration > 0 else float("nan")
    n_nan = int(np.isnan(acc).any(axis=1).sum())
    n_sat = int((np.abs(acc) >= ACCEL_RANGE_G - 1e-3).any(axis=1).sum())
    n_win = _windows_without_gap(gap_mask, n)

    if n_seq_err:
        reasons.append(f"{n_seq_err} rupture(s) de séquence")
    if n_time_err:
        reasons.append(f"{n_time_err} timestamp(s) non croissant(s)")
    if n_nan:
        reasons.append(f"{n_nan} échantillon(s) NaN")
    if n_sat:
        reasons.append(f"{n_sat} échantillon(s) saturé(s) à ±{ACCEL_RANGE_G:g} g")
    if n_win < min_windows:
        reasons.append(f"{n_win} fenêtre(s) de {N_WINDOW} échantillons sans lacune (minimum {min_windows})")
    # Les lacunes isolées n'invalident pas l'enregistrement : les fenêtres qui les
    # contiennent seront écartées. Elles sont comptées et affichées.
    return QualityReport(
        n_samples=n, duration_s=duration, measured_fs_hz=fs, median_dt_us=med,
        jitter_cv=float(dt.std() / dt.mean()) if dt.mean() > 0 else float("nan"),
        n_seq_errors=n_seq_err, n_time_errors=n_time_err, n_gaps=n_gaps,
        max_gap_us=int(dt.max()), n_nan=n_nan, n_saturated=n_sat, n_windows_possible=n_win,
        valid=not reasons, reasons=reasons,
    )


def format_report(r: QualityReport) -> str:
    lines = [
        f"échantillons      : {r.n_samples} sur {r.duration_s:.2f} s",
        f"cadence mesurée   : {r.measured_fs_hz:.2f} Hz (intervalle médian {r.median_dt_us:.0f} µs, CV {r.jitter_cv:.3f})",
        f"séquence / temps  : {r.n_seq_errors} rupture(s), {r.n_time_errors} timestamp(s) non croissant(s)",
        f"lacunes           : {r.n_gaps} (plus grande {r.max_gap_us} µs)",
        f"NaN / saturations : {r.n_nan} / {r.n_saturated}",
        f"fenêtres de {N_WINDOW}  : {r.n_windows_possible} sans lacune",
        "VERDICT           : " + ("VALIDE" if r.valid else "INVALIDE — " + " ; ".join(r.reasons)),
    ]
    return "\n".join(lines)
