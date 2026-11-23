# Contrat de données et de modèle — référence à implémenter et vérifier

**Version 0.3 (23/11/2026).** Le contrat est **une proposition pédagogique**, fondée sur le Lab 7–8 du livre. Toute modification de définition de feature doit provoquer une régénération du dataset, un nouvel entraînement, une nouvelle quantification et de nouveaux tests embarqués.

## Enregistrement brut
Chaque capture est associée à un `recording_id` unique et à un `session_id`. Un fichier CSV par enregistrement :
```csv
seq,t_us,ax_g,ay_g,az_g
0,0,0.01,-0.02,1.01
1,10000,0.02,-0.01,0.99
```
**Exemple purement illustratif, non mesuré.** `seq` est monotone et sans duplication, `t_us` correspond au temps d'échantillonnage côté carte, les accélérations sont en g. Pour ne pas masquer les pertes, la cadence doit être évaluée à partir de ces marqueurs, et non supposée égale à une fréquence nominale. Les données sont rejetées ou explicitement marquées invalides si cadence, timestamp ou séquence échouent; aucune interpolation silencieuse.

`manifest.csv` : `recording_id,session_id,condition,trial,board_revision,board_id,source,requested_fs_hz,measured_fs_hz,valid,notes`. `source` est `hardware` ou `simulated`. Un fichier de métadonnées JSON optionnel peut documenter OS, firmware, version du protocole, opérateur et paramètres de capture. Les données personnelles restent locales; ne pas enregistrer nom/voix ni identifiant durable de l'étudiant par défaut.

## Classes et protocole
`stationary`, `periodic`, `impact`. Préparer au minimum plusieurs sessions **indépendantes**, chacune contenant toutes les classes. Repositionner la carte et varier modérément le protocole entre sessions pour tester la généralisation; documenter les conditions. Les fenêtres proches d'une transition ne reçoivent pas automatiquement le label du fichier si le contenu est ambigu.

## Fenêtrage et cadence (décision validée le 23/11/2026)
- **Cadence native, sans réglage de registre.** Carte originale : ODR 119 Hz nominal, 114,2 Hz médian mesuré (`evidence/lot0`). Rev2 : 100 Hz nominal (bibliothèque), à mesurer. La cible de 50 Hz est abandonnée. Le manifest enregistre `requested_fs_hz` (ODR nominale) et `measured_fs_hz`.
- Fenêtre `N = 256` échantillons, pas `128` (50 % de recouvrement). Durée ≈ 2,2 s (originale) et 2,6 s (Rev2).
- **Fréquence d'échantillonnage par fenêtre**, calculée de façon identique en Python et en C++ :
  `fs_win = (N − 1) / ((t_us[N−1] − t_us[0]) · 10⁻⁶)`, en Hz.
- **Validité d'une fenêtre** : `seq` strictement consécutif, `t_us` strictement croissant, et aucun intervalle `> 1,5 ×` la médiane des intervalles de la fenêtre. Une fenêtre invalide est marquée, jamais interpolée.
- Un modèle est entraîné et validé pour une révision donnée. Le transfert entre révisions n'est pas garanti et doit être mesuré.

## Caractéristiques de référence (décision validée le 23/11/2026)
Axe `ax_g`, fenêtre valide de N = 256 échantillons `x[n]` en g, `fs = fs_win`.

1. Centrage : `c[n] = x[n] − mean(x)`.
2. `rms_g = sqrt(mean(c²))` (g).
3. `crest_factor = max|c| / rms_g`. **Si `rms_g < 1e−6 g`**, l'indicateur `rms_zero = 1` est levé et `crest_factor = dominant_hz = band_power_g2 = 0`. Pas de NaN dans le contrat embarqué. *Changement v0.3 :* le seuil v0.2 (1e−9 g) était inférieur au résidu d'arrondi float32 du centrage (7·10⁻⁹ g mesuré sur une fenêtre constante par le test hôte `tests/test_features_cpp.py`) : Python donnait crest = 0, le C++ crest = 1. 1e−6 g reste 100 fois sous la résolution du LSM9DS1 (1,2·10⁻⁴ g).
4. PSD une face, à un seul segment, fenêtre de Hann périodique `w[n] = 0,5 − 0,5·cos(2πn/N)` :
   `X[k] = Σ c[n]·w[n]·e^(−2iπkn/N)`, puis `P[k] = a_k·|X[k]|² / (fs·Σw²)` en g²/Hz, avec `a_k = 1` pour k = 0 et k = N/2, et `a_k = 2` sinon.
   Fréquences : `f[k] = k·fs/N`. Cette formule est équivalente à `scipy.signal.welch(c, fs, window="hann", nperseg=N, scaling="density")`, ce qui doit être vérifié par un test à 1e−12 près.
5. Bande `B = {k : 0,5 Hz ≤ f[k] ≤ 10 Hz}`.
6. `dominant_hz = f[argmax_{k∈B} P[k]]`. En cas d'égalité, on prend le **plus petit indice**.
7. `band_power_g2 = Σ_{k∈B} P[k] · fs/N` (g²).

**Tolérances Python (float64) / C++ (float32)** sur les golden vectors :
- `rms_g`, `crest_factor` et `band_power_g2` : erreur relative ≤ 1e−4 (à confirmer par l'essai E6) ;
- `dominant_hz` : au plus 1 bin d'écart.
On compte les fenêtres « ambiguës », dont les deux plus grands bins de B diffèrent de moins de 1e−4 en relatif.

Implémentation embarquée : FFT radix-2 de 256 points en float32, écrite pour le cours (`labs/03-embedded-inference/firmware/infer_nano/features.h`), plutôt que la kissfft de la bibliothèque TFLM, compilée en virgule fixe pour le micro-frontend audio. Parité vérifiée d'abord sur le poste (`tests/test_features_cpp.py`), puis sur la carte (mode REPLAY du firmware).
Ne pas appliquer de filtrage différent au moment de l'inférence : le filtre de visualisation du TP01 n'entre pas dans les features.

## Protocole `impact` (décision validée le 23/11/2026)
Tapotements doux et **réguliers pendant tout l'enregistrement**, environ 1 à 2 par seconde, sur la table à côté de la carte, sans frapper la carte. Lors de l'essai E3, ils ont donné des pics |Δa| de 0,09 à 0,26 g. Cette consigne évite les fenêtres sans aucun impact mais étiquetées `impact`. L'étiquetage par fenêtre fondé sur un détecteur d'événement reste une question d'interprétation.

## Modèle et ensembles
Les partitions doivent être réalisées par `session_id`, **avant** apprentissage de normalisation, imputation, calibration ou sélection. Parcours de référence (décision du 23/11/2026, 3 sessions) : 2 sessions d'entraînement, 1 session de test. La sélection de modèle se fait par validation croisée « une session laissée de côté » sur les sessions d'entraînement. Avec plus de sessions, le même code accepte N sessions d'entraînement. Ne jamais disperser les fenêtres voisines d'une même session entre partitions. Réserver le test jusqu'à la validation de l'architecture.

**Prétraitement des entrées du réseau** (appris sur le train uniquement, `preprocessing.json`) : `log10(rms_g + 1e−6)`, `crest_factor`, `dominant_hz`, `log10(band_power_g2 + 1e−12)`, puis standardisation (moyenne et écart-type du train). Le passage en log10 ramène rms et band power, étalés sur 4 à 5 ordres de grandeur, à une échelle comparable aux deux autres entrées.
Comparer dummy, régression logistique et réseau dense compact, par exemple 4 entrées → 8 neurones → 3 sorties, en expliquant l'arbitrage taille/précision. Classes dans l'ordre `stationary,periodic,impact`.

## Artefacts exportés
- `features.csv`, `splits.csv`, `metrics.json`, matrice de confusion, courbes
- `model_fp32.tflite`, `model_int8.tflite`
- `preprocessing.json` (ordre des features, normalisation, valeurs d'imputation et unités)
- `labels.json` (ordre strict), `training_config.json` (seed, versions et splits)
- `calibration_train.npy` issu exclusivement de train
- `golden_vectors.npz` avec entrées brutes, features, valeurs normalisées, codes int8 et scores. Les sorties INT8 de LiteRT desktop ne sont pas forcément bit-exactes avec TFLM (écart de 2 LSB mesuré, voir AUDIT §11.4) : la tolérance de parité sera fixée et justifiée au TP03 à partir de mesures sur la carte
- `model_int8.h`, `release_manifest.json` avec SHA-256, versions et cibles
Les artefacts générés restent ignorés par git par défaut, sauf petits exemples de référence explicitement autorisés.

## Vérifications obligatoires
- Séquences et timestamps croissants, cadence plausible, aucune valeur manquante utilisée sans décision explicite.
- Aucun chevauchement de sessions entre train/validation/test.
- Dimensions et ordre des entrées/sorties identiques entre Python, LiteRT et C++.
- Comparaison FP32/INT8 sur exemples appariés, attention aux erreurs dues aux scales/zero-points.
- Comparaison des caractéristiques Python/C++ sur signaux connus, **avant** test live.
- Les prédictions des classes inconnues ne doivent pas être présentées comme des certitudes.
