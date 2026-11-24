"""Code Python partagé par les tutoriels et TP TinyML2027."""

__version__ = "0.1.0"

import os as _os

# Les messages internes de TensorFlow (journaux C++, avertissements MLIR) noient les
# résultats des TP. On les masque par défaut ; TINYML_VERBOSE=1 les réaffiche.
if not _os.environ.get("TINYML_VERBOSE"):
    _os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import sys as _sys

# Windows : quand la sortie n'est pas une console Windows (Git Bash/mintty, tube, fichier),
# Python écrit en cp1252 et les accents s'affichent mal (« fen▒tres »). On force l'UTF-8.
for _stream in (_sys.stdout, _sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass
