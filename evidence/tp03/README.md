# TP03 — inférence de mouvements sur la Nano : validé sur matériel

**Date :** 23/11/2026. **Poste :** macOS 15.6 (Apple Silicon). **Carte :** Nano 33 BLE Sense V1 (LSM9DS1).
**Chaîne :** Arduino CLI 1.5.1, mbed_nano 4.6.0, Arduino_TensorFlowLite `7948b85e` (kissfft incluse), Arduino_LSM9DS1 1.1.1.
**Modèle :** `motion-v1`, INT8, SHA-256 `023e01b8d61b1f962f30a660ff1528a50a8716862fec1f1b459b377944db2879` (annoncé par la carte au démarrage). Entraînement sur s01 à s04, test sur s05.

| Étape | Résultat | Statut |
|---|---|---|
| Compilation, carte originale | 183 872 octets de Flash (18 %), 61 792 octets de RAM statique (23 %), voir `tp03-infer_nano-compile-original.log` | compilé |
| Compilation, Rev2 (`REV=rev2`) | voir `tp03-infer_nano-compile-rev2.log` | **compilé seulement** (pas de carte Rev2) |
| Parité des features C++/Python sur le Mac | `tests/test_features_cpp.py` : réussi | testé (hôte) |
| Rejeu des 8 golden vectors sur la carte | 8/8 OK ; 0 cran d'écart en entrée et en sortie ; features ≤ 668 µs ; `Invoke()` ≤ 108 µs ; arena 788/4096 octets (`tp03-replay-macos15.6-v1.txt`) | **validé sur matériel** |
| Direct, immobile (20 s) | 17/17 « stationary » (`tp03-live-stationary-macos15.6-v1.txt`) | **validé sur matériel** |
| Direct, glisser (20 s) | 17/17 « periodic » (`tp03-live-periodic-macos15.6-v1.txt`) | **validé sur matériel** |
| Direct, tapoter (20 s) | 16/17 « impact » ; la dernière fenêtre, classée « stationary » (crest 3,3), a sans doute été prise après la fin des tapotements (`tp03-live-impact-macos15.6-v1.txt`) | **validé sur matériel** |

Pendant le test en direct, le geste était fait par l'enseignant, à la consigne donnée dans la conversation. Le journal brut de chaque essai est enregistré à partir de l'envoi de la commande `L`.
