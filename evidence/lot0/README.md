# Preuves Lot 0 — mesures réelles

Toutes les données de ce dossier proviennent de la carte de référence. Aucune n'est simulée.

| Élément | Valeur |
|---|---|
| Carte | Arduino Nano 33 BLE Sense **originale** (LSM9DS1), identifiée par `tutorials/02-arduino-nano/sketches/board_identify` |
| Hôte | macOS 15.6 (24G84), Apple M4 |
| Outils | arduino-cli 1.5.1, core `arduino:mbed_nano` 4.6.0, Arduino_LSM9DS1 1.1.1, pyserial 3.5, Python 3.12.7 |
| Firmware | `imu_rate.ino` (diagnostic : `seq,t_us,ax_g,ay_g,az_g`, lecture sur `accelerationAvailable()`) |
| Date | 23/11/2026 |

## E3 — `lot0-e3-macos15.6-original.csv`

- Capture de 120 s par pyserial à 115200 bauds.
- SHA-256 : `1576a42d00a2aff60ea58c29e7aa39220aa2f93758073e8cbfdd387df7898f38`.
- Consigne donnée à l'enseignant : 6 orientations, puis un mouvement gauche-droite, puis des tapotements.
- Analyse : `python3 analyze_e3.py lot0-e3-macos15.6-original.csv figure.png`. La figure est désactivée si matplotlib est inutilisable.

Résultats :

- **Intégrité.** 13 889 échantillons sur 119,5 s, aucun trou de `seq`, `t_us` strictement croissant. Cadence médiane 114,22 Hz, moyenne 116,25 Hz, intervalle maximal 9,1 ms.
- **Orientations stables.** On observe +X (≈ +0,98 g), −X incliné (−0,88 g), +Z (+0,967 g) et −Z (−1,00 à −1,03 g). **Aucune orientation ±Y n'apparaît**, et **le mouvement gauche-droite n'est pas visible** dans l'enregistrement (8,7 s de mouvement au total, toutes des transitions). Ces deux points sont à refaire.
- **Tapotements.** Entre 50 et 61 s, carte à plat, on mesure des pics |Δa| de 0,09 à 0,26 g sur Z, environ 2 par seconde. L'écart-type par seconde ne dépasse pas 0,03 g. Les tapotements sont donc visibles en crête mais faibles en RMS.
- **Bruit au repos.** Entre 62 et 119 s, l'écart-type par seconde est ≤ 0,001 g sur chaque axe.
- **Calibration Z.** Elle est grossière : +0,967 g et −1,005 g, ce qui donne un offset ≈ −0,019 g et un gain ≈ 0,986. Elle reste indicative, car les orientations n'étaient pas parfaitement verticales.
