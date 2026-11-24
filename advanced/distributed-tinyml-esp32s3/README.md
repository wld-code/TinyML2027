# Extension expérimentale — Nano et ESP32-S3

Le travail préparatoire porte sur la compilation de l’exemple officiel `hello_world` d’[Espressif](https://github.com/espressif/esp-tflite-micro) avec ESP-IDF. L’exemple approxime une sinusoïde avec TensorFlow Lite Micro. Consultez le [README d’origine](esp32s3/00_tflm_hello_world/README.md) pour le détail de l’exemple et sa licence.

Depuis la racine du dépôt, préparez l’environnement ESP-IDF dédié et lancez la compilation.

```sh
./scripts/setup_esp.sh
./scripts/esp.sh -C advanced/distributed-tinyml-esp32s3/esp32s3/00_tflm_hello_world build
```

La compilation a été vérifiée. L’exécution sur ESP32-S3 et la communication avec la Nano restent à valider. Le [journal de compilation](../../evidence/esp32s3/README.md) décrit l’essai.
