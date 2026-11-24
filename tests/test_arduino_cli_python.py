"""Le code Python ne doit pas lancer de script .sh : Windows ne sait pas l'exécuter (WinError 193).

Constaté le 2026-11-24 : `release flash` plantait sous Windows avant tout téléversement.
"""
import re
from pathlib import Path

import pytest

from tinyml2027 import release

ROOT = Path(__file__).resolve().parents[1]


def test_no_shell_script_launched_from_python():
    bad = []
    for f in sorted([*(ROOT / "src").rglob("*.py"), *(ROOT / "python").rglob("*.py")]):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"scripts/\w+\.sh", line) and not line.lstrip().startswith("#") \
                    and ("subprocess" in line or "[str(ROOT" in line):
                bad.append(f"{f.relative_to(ROOT)}:{i}")
    assert not bad, bad


def test_arduino_cli_runs_without_bash():
    exe = ROOT / ".arduino/bin"
    if not exe.exists():
        pytest.skip("arduino-cli non installé (./scripts/setup.sh)")
    r = release.arduino_cli("version")
    assert r.returncode == 0, r.stderr
    assert "arduino-cli" in r.stdout.lower()
