# Tailles des firmwares : macOS, Windows et Linux

Tous les croquis du cours compilés le 24/11/2026 sur le Mac de référence (macOS 15.6, Apple Silicon), au commit 7e2e463, pour la carte originale et pour la Rev2. Même chaîne partout : `arduino:mbed_nano` 4.6.0, compilateur `arm-none-eabi-gcc` 7-2017q4.

- Script : [`compile_all.sh`](compile_all.sh) (`bash evidence/compilation/compile_all.sh sortie.tsv`)
- Résultat brut : [`tailles-macos15.6-2026-11-24.tsv`](tailles-macos15.6-2026-11-24.tsv). **16 compilations sur 16 OK.**
- Windows 10 : journaux de [`evidence/windows/`](../windows/). Linux : journaux de [`evidence/linux/`](../linux/).

## Flash, en octets

| Croquis | macOS originale | Windows originale | macOS Rev2 | Windows Rev2 |
|---|---|---|---|---|
| `examples/01_blink` | 85 504 | 85 544 | 85 504 | — |
| `board_identify` | 93 224 | 93 264 | 93 224 | — |
| `examples/03_custom_model` | 142 464 | 142 552 | 142 464 | — |
| `examples/04_imu` | 95 384 | 95 416 | 116 408 | 116 448 |
| `examples/05_int8_model` | 142 136 | — | 142 136 | — |
| `imu_capture` (TP01) | 95 768 | 95 800 | 116 728 | 116 768 |
| `infer_nano` (TP03, 8 golden vectors) | **183 968** | **184 088** | **204 912** | — |
| `mic_check` | 88 136 | 88 168 | 88 136 | — |

La RAM statique est identique sur les deux systèmes, pour chaque croquis compilé des deux côtés (par exemple `infer_nano` : 61 792 octets, Rev2 : 62 448).

## Ce qu'on en retient

- **Windows donne 32 à 120 octets de plus que macOS, toujours.** L'écart est petit et stable. Cause probable, non vérifiée : les chemins de fichiers, plus longs sous Windows, sont inscrits dans le binaire.
- **Seuls les croquis qui lisent l'IMU grossissent en Rev2** (environ +21 000 octets : bibliothèque BMI270_BMM150 au lieu de LSM9DS1). Les autres sont identiques.
- **L'écart Linux est expliqué.** Le test Linux du 23/11 donnait 171 152 octets pour `infer_nano`. Son journal ([`TP03_int8_cpp_firmware.log`](../linux/TP03_int8_cpp_firmware.log)) indique « 2 golden vectors » : dans un clone neuf, `quantize_motion` lisait par défaut `data/` (dossier des captures de l'étudiant, absent du dépôt) et n'écrivait que les 2 cas synthétiques, sans erreur. Windows a reproduit le même cas (171 504 octets avec 2 vecteurs, 184 088 avec 8). Depuis le commit 021a003, `quantize_motion` s'arrête avec un message clair dans ce cas.
- Ne pas comparer : `infer_nano` Rev2 sous Windows (192 472 octets) a été compilé avant ce correctif, avec 2 golden vectors seulement.

Compiler n'est pas tester : la Rev2 reste **compilée seulement**, aucune carte Rev2 n'a été essayée.
