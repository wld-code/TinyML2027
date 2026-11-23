"""Code Python partagé par les tutoriels et TP TinyML2027."""

__version__ = "0.1.0"

import os as _os

# Les messages internes de TensorFlow (journaux C++, avertissements MLIR) noient les
# résultats des TP. On les masque par défaut ; TINYML_VERBOSE=1 les réaffiche.
if not _os.environ.get("TINYML_VERBOSE"):
    _os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
