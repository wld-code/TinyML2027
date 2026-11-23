"""Prépare un sous-ensemble de Speech Commands v0.02 pour Edge Impulse.

Classes : « go », « stop » et « bruit » (bruit de fond découpé + autres mots).
Séparation train/test **par locuteur**, à partir des listes officielles du jeu
(testing_list.txt) : aucun locuteur du test n'apparaît dans l'entraînement.

Usage :
    uv run python advanced/edge-impulse/prepare_speech_commands.py \
        --src CHEMIN/speech_commands_v0.02 --out CHEMIN/sortie

Chaque fichier de sortie est un WAV 16 kHz, mono, 16 bits, d'exactement 1 s
(les clips plus courts sont complétés par des zéros). Le nom commence par
le label (« go.xxx.wav »), ce qui permet à Edge Impulse de l'inférer.

Licence des données : CC BY 4.0, Pete Warden, « Speech Commands: A Dataset for
Limited-Vocabulary Speech Recognition », 2018. Ne versionnez pas les WAV.
"""
from __future__ import annotations

import argparse
import json
import random
import wave
from pathlib import Path

import numpy as np

SR = 16000
UNKNOWN_WORDS = ["yes", "no", "up", "down", "left", "right"]
# Bruits de fond : fichiers réservés au test (les autres vont à l'entraînement).
NOISE_TEST = {"running_tap.wav", "pink_noise.wav"}


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        if w.getframerate() != SR or w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError(f"{path} : format inattendu")
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")


def write_wav(path: Path, x: np.ndarray) -> None:
    x = np.asarray(x, dtype="<i2")
    if len(x) < SR:
        x = np.concatenate([x, np.zeros(SR - len(x), dtype="<i2")])
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(x[:SR].tobytes())


def speaker(rel: str) -> str:
    return Path(rel).name.split("_nohash_")[0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--train-per-class", type=int, default=200)
    ap.add_argument("--test-per-class", type=int, default=50)
    ap.add_argument("--seed", type=int, default=2027)
    a = ap.parse_args()
    rng = random.Random(a.seed)

    test_list = set((a.src / "testing_list.txt").read_text().split())
    val_list = set((a.src / "validation_list.txt").read_text().split())

    def files(word: str, split: str) -> list[str]:
        rels = sorted(f"{word}/{p.name}" for p in (a.src / word).glob("*.wav"))
        if split == "test":
            return [r for r in rels if r in test_list]
        return [r for r in rels if r not in test_list and r not in val_list]

    report: dict = {"seed": a.seed, "source": "speech_commands_v0.02", "splits": {}}
    for split, n in (("train", a.train_per_class), ("test", a.test_per_class)):
        out = a.out / split
        out.mkdir(parents=True, exist_ok=True)
        chosen: dict[str, list[str]] = {}
        for word in ("go", "stop"):
            chosen[word] = rng.sample(files(word, split), n)
        # bruit : moitié mots inconnus, moitié bruit de fond découpé en 1 s
        n_words = n // 2
        pool = [r for w in UNKNOWN_WORDS for r in files(w, split)]
        chosen["bruit"] = rng.sample(pool, n_words)
        for label, rels in chosen.items():
            for r in rels:
                write_wav(out / f"{label}.{r.replace('/', '_')}", read_wav(a.src / r))
        noise_files = sorted(p for p in (a.src / "_background_noise_").glob("*.wav")
                             if (p.name in NOISE_TEST) == (split == "test"))
        segs = []
        for p in noise_files:
            x = read_wav(p)
            segs += [(p.name, i) for i in range(0, len(x) - SR, SR)]
        for name, i in rng.sample(segs, n - n_words):
            x = read_wav(a.src / "_background_noise_" / name)[i:i + SR]
            write_wav(out / f"bruit.noise_{Path(name).stem}_{i // SR:03d}.wav", x)
        spk = {lab: len({speaker(r) for r in rels}) for lab, rels in chosen.items()}
        report["splits"][split] = {
            "clips_per_class": n, "speakers_per_class": spk,
            "noise_files": [p.name for p in noise_files],
        }
    train_spk = {speaker(f.name.split(".", 1)[1].split("_", 1)[1])
                 for f in (a.out / "train").glob("*.wav") if "noise_" not in f.name}
    test_spk = {speaker(f.name.split(".", 1)[1].split("_", 1)[1])
                for f in (a.out / "test").glob("*.wav") if "noise_" not in f.name}
    report["speaker_overlap_train_test"] = len(train_spk & test_spk)
    if report["speaker_overlap_train_test"]:
        raise SystemExit("ERREUR : un locuteur est à la fois dans le train et le test")
    (a.out / "subset_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
