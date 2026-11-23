"""Organisation du dataset : chemins, identifiants et manifest (docs/DATA_CONTRACT.md).

  data/
    manifest.csv                         une ligne par enregistrement, accepté ou non
    raw/<session_id>/<recording_id>.csv  enregistrements acceptés
    raw/<session_id>/<recording_id>.json métadonnées (firmware, OS, QC complet)
    rejected/<session_id>/...            enregistrements refusés, conservés pour analyse

`data/` est ignoré par git : les acquisitions des étudiants restent locales.
"""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

MANIFEST_COLUMNS = ["recording_id", "session_id", "condition", "trial", "board_revision", "board_id",
                    "source", "requested_fs_hz", "measured_fs_hz", "valid", "notes"]
CONDITIONS = ("stationary", "periodic", "impact")
_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def recording_id(session_id: str, condition: str, trial: int) -> str:
    rid = f"{session_id}_{condition}_t{trial:02d}"
    if not _ID.match(rid):
        raise ValueError(f"identifiant invalide : {rid!r} (lettres, chiffres, _ et -, 40 caractères max)")
    return rid


def board_id(usb_serial: str | None) -> str:
    """Identifiant court et non réversible de la carte (pas de l'étudiant)."""
    if not usb_serial:
        return "inconnu"
    return hashlib.sha256(usb_serial.encode()).hexdigest()[:8]


def recording_path(root: Path, session_id: str, rid: str, accepted: bool) -> Path:
    return Path(root) / ("raw" if accepted else "rejected") / session_id / f"{rid}.csv"


def read_manifest(root: Path) -> list[dict]:
    path = Path(root) / "manifest.csv"
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def append_manifest(root: Path, row: dict) -> None:
    path = Path(root) / "manifest.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = {r["recording_id"] for r in read_manifest(root)}
    if row["recording_id"] in existing:
        raise ValueError(f"{row['recording_id']} existe déjà dans {path} : choisissez un autre numéro d'essai")
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in MANIFEST_COLUMNS})
