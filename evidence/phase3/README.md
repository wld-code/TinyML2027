# Phase 3 — exemple officiel `hello_world` (Arduino_TensorFlowLite @ 7948b85e)

Conditions : 23/11/2026, macOS 15.6 (M4), arduino-cli 1.5.1, `arduino:mbed_nano@4.6.0`, Nano 33 BLE Sense V1 (série USB E011A05896DEE871). Exemple **non modifié**.

| Étape | Résultat | Statut |
|---|---|---|
| Compilation (gnu++14 par défaut du core, aucune option ajoutée) | 0 erreur, 0 avertissement ; Flash 345 384 o (35 %), RAM statique 54 104 o (20 %) — `phase3-hello_world-compile.log` | compilé |
| Téléversement | OK | téléversé |
| Sortie série (`MicroPrintf` de la luminosité LED, ~30 lignes/s) | 183 lignes en 6 s, port ouvert à 0 s ou 6 s ; 123 lignes en 4 s pour une ouverture à 1, 2, 3, 3 et 4 s | exécuté |
| Arène | réservée 2 000 o ; utilisée **820 o** (mesuré par une copie instrumentée hors dépôt, `arena_used_bytes()`) ; schéma du modèle = 3 | exécuté |
| LED orange qui « respire » (sinus) | confirmée visuellement par l'enseignant le 23/11/2026 | **validé sur matériel** |

## Incident non reproduit
Premier essai après téléversement : 0 octet reçu pendant 6 s, puis 0 octet sur une seconde ouverture de 8 s, alors que le port `/dev/cu.usbmodem31201` restait présent. Les 7 essais suivants, avec ouverture du port entre 0 et 6 s après le téléversement, ont tous réussi. Cause **non établie**. Pistes : course à l'énumération USB CDC du core Mbed, ou charge du Mac (installation ESP-IDF en parallèle). Parade documentée pour les étudiants : fermer puis rouvrir le moniteur, ou appuyer une fois sur RESET.

## Remarque sur le code officiel
Si `AllocateTensors()` échoue, `setup()` fait `return` et `loop()` utilise ensuite `input == nullptr`, d'où un plantage. Ce n'est pas observé ici, mais nos propres exemples devront arrêter proprement la boucle en cas d'échec.
