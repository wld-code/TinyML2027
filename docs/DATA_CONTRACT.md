# Contrat de données et de modèle — référence à implémenter et vérifier

Le contrat est **une proposition pédagogique initiale**, fondée sur le Lab 7–8 du livre. Toute modification de définition de feature doit provoquer une régénération du dataset, un nouvel entraînement, une nouvelle quantification et de nouveaux tests embarqués.

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

## Fenêtrage
Longueur proposée : `256` échantillons; pas `128` (50 % de recouvrement). Attention : une fenêtre de 256 échantillons a une durée égale à 256 / fs en première approximation, par exemple 5.12 s à 50 Hz; la durée exacte de couverture entre le premier et le dernier échantillon vaut (255/fs) pour une cadence régulière. Mesurer fs, puis vérifier la pertinence des fenêtres pour les gestes enregistrés.

## Caractéristiques de référence
Calculer sur l'axe `ax_g` : `rms_g`, `crest_factor`, `dominant_hz`, `band_power_g2`. Valeurs, traitement DC, bornes de fréquence, PSD, fenêtrage et cas RMS = 0 sont définis dans `AIoT-Book/labs/ch07-08-acceleration-features/analysis/lab78.py` et doivent être figés dans un contrat explicite et reproduits **bit à bit ou à tolérance documentée** en C++ : vérifier la faisabilité du calcul spectral à bord et les ressources utilisées, ou simplifier de façon déclarée **avant** l'entraînement.
Ne pas appliquer un filtrage différent au moment de l'inférence; le filtre de visualisation du Lab 7–8 n'est pas nécessairement utilisé pour les features.

## Modèle et ensembles
Les partitions doivent être réalisées par `session_id`, **avant** apprentissage de normalisation, imputation, calibration ou sélection. Proposer un split par exemple 4 sessions train, 1 validation, 1 test; ne jamais disperser les fenêtres voisines d'une même session entre partitions. Réserver le test jusqu'à la validation de l'architecture.
Comparer dummy, régression logistique et réseau dense compact, par exemple 4 entrées → 8 neurones → 3 sorties, en expliquant l'arbitrage taille/précision. Classes dans l'ordre `stationary,periodic,impact`.

## Artefacts exportés
- `features.csv`, `splits.csv`, `metrics.json`, matrice de confusion, courbes
- `model_fp32.tflite`, `model_int8.tflite`
- `preprocessing.json` (ordre des features, normalisation, valeurs d'imputation et unités)
- `labels.json` (ordre strict), `training_config.json` (seed, versions et splits)
- `calibration_train.npy` issu exclusivement de train
- `golden_vectors.npz` avec entrées brutes, features, valeurs normalisées, codes int8, scores
- `model_int8.h`, `release_manifest.json` avec SHA-256, versions et cibles
Les artefacts générés restent ignorés par git par défaut, sauf petits exemples de référence explicitement autorisés.

## Vérifications obligatoires
- Séquences et timestamps croissants, cadence plausible, aucune valeur manquante utilisée sans décision explicite.
- Aucun chevauchement de sessions entre train/validation/test.
- Dimensions et ordre des entrées/sorties identiques entre Python, LiteRT et C++.
- Comparaison FP32/INT8 sur exemples appariés, attention aux erreurs dues aux scales/zero-points.
- Comparaison des caractéristiques Python/C++ sur signaux connus, **avant** test live.
- Les prédictions des classes inconnues ne doivent pas être présentées comme des certitudes.
