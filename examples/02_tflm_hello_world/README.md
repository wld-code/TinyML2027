# 02 — Exemple officiel TensorFlow Lite Micro `hello_world`

L'exemple est utilisé **tel quel** depuis la bibliothèque officielle installée par `./scripts/setup.sh` (commit figé dans `config/versions.lock`). Il n'est pas recopié dans le dépôt.

```sh
./scripts/compile.sh .arduino/user/libraries/Arduino_TensorFlowLite/examples/hello_world
./scripts/arduino.sh upload -p PORT --fqbn arduino:mbed_nano:nano33ble --input-dir build/hello_world
./scripts/arduino.sh monitor -p PORT -c baudrate=115200
```

Résultat attendu (mesuré, voir `evidence/phase3/`) :
- environ 30 nombres par seconde entre 0 et 255 dans le moniteur (luminosité de la LED) ;
- la LED orange s'allume et s'éteint progressivement, selon un sinus ;
- Flash 345 384 octets (35 %), RAM statique 54 104 octets (20 %).

Moniteur vide : fermez-le puis rouvrez-le, ou appuyez une fois sur RESET (incident observé une fois, non reproduit).
