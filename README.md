# TinyML 2027

Travaux pratiques de TinyML avec l'Arduino Nano 33 BLE Sense (originale et Rev2).

**Statut (23/11/2026).** Sur la carte de référence (Nano 33 BLE Sense **V1**, macOS Apple Silicon), toute la chaîne est **validée sur matériel** : l'acquisition, le dataset (5 sessions), l'entraînement, le modèle INT8, le rejeu des golden vectors et la reconnaissance en direct des 3 gestes. Les firmwares Rev2 sont **compilés seulement** (pas de carte Rev2). Windows et Linux ne sont **pas testés**. Les preuves sont dans [evidence/](evidence/).

Chaque résultat annoncé porte l'un de ces statuts : **non testé**, **compilé**, **téléversé**, **exécuté**, **validé sur matériel**.

## Parcours

| Étape | Contenu | Statut sur la carte de référence |
|---|---|---|
| [Tutoriel 01 — Python et Jupyter](tutorials/01-python-jupyter/README.md) | environnement, NumPy, premiers signaux | en cours de rédaction |
| [Tutoriel 02 — Prendre en main la Nano](tutorials/02-arduino-nano/README.md) | Blink, identification, IMU sur 3 axes | validé sur matériel |
| [Exemples 01 à 05](examples/) | Blink, `hello_world` officiel, modèle sinus FP32 et INT8, IMU | validé sur matériel |
| [TP01 — Du capteur au dataset](labs/01-sensor-data/README.md) | acquisition, contrôle qualité, fenêtres, 4 features | validé sur matériel |
| [TP02 — Entraîner sans tricher](labs/02-model-training/README.md) | partition par session, baselines, réseau 4-8-3 | exécuté (données réelles) |
| [TP03 — Le modèle sur la carte](labs/03-embedded-inference/README.md) | INT8, rejeu des golden vectors, direct, ressources | validé sur matériel |
| [Pour aller plus loin — Edge Impulse](advanced/edge-impulse/README.md) | audio, plateforme en ligne | validé sur matériel (Nano V1) ; Rev2 non testée |
| [Pour aller plus loin — Edge MLOps](advanced/edge-mlops/README.md) | versions, mise à jour USB, retour arrière | non commencé |
| [Pour aller plus loin — TinyML distribué Nano + ESP32-S3](advanced/distributed-tinyml-esp32s3/) | extension facultative | compilé (ESP32-S3 non détectée par le Mac) |

## Matériel

- Une Arduino Nano 33 BLE **Sense** : originale/V1 (ABX00031, IMU LSM9DS1) ou Rev2 (ABX00069, IMU BMI270). Seule la V1 est disponible pour les vérifications.
- Un câble USB **de données**. Beaucoup de câbles ne font que la charge : si la carte n'apparaît pas, changez de câble en premier.
- Un Mac. Linux et Windows sont des objectifs secondaires, **non testés**.

Le parcours obligatoire n'utilise ni ESP32, ni capteur externe, ni shield, ni cloud payant. L'extension ESP32-S3 est facultative.

## Versions figées

Toutes les versions sont dans [config/versions.lock](config/versions.lock) (chaîne Arduino) et dans [uv.lock](uv.lock) / [requirements.lock](requirements.lock) (Python, avec les empreintes SHA-256 des paquets).

| Composant | Version | Statut |
|---|---|---|
| Arduino CLI | 1.5.1 (binaire officiel macOS ARM64, SHA-256 vérifié) | installé |
| Core | `arduino:mbed_nano@4.6.0`, FQBN `arduino:mbed_nano:nano33ble` | validé sur matériel (identification, IMU) |
| Arduino_LSM9DS1 | 1.1.1 | validé sur matériel (cadence 116 Hz, 6 orientations, voir evidence/phase6) |
| Arduino_BMI270_BMM150 | 1.2.4 (Rev2) | compilé seulement |
| Arduino_TensorFlowLite | commit `7948b85e020470a30a83bf00e10fc43b486bfcba` (dépôt officiel archivé) | **validé sur matériel** (exemple officiel `hello_world`, phase 3) |
| Python | 3.12.7 | testé sur Mac |
| TensorFlow / NumPy | 2.21.0 / 2.5.5 | testés sur Mac (`uv run pytest` : 32 tests) |

---

## Installation (macOS Apple Silicon, vérifiée)

L'installation reste **dans le dossier du projet**. Elle ne touche ni à votre Python système ni à votre installation Arduino existante :

| Dossier | Contenu |
|---|---|
| `.venv/` | Python 3.12.7 et les bibliothèques verrouillées (TensorFlow, LiteRT, NumPy, Jupyter…) |
| `.arduino/` | Arduino CLI 1.5.1, core Mbed OS Nano 4.6.0, compilateur ARM, bibliothèques IMU et TensorFlow Lite Micro |

Ces deux dossiers sont ignorés par git. Pour repartir de zéro, supprimez-les et relancez `./scripts/setup.sh`. Prévoyez environ 1,5 Go d'espace disque et une connexion Internet pour l'installation. Ensuite, tout fonctionne hors ligne.

### Étape 1 — Outils de base

**Objectif :** disposer de `git` et du gestionnaire Python `uv`.

```sh
xcode-select --install     # outils Apple et git ; ignorer l'erreur s'ils sont déjà installés
# Homebrew, si absent : https://brew.sh
brew install uv
```

**Contrôle :** `git --version` et `uv --version` affichent une version. Versions de vérification : git 2.54.0, uv 0.11.14.

### Étape 2 — Récupérer le dépôt

```sh
git clone https://github.com/wld-code/TinyML2027.git
cd TinyML2027
```

Toutes les commandes suivantes se lancent **depuis ce dossier**.

### Étape 3 — Tout installer

```sh
./scripts/setup.sh
```

Le script effectue, dans l'ordre :
1. il télécharge Arduino CLI 1.5.1 et **refuse de continuer si l'empreinte SHA-256 ne correspond pas** ;
2. il installe le core `arduino:mbed_nano@4.6.0` et les bibliothèques IMU aux versions figées ;
3. il récupère `Arduino_TensorFlowLite` au commit figé et vérifie ce commit ;
4. il crée `.venv/` avec `uv sync --frozen`, qui refuse toute version différente de `uv.lock`.

Il se termine par un récapitulatif. Résultat attendu, tel qu'obtenu sur la machine de référence :

```text
arduino:mbed_nano 4.6.0
Arduino_LSM9DS1        1.1.1
Arduino_TensorFlowLite 2.4.0-ALPHA
Python 3.12.7 | TensorFlow 2.21.0 | NumPy 2.5.5
```

**Pourquoi Python 3.12 ?** TensorFlow 2.21 ne publie ses paquets que pour Python 3.10 à 3.13, et NumPy 2.5 exige au moins 3.12.

**Contrôle Python :** `uv run pytest -q` doit afficher `32 passed`. Ces tests couvrent la chaîne TensorFlow/LiteRT, les features (comparées à SciPy), le contrôle qualité, le protocole série (avec une carte simulée) et le calcul C++ des features compilé sur le poste.

> N'utilisez pas `pip install` dans le Python global. Sur la machine de référence, il contenait un matplotlib cassé (Pillow absent) : c'est ce que `.venv` évite.

### Étape 4 — Brancher et identifier la carte

1. Branchez la carte avec le câble de données. La LED verte « ON » s'allume.
2. Listez les cartes :

   ```sh
   ./scripts/arduino.sh board list
   ```

   Résultat attendu : `Arduino Nano 33 BLE` et `arduino:mbed_nano:nano33ble`, sur un port `/dev/cu.usbmodemXXXX`. **Notez votre port.**

   > Le nom affiché est toujours « Nano 33 BLE », même pour une Sense : l'identifiant USB ne distingue pas les modèles. La révision se reconnaît aux capteurs.

3. Identifiez la révision (remplacez `PORT`) :

   ```sh
   ./scripts/compile.sh tutorials/02-arduino-nano/sketches/board_identify
   ./scripts/arduino.sh upload -p PORT --fqbn arduino:mbed_nano:nano33ble --input-dir build/board_identify
   ./scripts/arduino.sh monitor -p PORT -c baudrate=115200      # puis Entrée ; Ctrl+C pour quitter
   ```

   Résultat obtenu sur la carte de référence :

   ```text
   i2c_devices=0x1E,0x39,0x5C,0x5F,0x6B
   lsm9ds1_whoami=0x68
   verdict=nano33ble_sense_original
   ```

**Dépannage :**
- *Aucun port* : changez de câble, puis de prise USB. Un double appui rapide sur RESET met la carte en mode bootloader (la LED orange pulse).
- *Moniteur vide* : le rapport part au démarrage, souvent avant l'ouverture du port. Appuyez sur Entrée.
- *« port busy »* : un seul programme peut ouvrir le port. Fermez le moniteur série, l'IDE ou un notebook.

### Arduino IDE 2 (facultatif)

https://www.arduino.cc/en/software (version vérifiée : 2.3.10). L'IDE utilise ses propres dossiers, pas ceux du projet. Installez-y le core « Arduino Mbed OS Nano Boards » et la bibliothèque `Arduino_LSM9DS1`. Le parcours de référence utilise les scripts, dont les versions sont figées.

## Organisation du dépôt

```text
config/         versions figées de la chaîne Arduino et ESP-IDF (versions.lock)
docs/           spécification, contrat de données, validation, audit ; figures/ : images et GIF des TP
tutorials/      tutoriels 01 (Python) et 02 (Arduino)
examples/       01_blink, 02_tflm_hello_world, 03_custom_model, 04_imu, 05_int8_model
labs/           TP01 à TP03 (dont les firmwares imu_capture et infer_nano)
datasets/       motion-nano-v1 : les 5 sessions réelles de la carte de référence (CC BY 4.0)
advanced/       extensions « pour aller plus loin »
python/         modèle sinus (train, convert, verify) et génération des figures
src/tinyml2027/ code Python des TP : acquisition, contrôle qualité, features, entraînement, quantification
scripts/        setup.sh, arduino.sh, compile.sh, upload.sh (+ setup_esp.sh, esp.sh pour l'extension)
tests/          tests pytest sans carte (dont le test C++ des features)
evidence/       mesures et journaux réels, avec leurs conditions
```

Les firmwares n'utilisent que des bibliothèques officielles : Arduino_TensorFlowLite (avec sa kissfft), Arduino_LSM9DS1 et Arduino_BMI270_BMM150.

## Licence

- Code (Python, C++, sketches, scripts) : [MIT](LICENSE).
- Contenus pédagogiques : [CC BY 4.0](LICENSE-docs.md).
- Composants tiers : leurs propres licences. TensorFlow Lite Micro (`Arduino_TensorFlowLite`) est sous Apache-2.0.

Sources : [AIoT-Book/labs](https://github.com/wld-code/AIoT-Book/tree/main/labs) et [TinyML-for-motor](https://github.com/wld-code/TinyML-for-motor).

Auteur : Walid Abdaoui.
