# Rapport qualité TP01

Généré par `python -m tinyml2027.build_features`. Fenêtres de 256 échantillons, pas de 128, axe ax_g.

## Enregistrements

| recording_id | session_id | condition | source | echantillons | fs_mesuree_hz | lacunes | fenetres | fenetres_valides | retenu |
|---|---|---|---|---|---|---|---|---|---|
| s01_stationary_t01 | s01 | stationary | hardware | 2315 | 116.2 | 0 | 17 | 17 | oui |
| s01_periodic_t01 | s01 | periodic | hardware | 2315 | 116.3 | 0 | 17 | 17 | oui |
| s01_impact_t01 | s01 | impact | hardware | 2315 | 116.2 | 0 | 17 | 17 | oui |
| s02_stationary_t01 | s02 | stationary | hardware | 2315 | 116.2 | 0 | 17 | 17 | oui |
| s02_periodic_t01 | s02 | periodic | hardware | 2315 | 116.3 | 0 | 17 | 17 | oui |
| s02_impact_t01 | s02 | impact | hardware | 2315 | 116.2 | 0 | 17 | 17 | oui |
| s03_stationary_t01 | s03 | stationary | hardware | 2315 | 116.2 | 0 | 17 | 17 | oui |
| s03_periodic_t01 | s03 | periodic | hardware | 2315 | 116.2 | 0 | 17 | 17 | oui |
| s03_impact_t01 | s03 | impact | hardware | 2315 | 116.3 | 0 | 17 | 17 | oui |
| s04_stationary_t01 | s04 | stationary | hardware | 2315 | 116.2 | 0 | 17 | 17 | oui |
| s04_periodic_t01 | s04 | periodic | hardware | 2315 | 116.1 | 0 | 17 | 17 | oui |
| s04_impact_t01 | s04 | impact | hardware | 2315 | 116.2 | 0 | 17 | 17 | oui |
| s05_stationary_t01 | s05 | stationary | hardware | 2315 | 116.2 | 0 | 17 | 17 | oui |
| s05_periodic_t01 | s05 | periodic | hardware | 2315 | 116.2 | 0 | 17 | 17 | oui |
| s05_impact_t01 | s05 | impact | hardware | 2315 | 116.2 | 0 | 17 | 17 | oui |

## Fenêtres valides par session et condition

| session_id | impact | periodic | stationary |
|---|---|---|---|
| s01 | 17 | 17 | 17 |
| s02 | 17 | 17 | 17 |
| s03 | 17 | 17 | 17 |
| s04 | 17 | 17 | 17 |
| s05 | 17 | 17 | 17 |

## Médianes des caractéristiques par condition (fenêtres valides)

| condition | rms_g | crest_factor | dominant_hz | band_power_g2 |
|---|---|---|---|---|
| impact | 0.004083 | 6.037 | 7.72 | 2.858e-06 |
| periodic | 0.06284 | 2.918 | 0.9082 | 0.002681 |
| stationary | 0.0006447 | 3.217 | 8.174 | 8.393e-08 |

Fenêtres invalides écartées : 0. Fenêtres à pic spectral ambigu : 0. Fenêtres à RMS nulle : 0.

