# TP03 — Quantification INT8 et inférence sur la Nano 33 BLE Sense

**Statut : spécification, aucun firmware d'inférence TinyML2027 validé à ce jour.** Durée cible : 4 h. Matériel : **une seule** Arduino Nano 33 BLE Sense originale ou Rev2, USB et ordinateur; aucun ESP32.

## Mission
Transformer le modèle FP32 du TP02 en INT8, vérifier les artefacts et démontrer les prédictions sur la carte, d'abord à partir de données de référence puis en direct. Comparer taille du modèle, Flash, RAM et latence. La consommation n'est pas exigée faute de matériel de mesure.

## Procédure
1. Charger le contrat de modèle TP02 (quatre features, unités, scaler, trois classes, ordre strict), regarder le graphe et les signatures entrées/sorties.
2. Réaliser une quantification **full integer INT8** avec calibration faite sur train uniquement; vérifier types des tenseurs de poids, activations, entrées et sorties et les opérateurs, sans supposer que toutes les architectures sont supportées.
3. Comparer FP32 et INT8 **sur les mêmes fenêtres**, métriques globales et exemples à désaccord; expliquer l'échelle `scale`, `zero_point`, saturations et surcoûts des petits modèles.
4. Exporter le modèle et un fichier `model_int8.h` reproduisible, SHA-256 et manifeste, associer Golden vectors de données brutes, features, valeurs normalisées, quantification et scores attendus.
5. Identifier une version **testée** de LiteRT Micro / TensorFlow Lite Micro compatible avec le core Mbed Nano et les deux IMU; fixer commit, dépendances, API. Ne **pas** copier le code `MicroErrorReporter` historique ou supposer une bibliothèque `TensorFlowLite` toujours disponible.
6. Compiler firmware `infer_nano.ino` avec sélecteur de révision ou deux variantes; rendre les opérateurs explicites, dimensionner tensor arena et gérer l'échec `AllocateTensors`, les conditions erreurs et les prints.
7. **Replay avant live** : injecter fenêtres de référence, calculer en C++ exactement les mêmes features que Python, comparer à tolérances déclarées. Attention : fréquence dominante/PSD peuvent coûter CPU/RAM; préférer une implémentation mesurée, et si simplification nécessaire revenir au TP01 et réentraîner (ne pas modifier seulement C++).
8. Tester parité de sortie INT8/float déquantifiée avec le moteur desktop; afficher discordances et causes possibles.
9. Passer en mode live : IMU -> tranches de 256 échantillons -> features -> scaler -> codes INT8 -> inférence -> label + scores + indication d'incertitude/rejet documentée. Un classifieur 3 classes ne connaît pas automatiquement l'état `unknown`.
10. Mesurer Flash/RAM de compilation, tensor arena utilisée, et latence d'inférence sur la Nano; si possible séparer acquisition, features et invoke. Ne jamais présenter une mesure simulée comme hardware.
11. Montrer à l'étudiant comment réinitialiser/reflasher une version connue en cas d'échec.

## Sorties
`quantization/` scripts et tests, `firmware/` code de capture/inférence, `artifacts/` modèle et manifest, `results/comparison.md`, `results/hardware-benchmark.md` avec résultats par révision OS/board/core/runtime, captures de compilation/téléversement/console. Les artefacts de génération doivent conserver licences et provenance.

## Acceptation
Compilation et exécution **vérifiées sur carte réelle**, golden vectors rejoués, contrat numérique contrôlé, classes affichées, chiffres réels de ressources et tutoriel d'installation exécuté de bout en bout sur les systèmes déclarés supportés. CI non matériel seulement = résultat partiel.

## Sources
https://github.com/wld-code/AIoT-Book/tree/main/labs/ch11-int8-quantization
https://github.com/wld-code/AIoT-Book/tree/main/labs/ch12-nano-esp32-deployment
https://ai.google.dev/edge/litert/microcontrollers
https://github.com/tensorflow/tflite-micro
