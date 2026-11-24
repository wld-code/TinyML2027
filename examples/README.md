# Exemples

Des sketches courts, à faire dans l'ordre. Chacun vérifie un maillon de la chaîne avant les TP.

| Exemple | Ce qu'il montre | Où il est expliqué |
|---|---|---|
| `01_blink` | compiler, téléverser, lire le port série | [tutoriel 02, étape 2](../tutorials/02-arduino-nano/README.md#étape-2--blink) |
| [`02_tflm_hello_world`](02_tflm_hello_world/README.md) | l'exemple officiel TensorFlow Lite Micro, tel quel | sa page |
| [`03_custom_model`](03_custom_model/README.md) | notre propre réseau (sinus) en FP32, et la preuve que la carte calcule comme l'ordinateur | sa page |
| `04_imu` | lire l'accéléromètre et le gyroscope, mesurer la vraie cadence | [tutoriel 02, étape 4](../tutorials/02-arduino-nano/README.md#étape-4--lire-limu) |
| [`05_int8_model`](05_int8_model/README.md) | le même réseau en INT8 : ce qu'on gagne, ce qu'on perd | sa page |

Toutes les commandes se lancent depuis la racine du dépôt, par exemple :

```sh
./scripts/compile.sh examples/01_blink
./scripts/upload.sh  examples/01_blink
```

Carte **Rev2** : ajoutez `REV=rev2` devant les commandes de `04_imu`.
