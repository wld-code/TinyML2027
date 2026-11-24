# Contrat de données et de modèle

**Version 0.3 (23/11/2026).** Ce document définit exactement ce que Python et la carte doivent calculer. Python (`src/tinyml2027/features.py`) et le firmware (`labs/03-embedded-inference/firmware/infer_nano/features.h`) l'implémentent tous deux. Toute modification d'une définition oblige à refaire les features, l'entraînement, la quantification et le rejeu sur la carte.

## 1. Enregistrement brut

Un fichier CSV par enregistrement :

```csv
seq,t_us,ax_g,ay_g,az_g
```

*(Format seulement ; les valeurs réelles sont dans `datasets/motion-nano-v1/raw/`.)*

| Colonne | Sens |
|---|---|
| `seq` | numéro de la mesure, croissant, sans doublon |
| `t_us` | instant de la mesure sur la carte (µs) |
| `ax_g`, `ay_g`, `az_g` | accélération (g) |

La cadence est **mesurée** à partir de `seq` et `t_us`, jamais supposée. Une mesure perdue n'est jamais interpolée : l'enregistrement ou la fenêtre est marqué invalide.

`manifest.csv` : `recording_id,session_id,condition,trial,board_revision,board_id,source,requested_fs_hz,measured_fs_hz,valid,notes`. `source` vaut `hardware` ou `simulated`. Aucune donnée personnelle (nom, voix, identifiant durable) n'est enregistrée.

## 2. Classes et protocole

Trois classes, dans cet ordre : `stationary`, `periodic`, `impact`. Chaque session contient les trois. Entre deux sessions, la carte est déplacée et les gestes varient un peu.

- `stationary` : carte posée, personne ne la touche.
- `periodic` : glisser la carte dans le sens du câble, environ 1 aller-retour par seconde.
- `impact` : tapoter la table à côté de la carte, 1 à 2 fois par seconde, **pendant tout l'enregistrement** ; ne jamais frapper la carte.

## 3. Fenêtres

- Cadence native du capteur, sans réglage de registre : 119 Hz annoncés sur la carte originale (≈ 116 Hz mesurés), 100 Hz annoncés sur la Rev2 (non mesuré).
- Fenêtre de **N = 256** mesures, pas de **128** (recouvrement de 50 %).
- Cadence de chaque fenêtre, calculée de la même façon en Python et en C++ :
  `fs_win = (N − 1) / ((t_us[N−1] − t_us[0]) · 10⁻⁶)` Hz.
- Une fenêtre est **valide** si `seq` est consécutif, `t_us` strictement croissant, et aucun intervalle ne dépasse 1,5 fois la médiane de la fenêtre.
- Un modèle est entraîné pour une révision de carte. Le passage à l'autre révision doit être mesuré.

## 4. Les 4 features

Sur l'axe `ax_g` d'une fenêtre valide, x[n] en g, n = 0 … 255, fs = fs_win.

1. Centrage : `c[n] = x[n] − moyenne(x)`.
2. `rms_g = √(moyenne(c²))` (g).
3. `crest_factor = max|c| / rms_g`. **Si `rms_g < 10⁻⁶ g`**, alors `crest_factor = dominant_hz = band_power_g2 = 0` (pas de NaN).
4. Densité spectrale, un seul segment, fenêtre de Hann périodique `w[n] = 0,5 − 0,5·cos(2πn/N)` :
   `X[k] = Σ c[n]·w[n]·e^(−2iπkn/N)`, puis `P[k] = a_k·|X[k]|² / (fs·Σw²)` en g²/Hz, avec `a_k = 1` pour k = 0 et k = N/2, `a_k = 2` sinon. Fréquences : `f[k] = k·fs/N`.
   C'est l'équivalent de `scipy.signal.welch(c, fs, window="hann", nperseg=N, scaling="density")` ; un test le vérifie à 10⁻¹² près.
5. Bande `B = {k : 0,5 Hz ≤ f[k] ≤ 10 Hz}`.
6. `dominant_hz = f[argmax P[k]]` sur B ; en cas d'égalité, le plus petit indice.
7. `band_power_g2 = Σ P[k] · fs/N` sur B (g²).

**Pourquoi 10⁻⁶ g (v0.3) ?** Le seuil de la v0.2 (10⁻⁹ g) était sous le résidu d'arrondi du float32 : sur une fenêtre constante, le C++ trouvait 7·10⁻⁹ g et Python 0. 10⁻⁶ g reste 100 fois sous la résolution du LSM9DS1.

Sur la carte, la FFT est la **kissfft** livrée avec la bibliothèque officielle `Arduino_TensorFlowLite`, compilée en float32.

## 5. Entrées du réseau

Appris **sur l'entraînement seul** et enregistrés dans `preprocessing.json` :

1. `log10(rms_g + 10⁻⁶)`, `crest_factor`, `dominant_hz`, `log10(band_power_g2 + 10⁻¹²)` ;
2. puis standardisation : (valeur − moyenne) / écart-type de l'entraînement.

## 6. Entraînement et évaluation

- Séparation **par session**, avant toute normalisation, calibration ou sélection de modèle. Les fenêtres d'une même session restent ensemble.
- Choix du modèle par validation croisée « une session de côté » sur les sessions d'entraînement.
- Une session de test, regardée **une seule fois** à la fin. Parcours de référence : s01 à s04 pour l'entraînement, s05 pour le test.
- Comparaison obligatoire avec la classe majoritaire et une régression logistique.

## 7. Fichiers exportés

| Fichier | Contenu |
|---|---|
| `features.csv` | une ligne par fenêtre |
| `metrics.json`, `test_predictions.csv` | scores et prédictions |
| `model_fp32.tflite`, `model_int8.tflite` | le modèle |
| `preprocessing.json`, `labels.json` | entrées et ordre des classes |
| `calibration_train.npy` | données de calibration INT8, issues de l'entraînement seul |
| `golden_vectors.npz` | fenêtres brutes, features, codes int8 et scores attendus |
| `release_manifest.json` | versions, cibles et SHA-256 |

## 8. Tolérances carte / Python

Fixées avant l'essai sur la carte (TP03) :

| Grandeur | Tolérance |
|---|---|
| `rms_g`, `crest_factor`, `band_power_g2` | 10⁻⁴ en relatif |
| `dominant_hz` | 1 case de fréquence |
| codes int8 d'entrée | 1 cran |
| codes int8 de sortie | 2 crans |
| classe prédite | identique |

Les sorties INT8 de LiteRT (ordinateur) et de TFLM (carte) peuvent différer de quelques crans : les golden vectors utilisent donc TFLM comme référence.
