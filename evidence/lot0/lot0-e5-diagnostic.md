# E5 — diagnostic de l'écart LiteRT / TFLM (23/11/2026, carte originale, macOS 15.6)

Premier essai : le sketch `tflm_smoke` comparait la carte aux sorties de LiteRT desktop.
Résultat : 7 vecteurs sur 8 identiques ; vecteur 0 : carte `85,-88,-125`, LiteRT `83,-87,-124`.

| Étape | Observation (mesurée) |
|---|---|
| Noyaux CMSIS-NN sur la carte | `85,-88,-125`, invoke 113 µs |
| Noyaux de référence TFLM sur la carte | `85,-88,-125`, invoke 233 µs : l'écart ne vient pas de CMSIS-NN |
| LiteRT desktop REF / optimisé / XNNPACK | `83,-87,-124` dans les trois cas |
| Tenseurs intermédiaires (carte vs LiteRT) | couche 1 identique ; couche 2 : logit 0 = **29** (carte) vs **28** (LiteRT) |
| Valeur exacte recalculée (acc = 7817) | 34,4977 avant point zéro (−6), donc 28,4977 |
| `MultiplyByQuantizedMultiplier` int32 (double arrondi, chemin FC par canal TFLM) | 35, soit 29, sur la carte et en Python |
| Variante int64 / arrondi simple | 34, soit 28 (comme LiteRT) |
| Runtime TFLM Python `tflite-micro==0.dev20261119010814` (Docker linux/amd64) | **8/8 identiques à la carte**, y compris `85,-88,-125` |

Conclusion : la carte est bit-exacte avec TFLM. LiteRT desktop requantifie différemment et n'est pas un oracle bit-exact pour TFLM. Le cours adopte donc :
- les golden vectors produits par `tinyml2027.tflm_oracle` (critère exact) ;
- LiteRT comme comparaison secondaire (même classe, écart ≤ 4 LSB).
