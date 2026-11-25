# Référence KWS v1 dans Edge Impulse Studio

Essai exécuté depuis macOS avec le projet personnel privé `TinyML2027 - Edge MLOps` (identifiant 1173087), impulse 1, bloc DSP 2 et bloc d’apprentissage 3. La cible affichée dans Studio était Arduino Nano 33 BLE Sense (Cortex-M4F 64MHz).

- L’import Studio a confirmé 600 fichiers Training et 300 fichiers Test, avec zéro échec pour chaque lot. L’option d’inférence du label par nom de fichier était sélectionnée.
- Training contient `train-v1`. Test contient `evaluation-clean` et `evaluation-shifted`. Les clips `final-*` restent locaux.
- Studio a affiché 600 fenêtres d’entraînement et les trois classes `bruit`, `go` et `stop`.
- Fenêtre 1 000 ms, pas 500 ms, 16 kHz. MFCC avec 13 coefficients, 32 filtres, trames et pas de 20 ms, FFT de 256 points, préaccentuation de coefficient 0,98.
- Classifieur 1D avec 8 puis 16 filtres de largeur 3. CPU, 100 cycles, taux 0,0001, validation interne de 20 %, taille de lot 32 affichée, profilage INT8 activé, augmentation native désactivée.

Le SHA-256 du manifeste est consigné dans [dataset-report.json](dataset-report.json).

## Évaluation Studio sur les 300 clips de promotion

L’entraînement Studio s’est terminé. Après sélection de **Test 'Quantized (int8)' model** et **Classify all**, la vue **Results → Quantized (int8)** affiche une accuracy de **12,00 %**. La matrice de confusion regroupe les conditions propre et dégradée. Chaque ligne représente 100 clips.

| Réel / prédit | bruit | go | stop | uncertain |
|---|---:|---:|---:|---:|
| bruit | 17 | 0 | 3 | 80 |
| go | 5 | 1 | 2 | 92 |
| stop | 7 | 0 | 18 | 75 |

Il y a 36 prédictions correctes et 247 réponses `uncertain`. Ces résultats décrivent la référence sur le lot de promotion et le seuil Studio utilisé. Ils ne quantifient pas à eux seuls l’écart propre/dégradé.

## Export local

Studio a produit une bibliothèque **Arduino library**, **EON Compiler**, **Quantized (int8)**. Le ZIP téléchargé fait 5 247 142 octets et son intégrité ZIP a été vérifiée. L’archive locale `artifacts/edge-impulse-mlops/kws-v1/arduino-int8.zip` a pour SHA-256 `329671a8ac84d60805e89c284ea9b8f9ce6ee9a8e2eb294b4cd8fc73554919ba`.

Les seuils du candidat ont été consignés après ce premier résultat et avant son entraînement. Les valeurs proposées ont été conservées. Les faux déclenchements sont les clips `bruit` classés `go` ou `stop`, rapportés au nombre de clips `bruit`, séparément dans chaque condition. Les réponses incertaines comptent comme des erreurs de reconnaissance.
