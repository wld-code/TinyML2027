"""TP01 — du dataset brut à la table des caractéristiques.

  uv run python -m tinyml2027.build_features [--data data] [--out results/tp01]

Lit data/manifest.csv, ne garde que les enregistrements acceptés (valid=1), découpe
chacun en fenêtres de 256 échantillons (pas 128), écarte les fenêtres invalides
(lacune, séquence, temps) et calcule les 4 caractéristiques du contrat sur ax_g.

Sorties :
  features.csv       une ligne par fenêtre, valides ET invalides (colonne valid)
  quality_report.md  bilan par enregistrement : cadence, lacunes, fenêtres retenues
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from . import dataset, features, recording


def build(data_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    manifest = pd.DataFrame(dataset.read_manifest(data_root))
    if manifest.empty:
        raise SystemExit(f"aucun enregistrement dans {data_root / 'manifest.csv'}")
    tables, rows = [], []
    for _, m in manifest.iterrows():
        accepted = m["valid"] == "1"
        path = dataset.recording_path(data_root, m["session_id"], m["recording_id"], accepted)
        if not accepted:
            rows.append({"recording_id": m["recording_id"], "retenu": "non (refusé à l'acquisition)"})
            continue
        df = recording.read_csv(path)
        qc = recording.quality(df)
        f = features.extract(df)
        for col in ("recording_id", "session_id", "condition", "source", "board_revision"):
            f[col] = m[col]
        tables.append(f)
        rows.append({
            "recording_id": m["recording_id"], "session_id": m["session_id"], "condition": m["condition"],
            "source": m["source"], "echantillons": qc.n_samples, "fs_mesuree_hz": round(qc.measured_fs_hz, 2),
            "lacunes": qc.n_gaps, "fenetres": len(f), "fenetres_valides": int(f["valid"].sum()),
            "retenu": "oui",
        })
    table = pd.concat(tables, ignore_index=True)
    order = ["recording_id", "session_id", "condition", "source", "board_revision", "start", "end",
             "t_start_us", "valid", "reason", "fs_win_hz", *features.FEATURES, "rms_zero", "ambiguous_peak"]
    return table[order], pd.DataFrame(rows)


def md_table(df: pd.DataFrame, index: bool = True, fmt: str = "{:.4g}") -> str:
    """Tableau Markdown sans dépendance supplémentaire."""
    if index:
        df = df.reset_index()
    cells = [[fmt.format(v) if isinstance(v, float) else str(v) for v in row] for row in df.itertuples(index=False)]
    head = [str(c) for c in df.columns]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(r) + " |" for r in cells]
    return "\n".join(out)


def report(table: pd.DataFrame, summary: pd.DataFrame) -> str:
    v = table[table.valid]
    lines = [
        "# Rapport qualité TP01", "",
        "Généré par `python -m tinyml2027.build_features`. Fenêtres de 256 échantillons, pas de 128, axe ax_g.", "",
        "## Enregistrements", "", md_table(summary, index=False), "",
        "## Fenêtres valides par session et condition", "",
        md_table(v.pivot_table(index="session_id", columns="condition", values="start", aggfunc="count",
                               fill_value=0)), "",
        "## Médianes des caractéristiques par condition (fenêtres valides)", "",
        md_table(v.groupby("condition")[features.FEATURES].median()), "",
        f"Fenêtres invalides écartées : {int((~table.valid).sum())}. "
        f"Fenêtres à pic spectral ambigu : {int(v.ambiguous_peak.sum())}. "
        f"Fenêtres à RMS nulle : {int(v.rms_zero.sum())}.",
        "",
    ]
    if (table.source == "simulated").any():
        lines.append("**Attention : ce rapport contient des données SIMULÉES, sans valeur de preuve matérielle.**")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default="data", type=Path)
    ap.add_argument("--out", default="results/tp01", type=Path)
    args = ap.parse_args(argv)
    table, summary = build(args.data)
    args.out.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out / "features.csv", index=False, float_format="%.9g")
    (args.out / "quality_report.md").write_text(report(table, summary), encoding="utf-8", newline="\n")
    v = table[table.valid]
    print(f"{len(table)} fenêtres, {len(v)} valides -> {args.out / 'features.csv'}")
    print(v.groupby(["session_id", "condition"]).size().unstack(fill_value=0).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
