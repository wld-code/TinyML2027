"""Vérifie un ZIP EON INT8, prépare le sketch et compile pour la Nano originale."""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

from pipeline import PipelineError, file_sha256, validate_zip

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB.parents[1]


def build(archive, release):
    if not re.fullmatch(r"kws-v[1-9][0-9]*", release):
        raise PipelineError("Version attendue sous la forme kws-v1.")
    blob = archive.read_bytes()
    validate_zip(blob)
    digest = file_sha256(archive)
    work = ROOT / "build/kws-inputs" / release / digest
    sketch = work / "kws_nano"
    libraries = work / "libraries"
    sketch.mkdir(parents=True, exist_ok=True)
    libraries.mkdir(exist_ok=True)
    with ZipFile(archive) as bundle:
        headers = [Path(name) for name in bundle.namelist() if name.endswith("/library.properties")]
        if len(headers) != 1 or len(headers[0].parts) != 2:
            raise PipelineError("Structure de la bibliothèque Arduino inattendue.")
        name = headers[0].parent.name
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise PipelineError("Nom de bibliothèque Arduino invalide.")
        library = libraries / name
        if any(Path(entry.filename).is_absolute() or ".." in Path(entry.filename).parts
               or "\\" in entry.filename for entry in bundle.infolist()):
            raise PipelineError("Chemin non autorisé dans le ZIP.")
        bundle.extractall(libraries)
    header = name + ".h"
    if not (library / "src" / header).is_file():
        raise PipelineError("En-tête d’inférence Arduino absent.")
    shutil.copy2(LAB / "firmware/kws_nano/kws_nano.ino", sketch / "kws_nano.ino")
    (sketch / "lab_build.h").write_text(
        f'#pragma once\n#include <{header}>\n#define KWS_RELEASE "{release}"\n'
        f'#define KWS_EXPORT_SHA256 "{digest}"\n',
        encoding="utf-8", newline="\n",
    )
    print(f"Export : {digest}\nSketch : {sketch.relative_to(ROOT)}", flush=True)
    subprocess.run(["bash", str(ROOT / "scripts/compile.sh"), str(sketch), "--library", str(library)],
                   cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--release", required=True)
    args = parser.parse_args()
    try:
        build(args.archive, args.release)
    except (PipelineError, OSError, subprocess.CalledProcessError) as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
