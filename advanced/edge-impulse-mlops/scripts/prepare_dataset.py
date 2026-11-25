"""Prépare les jeux audio versionnés du lab Edge MLOps."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import shutil
import sys
import tarfile
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import urlopen

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "edge-impulse"))
from prepare_speech_commands import SR, UNKNOWN_WORDS, read_wav, speaker, write_wav

URL = "https://storage.googleapis.com/download.tensorflow.org/data/speech_commands_v0.02.tar.gz"
ARCHIVE = "speech_commands_v0.02.tar.gz"
SHA256 = "af14739ee7dc311471de98f5f9d2c9191b18aedfe957f4a6ff791c709868ff58"
LABELS = ("go", "stop", "bruit")
GROUPS = ("train", "corrective", "promotion", "final")
COUNTS = dict(zip(GROUPS, (200, 100, 50, 50)))
FIELDS = (
    "sample_id", "label", "split", "partition", "pair_id", "speaker_id", "source_file",
    "source_offset", "base_pcm_sha256", "source_noise", "noise_offset", "augmentation", "snr_db",
    "gain_db", "shift_samples", "duration_ms", "sample_rate_hz", "sha256", "pcm_sha256",
)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def extract_source(cache):
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / ARCHIVE
    source = cache / "speech_commands_v0.02"
    if not archive.exists():
        with tempfile.NamedTemporaryFile(dir=cache, delete=False) as output:
            temporary = Path(output.name)
        try:
            with urlopen(URL, timeout=60) as response, temporary.open("wb") as output:
                shutil.copyfileobj(response, output)
            if digest(temporary) != SHA256:
                raise ValueError("SHA-256 incorrect pour l’archive téléchargée")
            os.replace(temporary, archive)
        finally:
            temporary.unlink(missing_ok=True)
    if digest(archive) != SHA256:
        raise ValueError(f"SHA-256 incorrect pour {archive}")
    if source.exists():
        return source
    with tempfile.TemporaryDirectory(dir=cache) as temporary:
        staged = Path(temporary) / "source"
        staged.mkdir()
        with tarfile.open(archive, "r|gz") as tar:
            for member in tar:
                relative = Path(member.name)
                parts = relative.parts
                if not member.isfile():
                    continue
                wanted = (
                    len(parts) == 1 and relative.name in {"testing_list.txt", "validation_list.txt", "LICENSE", "README.md"}
                ) or (
                    len(parts) == 2 and parts[0] in {"go", "stop", *UNKNOWN_WORDS, "_background_noise_"}
                    and relative.suffix == ".wav"
                )
                if wanted:
                    target = staged / relative
                    target.parent.mkdir(exist_ok=True)
                    with tar.extractfile(member) as data, target.open("wb") as output:
                        shutil.copyfileobj(data, output)
        staged.rename(source)
    return source


def groups(source, rng):
    official = {
        group: {speaker(rel) for rel in (source / name).read_text(encoding="utf-8").split()}
        for group, name in (("promotion", "validation_list.txt"), ("final", "testing_list.txt"))
    }
    if official["promotion"] & official["final"]:
        raise ValueError("Les partitions officielles partagent des locuteurs")
    paths = sorted(p for word in ("go", "stop", *UNKNOWN_WORDS) for p in (source / word).glob("*.wav"))
    available = sorted({speaker(path.name) for path in paths} - official["promotion"] - official["final"])
    rng.shuffle(available)
    cut = len(available) // 3
    official["corrective"] = set(available[:cut])
    official["train"] = set(available[cut:])
    owner = {person: group for group, people in official.items() for person in people}
    pools = defaultdict(list)
    for path in paths:
        word = path.parent.name
        pools[owner[speaker(path.name)], word if word in LABELS else "bruit"].append(path)
    noise = sorted((source / "_background_noise_").glob("*.wav"))
    if len(noise) < len(GROUPS):
        raise ValueError("Il faut au moins quatre bruits sources indépendants")
    rng.shuffle(noise)
    return pools, {group: noise[i::len(GROUPS)] for i, group in enumerate(GROUPS)}


def fixed_clip(values):
    return np.pad(values[:SR], (0, max(0, SR - len(values)))).astype(np.float64) / 32768


def select_bases(pools, noise, group, count, rng, seen):
    for label in LABELS:
        background = [
            (path, offset) for path in noise[group]
            for offset in range(0, len(read_wav(path)) - SR + 1, SR)
        ] if label == "bruit" else []
        speech = [(path, None) for path in pools[group, label]]
        rng.shuffle(background)
        rng.shuffle(speech)
        accepted = noise_count = 0
        for path, offset in background + speech:
            if offset is not None and noise_count >= count // 4:
                continue
            raw = read_wav(path)
            base = fixed_clip(raw if offset is None else raw[offset:offset + SR])
            identity = hashlib.sha256((base * 32768).astype("<i2").tobytes()).hexdigest()
            if identity in seen or not np.any(base):
                continue
            seen.add(identity)
            yield label, path, offset, base, identity
            accepted += 1
            noise_count += offset is not None
            if accepted == count:
                break
        if accepted != count:
            raise ValueError(f"{group}/{label} : {accepted} sources distinctes sur {count} requises")


def degrade(values, noise_path, shift, gain, snr, rng):
    shifted = np.zeros(SR)
    if shift > 0:
        shifted[shift:] = values[:-shift]
    else:
        shifted[:SR + shift] = values[-shift:]
    shifted *= 10 ** (gain / 20)
    noise = read_wav(noise_path)
    offset = rng.randrange(len(noise) - SR + 1)
    component = fixed_clip(noise[offset:offset + SR])
    norm = np.linalg.norm(component)
    if not norm:
        raise ValueError(f"Fenêtre de bruit nulle dans {noise_path.name}")
    component *= np.linalg.norm(shifted) / (norm * 10 ** (snr / 20))
    mixed = shifted + component
    mixed /= max(1, np.max(np.abs(mixed)) * 32768 / 32767)
    return mixed, offset


def check_manifest(rows):
    owners = defaultdict(set)
    ids, hashes, pcm = set(), set(), set()
    for row in rows:
        for key, seen in (("sample_id", ids), ("sha256", hashes), ("pcm_sha256", pcm)):
            if row[key] in seen:
                raise ValueError(f"Doublon {key} pour {row['sample_id']}")
            seen.add(row[key])
        owners["base PCM", row["base_pcm_sha256"]].add(row["partition"])
        if row["speaker_id"]:
            owners["speaker", row["speaker_id"]].add(row["partition"])
        for key in ("source_file", "source_noise"):
            if row[key]:
                owners["file", row[key]].add(row["partition"])
    for entity, partitions in owners.items():
        if len(partitions) > 1:
            raise ValueError(f"Fuite entre partitions pour {entity}")


def prepare(source, out, seed=2027, counts=COUNTS):
    rng = random.Random(seed)
    pools, noise = groups(source, rng)
    rows = []
    seen = set()
    for group in reversed(GROUPS):
        selected = select_bases(pools, noise, group, counts[group], rng, seen)
        for index, (label, path, offset, base, identity) in enumerate(selected):
            pair = f"{group}-{index:04d}"
            splits = {
                "train": ("train-v1",), "corrective": ("corrective-v2",),
                "promotion": ("evaluation-clean", "evaluation-shifted"),
                "final": ("final-clean", "final-shifted"),
            }[group]
            for split in splits:
                augmented = split.endswith("shifted") or group == "corrective"
                sound, source_noise, noise_offset, gain, shift, snr = base, "", "", "", "", ""
                if augmented:
                    noise_path = rng.choice([p for p in noise[group] if p != path] or noise[group])
                    gain, shift, snr = rng.choice((-12, -6, -3)), rng.choice((-1200, -600, 600, 1200)), rng.choice((0, 5, 10, 15))
                    sound, noise_offset = degrade(base, noise_path, shift, gain, snr, rng)
                    source_noise = noise_path.relative_to(source).as_posix()
                sample_id = f"{label}.{split}.{pair}"
                target = out / split / f"{sample_id}.wav"
                target.parent.mkdir(exist_ok=True, parents=True)
                samples = np.clip(np.rint(sound * 32768), -32768, 32767).astype("<i2")
                write_wav(target, samples)
                rows.append(dict(
                    sample_id=sample_id, label=label, split=split, partition=group, pair_id=pair,
                    speaker_id=speaker(path.name) if offset is None else "",
                    source_file=path.relative_to(source).as_posix(), source_offset="" if offset is None else offset,
                    base_pcm_sha256=identity, source_noise=source_noise, noise_offset=noise_offset,
                    augmentation="shift+gain+mix" if augmented else "none", snr_db=snr,
                    gain_db=gain, shift_samples=shift, duration_ms=1000, sample_rate_hz=SR,
                    sha256=digest(target), pcm_sha256=hashlib.sha256(samples.tobytes()).hexdigest(),
                ))
    check_manifest(rows)
    with (out / "manifest.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "seed": seed, "splits": {
            split: dict(Counter(row["label"] for row in rows if row["split"] == split))
            for split in sorted({row["split"] for row in rows})
        },
        "origins": {
            group: {"speakers": len({r["speaker_id"] for r in rows if r["partition"] == group and r["speaker_id"]}),
                    "noise_sources": [p.name for p in noise[group]]}
            for group in GROUPS
        },
        "manifest_sha256": digest(out / "manifest.csv"),
    }
    (out / "report.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", default=Path("data/edge-impulse-mlops/cache"), type=Path)
    parser.add_argument("--src", type=Path, help="archive officielle déjà extraite")
    parser.add_argument("--out", default=Path("data/edge-impulse-mlops/datasets"), type=Path)
    args = parser.parse_args()
    if args.out.exists():
        parser.error(f"{args.out} existe déjà. Choisissez un nouveau dossier de sortie.")
    source = args.src or extract_source(args.cache)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.out.parent) as temporary:
        stage = Path(temporary) / "datasets"
        prepare(source, stage)
        stage.rename(args.out)
    print(f"Jeux de données vérifiés. Rapport dans {args.out / 'report.json'}.")


if __name__ == "__main__":
    main()
