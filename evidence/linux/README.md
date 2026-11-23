# Parcours sans carte dans un Linux neuf — 23/11/2026

- Machine : conteneur Docker (OrbStack) sur le Mac de référence, image `ghcr.io/astral-sh/uv:python3.12-bookworm`, **Debian 12, aarch64**, `git clone` propre du dépôt (commit b53c623 + correctif de l'étape MLOps de la CI).
- Script : `parcours.sh` (mêmes étapes que `.github/workflows/ci.yml`). Résultat : `parcours-sans-carte-debian12-arm64.txt`, journaux de chaque étape à côté.
- **9/9 étapes OK** : setup.sh, 4 notebooks, tests, compilation de tous les sketches (originale et Rev2), exemples 03/05, TP01 (dataset publié), TP02, TP03 (INT8 + test C++), release MLOps build + validate.
- TP02 : test s05 accuracy 0,961, macro-F1 0,961, validation croisée 0,864 : **identiques à macOS**.
- Modèle INT8 : 2 176 octets comme sur macOS, mais SHA-256 `23685fb7…` au lieu de `023e01b8…` : l'entraînement n'est pas identique au bit près d'une machine à l'autre.
- `infer_nano` : 171 152 octets de Flash contre 183 968 sur macOS, même core 4.6.0 et même compilateur 7-2017q4 annoncé (Blink : 85 424 contre 85 504). **Écart non expliqué.**
- Limites : pas de carte (aucun port USB, téléversement, capteur), pas de x86-64 (TensorFlow exige AVX, non émulé), Debian et non Ubuntu.
