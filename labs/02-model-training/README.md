# TP02 — Concevoir et évaluer un modèle TinyML

**Statut : spécification pédagogique.** Durée cible : 4 h. Matériel : aucun supplémentaire; entrée = TP01 `features.csv` et `manifest.csv`. Dataset d'exemple clairement identifié si TP01 indisponible.

## Mission
Construire un classifieur compact `stationary`, `periodic`, `impact` sans fausser l'évaluation. Comprendre pourquoi un réseau neuronal n'est pas automatiquement meilleur qu'une méthode plus simple.

## Déroulé
1. Vérifier le contrat du TP01, nombre d'exemples, dimensions, distribution des classes, manifest, sessions et labels.
2. Démontrer par un exemple visuel pourquoi deux fenêtres chevauchantes ne doivent pas être réparties aléatoirement entre train et test.
3. Définir split par **session** (exemple 4 sessions train, 1 validation, 1 test, chacune avec les trois classes) et valider absence de fuite. Si données insuffisantes, déclarer insuffisance et utiliser référence pour l'exercice.
4. Expliciter les features `rms_g`, `crest_factor`, `dominant_hz`, `band_power_g2` avec unités et distributions.
5. Construire trois baselines : prédiction classe majoritaire (`DummyClassifier`), régression logistique, dense 4–8–3 sur entrées standardisées; rechercher taille/quantité de paramètres.
6. Calculer imputation et normalisation **sur train uniquement**. Documenter hyperparamètres, seed, nombre d'époques, early stopping et environnement reproductible.
7. Choisir le modèle sur validation; évaluer **une fois** sur session test tenue à part. Accuracy, precision, recall, macro-F1, matrice de confusion, erreurs concrètes. Ne pas retoucher après lecture test sans nouvelle campagne d'évaluation.
8. Vérifier performance par session et interroger dérive : orientation, vitesse du geste, carte Rev2 vs originale, nouvel utilisateur; pas de prétention de généralisation universelle.
9. Exporter modèle Keras, FP32 LiteRT/TFLite, scaler, labels, ordre features, paramètres, logs, golden vectors (y compris cas limites), jeu de calibration TRAIN pour TP03.
10. Mini-exercice : comparer l'effet d'une erreur de normalisation sur les prédictions; noter les limites.

## Sorties
`notebooks/01-split.ipynb`, `02-baselines.ipynb`, `03-network-evaluation.ipynb` ou scripts équivalents, mais garder une exécution CLI automatisable; `src/train.py`, `src/evaluate.py`, `src/export.py`; `artifacts/`, `figures/`, `tests/`, `results/evaluation.md`.

## Tests et critères
Session train/val/test sans overlap; dimensions et labels cohérents; outils installables sur 3 OS; métriques réellement produites; FP32 prédictions cohérentes avec source; artifact contract archivé et prêt pour TP03. Ne pas fixer un seuil artificiel de précision sans résultats empiriques.

## Source
https://github.com/wld-code/AIoT-Book/tree/main/labs/ch09-10-motion-classifier
