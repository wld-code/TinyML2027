# Vérification du parcours étudiant

Contrôles effectués le 25 novembre 2026 sur macOS arm64 à partir du cache et des artefacts du lab.

- `prepare_dataset.py --out ...` a régénéré les 1 500 WAV. `cmp` a confirmé que le manifeste CSV et le rapport JSON étaient identiques aux fichiers initiaux. `plot_dataset.py --out ...` a régénéré les figures audio.
- `score_studio.py` a relu les réponses INT8 archivées. Les deux CSV obtenus sont identiques aux exports d’analyse initiaux. `pipeline.py gate` a renvoyé le code 2 pour le candidat mesuré et pour l’exercice d’injection. `pipeline.py upload corrective-v2`, en dry-run, a affiché les 300 clips sans modifier le projet.
- `release_kws.py verify` a contrôlé les deux archives. `monitor.py report --html ...` a généré le rapport acoustique à partir des six fenêtres enregistrées avec la Nano. Le p95 d’inférence est de 142,65 ms, avec trois commandes manquées et zéro faux déclenchement sur deux clips `bruit`.
- `uv run --locked pytest -q` a réussi avec 57 tests. `uv run --locked pytest -q --nbmake tutorials/01-python-jupyter` a exécuté quatre notebooks avec succès. Les liens relatifs du parcours et de ses preuves, les 24 captures, les SVG et les chemins des WAV cités ont été contrôlés.
- Les lots précédents ont établi les [résultats Studio](studio-comparaison.md), les [mesures matérielles de v1](nano-v1.md) et la [restauration USB](releases.md). Le test final indépendant reste réservé. L’installation de v2 reste bloquée par les critères. Les essais du nouveau lab sur Windows, Linux et Rev2 restent à vérifier.
