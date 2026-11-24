"""Tout fichier texte doit être lu/écrit en UTF-8 explicite.

Sans `encoding=`, Python utilise l'encodage local : cp1252 sous Windows.
Les en-têtes générés (`model_data.h`, `golden.h`…) y étaient alors réécrits
avec des accents corrompus, et un caractère hors cp1252 (`→`, `≤`) faisait
échouer l'écriture (constaté le 2026-11-24, evidence/windows/).
Les écritures imposent aussi `newline="\\n"` : mêmes octets sur les 3 OS.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRS = ["python", "src", "tests"]


def _calls():
    for d in DIRS:
        for f in sorted((ROOT / d).rglob("*.py")):
            tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    yield f.relative_to(ROOT), node


def _kw(node, name):
    return any(k.arg == name for k in node.keywords)


def _binary_open(node):
    mode = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == "mode"), None)
    return isinstance(mode, ast.Constant) and isinstance(mode.value, str) and "b" in mode.value


def test_text_io_is_explicit_utf8():
    bad = []
    for path, node in _calls():
        name = node.func.attr
        if name in ("read_text", "write_text") and not _kw(node, "encoding"):
            bad.append(f"{path}:{node.lineno} {name} sans encoding=")
        if name == "write_text" and not _kw(node, "newline"):
            bad.append(f'{path}:{node.lineno} write_text sans newline="\\n"')
        if name == "open" and isinstance(node.func.value, (ast.Name, ast.Attribute, ast.Call)) \
                and not (isinstance(node.func.value, ast.Name) and node.func.value.id == "os") \
                and not _binary_open(node) and not _kw(node, "encoding"):
            bad.append(f"{path}:{node.lineno} .open() texte sans encoding=")
    assert not bad, "\n".join(bad)
