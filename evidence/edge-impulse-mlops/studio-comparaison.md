# Comparaison KWS v1 et v2 dans Studio

Exécutée sur le projet personnel privé 1173087, depuis macOS. v1 correspond à l’impulse 1 et v2 à l’impulse 2. Les deux résultats sont quantifiés INT8 avec le seuil de confiance 0,6. Le clone a reçu 300 clips correctifs supplémentaires, pour un total de 900 fenêtres. Les 300 clips de promotion proviennent du même manifeste pour les deux expériences. Les clips finaux sont conservés hors Studio.

| Condition | Mesure | v1 | v2 |
|---|---|---:|---:|
| Propre | Accuracy | 13,33 % | 19,33 % |
| Propre | Macro-F1 | 0,207 | 0,270 |
| Propre | Rappel `go` | 0 % | 0 % |
| Propre | Rappel `stop` | 28 % | 48 % |
| Dégradée | Accuracy | 10,67 % | 10,67 % |
| Dégradée | Macro-F1 | 0,165 | 0,175 |
| Dégradée | Rappel `go` | 2 % | 2 % |
| Dégradée | Rappel `stop` | 8 % | 18 % |

Les faux déclenchements sur `bruit` sont à 4 % et 2 % pour v1 (propre et dégradée), puis à 2 % et 4 % pour v2. Les réponses incertaines sont respectivement 124 et 123 pour v1, puis 118 et 125 pour v2, sur 150 clips par condition. Le gain de macro-F1 en condition dégradée est d’environ 0,95 point. Le candidat échoue aux seuils définis pour l’accuracy propre, le rappel des commandes et le gain en condition dégradée. Il reste un candidat de travail.

Les deux réponses brutes de l’API Studio sont archivées localement sous `artifacts/edge-impulse-mlops/`. La commande `score_studio.py` joint les 300 prédictions de chaque expérience au manifeste et produit les [métriques v1](kws-v1-promotion.json) et [v2](kws-v2-promotion.json). Le total des prédictions correctes concorde avec l’accuracy agrégée affichée par Studio (36/300 et 45/300).

Les deux ZIP Arduino EON INT8 ont été téléchargés et contrôlés avec `unzip -t`. SHA-256 v1 `329671a8ac84d60805e89c284ea9b8f9ce6ee9a8e2eb294b4cd8fc73554919ba`, v2 `8c8efa54d34e1d97e66065112c8da583c6ba565c0ce72b00aa5a5ec45a2642ed`. La compilation du futur firmware et le test matériel restent à faire.
