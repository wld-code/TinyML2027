# Phases 4, 5 et 7 — modèle sinus maison, FP32 puis INT8, sur la Nano

**Date :** 23/11/2026. **Poste :** macOS 15.6 (Apple Silicon). **Carte :** Arduino Nano 33 BLE Sense V1 (LSM9DS1), numéro de série USB `E011A05896DEE871`.
**Chaîne :** Arduino CLI 1.5.1, `arduino:mbed_nano@4.6.0`, Arduino_TensorFlowLite `7948b85e`, Python 3.12.7, TensorFlow 2.21.0, ai-edge-litert 2.4.0.

## Commandes exécutées

```sh
uv run python python/train.py                  # artifacts/sine/model.keras
uv run python python/convert.py --mode fp32    # artifacts/sine/model_fp32.tflite + examples/03_custom_model/*.h
uv run python python/convert.py --mode int8    # artifacts/sine/model_int8.tflite + examples/05_int8_model/*.h
./scripts/compile.sh examples/03_custom_model && ./scripts/upload.sh examples/03_custom_model
uv run python python/verify.py --mode fp32 --port /dev/cu.usbmodem314101 --log evidence/phase5/phase5-fp32-serial-macos15.6-v1.txt
./scripts/compile.sh examples/05_int8_model && ./scripts/upload.sh examples/05_int8_model
uv run python python/verify.py --mode int8 --port /dev/cu.usbmodem314101 --log evidence/phase5/phase7-int8-serial-macos15.6-v1.txt
```

## Apprentissage (phase 4)

Les données sont synthétiques : x ∈ [0, 2π], y = sin(x) + un bruit gaussien de σ = 0,1. Il y a 1 000 points, répartis en 600 pour l'entraînement, 200 pour la validation et 200 pour le test (seed 2027). Le réseau a la forme 1 → 16 ReLU → 16 ReLU → 1, soit 321 paramètres, et il est entraîné pendant 500 époques.

| MSE train | MSE validation | MSE test | Plancher de bruit (σ²) |
|---|---|---|---|
| 0,01046 | 0,01169 | 0,01050 | 0,01000 |

Le réseau atteint presque le bruit qu'on a ajouté : il ne peut pas faire mieux sur ces données.

## Conversion

| | FP32 | INT8 |
|---|---|---|
| Fichier `.tflite` | 3 216 octets | 2 704 octets |
| SHA-256 | `6990a391…216d6a` | `05758df8…5c926f4c` |
| Schéma / opérateurs | 3 / 3 × `FULLY_CONNECTED` (ReLU fusionné) | idem |
| Entrée | float32 | int8, scale 0,024632, zero_point −128 |
| Sortie | float32 | int8, scale 0,0080403, zero_point 5 |

Le modèle INT8 n'est que 16 % plus petit. Pour un réseau de 321 paramètres, les métadonnées du fichier pèsent autant que les poids.

La conversion INT8 est reproductible : deux exécutions produisent le même SHA-256. La quantification se fait **par tenseur** (`_experimental_disable_per_channel_quantization_for_dense_layers`), et `convert.py` refuse tout tenseur quantifié par canal.

## Exécution sur la carte (phases 5 et 7) : validé sur matériel

Le modèle est exécuté sur 23 entrées : 21 points réguliers sur [0, 2π], plus −0,5 et 7,0, hors du domaine d'entraînement. La référence est l'interpréteur LiteRT desktop avec ses noyaux de référence. `verify.py` refait toutes les comparaisons à partir des valeurs brutes reçues. Il vérifie aussi que le SHA-256 annoncé par la carte est bien celui du modèle.

| Mesure | FP32 | INT8 |
|---|---|---|
| Nano vs LiteRT | écart max **2,4·10⁻⁷**, 8/23 sorties identiques au bit près (tolérance 1·10⁻⁵) | écart max **1 LSB**, 22/23 codes identiques (tolérance 1 LSB) |
| Nano vs Keras FP32 sur [0, 2π] | 1,2·10⁻⁷ | 0,084 (erreur de quantification) |
| Résultat | 23/23 OK, `STATUT OK` | 23/23 OK, `STATUT OK` |
| `Invoke()`, médiane (min–max) | 129 µs (129–203) | 119 µs (118–164) |
| Mémoire de travail (arena) utilisée / réservée | 880 / 4 096 octets | 820 / 4 096 octets |
| Flash du programme | 142 464 octets (14 %) | 142 136 octets (14 %) |
| RAM statique (variables globales, arena incluse) | 50 432 octets (19 %) | 50 432 octets (19 %) |

**À ne pas confondre :**
- la **Flash** contient le programme, la bibliothèque et le modèle ;
- la **RAM statique** est connue dès la compilation, et la réserve de 4 096 octets de l'arena en fait partie ;
- l'**arena utilisée** est mesurée à l'exécution par `arena_used_bytes()`. C'est elle qui permet de réduire la réserve en toute sécurité.

Pour comparaison, l'exemple officiel `hello_world` occupe 345 384 octets de Flash (phase 3). Il enregistre **tous** les opérateurs (`AllOpsResolver`), alors que nos sketches n'enregistrent que `FULLY_CONNECTED`. Cela économise environ 200 Ko de Flash.

**Écart de 1 LSB en INT8, test n° 8 (x = 2,513274) : la carte donne 72, LiteRT 73.** Les codes d'entrée sont identiques sur les 23 tests (vérifié). L'écart vient donc de la requantification entière à l'intérieur de `FULLY_CONNECTED`, que LiteRT desktop et TFLM n'arrondissent pas de la même manière. Ce phénomène était déjà relevé dans `docs/AUDIT.md` §11.4. Un écart de 1 LSB vaut 0,008 en sortie, une valeur négligeable devant l'erreur de quantification (0,084).

**Hors domaine :** pour x = 7,0, l'entrée INT8 sature à 127, ce qui revient à x ≈ 6,28. La carte répond alors −0,153, quand le modèle FP32 répond +0,021. La quantification ne peut pas représenter une entrée qui sort de la plage de calibration. Le firmware sature explicitement l'entrée au lieu de la laisser déborder.

## Fichiers

- `phase5-fp32-compile.log`, `phase7-int8-compile.log` : sorties complètes de la compilation.
- `phase5-fp32-serial-macos15.6-v1.txt`, `phase7-int8-serial-macos15.6-v1.txt` : sorties série brutes de la carte.
- `phase5-arena512-error-macos15.6-v1.txt` : essai volontaire avec une arena de 512 octets. La carte affiche `ERREUR init=AllocateTensors` et ne lance aucune inférence (pas de pointeur nul, contrairement à l'exemple officiel).
