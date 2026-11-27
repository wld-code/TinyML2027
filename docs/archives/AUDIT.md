# Audit Lot 0 — état de l'existant, versions, risques et plan

**Date de l'audit : 23 novembre 2026.** Rédigé à partir de commandes réellement exécutées sur le Mac de l'enseignant et d'une carte réellement branchée. Chaque affirmation porte l'un des statuts suivants :

- **[mesuré]** : sortie réelle obtenue pendant l'audit (commande et date indiquées) ;
- **[lu]** : lu dans le code source ou les métadonnées officielles (PyPI, GitHub, index Arduino), sans exécution ;
- **[à tester]** : hypothèse qui doit être confirmée par un essai avant d'être enseignée.

Aucun TP n'est encore développé. Ce document sert de base de décision pour la suite des lots.

---

## 1. Diagnostic du poste de référence

Commandes : `sw_vers`, `uname -m`, `sysctl`, `xcode-select -p`, `git --version`, `pyenv versions`, `python3 -m pip list`, `arduino-cli version`, `arduino-cli core list`, `arduino-cli lib list`.

| Élément | Valeur [mesuré] | Commentaire |
|---|---|---|
| OS | macOS 15.6 (build 24G84) | |
| Processeur | Apple M4, `arm64`, 24 Go RAM | Wheels `macosx_12_0_arm64` requis |
| Outils de dév. | Command Line Tools, Apple clang 17.0.0, Git 2.54.0, CMake 4.4.3, GNU Make 3.81 | Suffisant pour `create_tflm_tree.py` [à tester] |
| Python actif | 3.12.7 (pyenv, global) + pip 24.2 | Aussi : Homebrew 3.14 et 3.15.2, système 3.9.6 |
| Gestionnaires | uv 0.11.14, Homebrew 7.0.13 ; pas de conda/pipx/poetry | |
| Paquets dans le Python global | numpy 2.5.2, scipy 1.18.0, matplotlib 3.11.1, pyserial 3.5, pytest 9.0.3 | TensorFlow, pandas, scikit-learn, Jupyter **absents**. Le cours n'utilisera pas le Python global |
| Arduino IDE | 2.3.10 | 2.3.11 publiée le 12/11/2026 [lu] |
| Arduino CLI | 1.5.1 (Homebrew) | 1.6.0 publiée le 10/11/2026 [lu] |
| Core | `arduino:mbed_nano` 4.6.0 | Dernière version de l'index [lu] |
| Bibliothèques | Arduino_LSM9DS1 1.1.1, Arduino_BMI270_BMM150 1.2.4, Chirale_TensorFlowLite 2.0.0, Harvard_TinyMLx 1.2.4-Alpha, AltSoftSerial, PubSubClient | Harvard_TinyMLx embarque un TFLite 2.4.0 de 2020 : risque de conflit d'en-têtes `tensorflow/…` avec un TFLM moderne |
| Autres cores | `arduino:avr` 1.8.8, `esp32:esp32` 3.3.10 | Hors périmètre ; ne pas toucher |

**Décision proposée :** ne pas modifier l'environnement global. Le dépôt utilisera :
1. un `.venv` local créé par `uv` avec Python 3.12 et un lockfile (`uv.lock`) ;
2. un répertoire Arduino isolé (`arduino-cli.yaml` du dépôt avec `directories.data` / `directories.user` dans un dossier ignoré par git). Les bibliothèques installées actuellement ne pourront alors plus interférer.

Ces deux créations restent à autoriser par l'enseignant. Elles téléchargent environ 1 Go (TensorFlow + toolchain ARM).

---

## 2. Identification réelle de la carte

### 2.1 Détection USB [mesuré, 23/11/2026]

```text
$ arduino-cli board list
Port                    Protocol Type              Board Name          FQBN
/dev/cu.usbmodem31201   serial   Serial Port (USB) Arduino Nano 33 BLE arduino:mbed_nano:nano33ble
```

`system_profiler SPUSBDataType` : VID `0x2341`, PID `0x805a`, « Nano 33 BLE ».

**Limite importante :** ce VID:PID est le même pour la Nano 33 BLE, la Sense originale et la Sense Rev2. Le port USB **ne permet pas** d'identifier la révision. Le nom « Nano 33 BLE » affiché par l'IDE ne veut pas dire « carte sans capteurs ».

### 2.2 Identification par les capteurs [mesuré, 23/11/2026]

Sketch : `tutorials/02-arduino-nano/sketches/board_identify/board_identify.ino`. Il ne fait que lire les registres d'identité sur le bus interne `Wire1` et n'écrit rien dans les capteurs. Il compile en 93 200 octets de Flash (9 %) et 45 912 octets de RAM globale (17 %) avec `arduino:mbed_nano` 4.6.0.

```text
BEGIN board_identify v1
i2c_devices=0x1E,0x39,0x5C,0x5F,0x6B
lsm9ds1_whoami=0x68
lsm9ds1m_whoami=0x3D
bmi270_chipid=none
bmm150_chipid=none
verdict=nano33ble_sense_original
END
```

Interprétation : LSM9DS1 (0x6B/0x1E), HTS221 (0x5F), LPS22HB (0x5C) et APDS9960 (0x39), aucun BMI270. **La carte de référence est une Nano 33 BLE Sense originale.** La présence des capteurs « Sense » laisse prévoir le microphone PDM MP34DT05, dont le fonctionnement reste [à tester] dans le Lot 6.

Incident rencontré et corrigé : la première version n'envoyait son rapport qu'au démarrage. Il était perdu si le port était ouvert après. Le sketch répond désormais à tout caractère reçu. Ce piège (« le moniteur série reste vide ») ira dans le dépannage du tutoriel 02.

**Conséquence :** la révision Rev2 (BMI270/BMM150) ne pourra être que **compilée**, jamais validée matériellement, tant qu'une carte Rev2 n'est pas disponible. La matrice de validation le dira explicitement.

### 2.3 Cadence réelle de l'accéléromètre [mesuré, 23/11/2026]

Sketch de diagnostic temporaire (hors dépôt) : `Arduino_LSM9DS1` 1.1.1, lecture quand `accelerationAvailable()` est vrai, horodatage `micros()` côté carte. Capture de 10 s par pyserial, carte posée.

```text
# accel_odr_hz=119.00
samples=1156 seq_gaps=0 non_monotonic_t=0
fs_median_hz=114.21 fs_mean_hz=116.22 dt_min_us=8167 dt_max_us=11550 dt_cv=0.0308
ax_mean_g=+0.0059 ay_mean_g=-0.0261 az_mean_g=+0.9626   |a|_mean_g=0.9630
```

Ce qu'on en retient :
- La bibliothèque fixe l'ODR à **119 Hz nominal** (`LSM9DS1.cpp:73`, registre `CTRL_REG6_XL = 0x70`, ±4 g). Elle n'expose pas d'API pour la changer.
- La cadence observée est plus basse et irrégulière (médiane 114 Hz, CV 3 %).
- La **cible de 50 Hz** de `DATA_CONTRACT.md` / TP01 **n'est pas native**. L'atteindre demanderait d'écrire un registre (59,5 Hz est l'ODR LSM9DS1 la plus proche) ou de décimer. Voir §5.1.
- La norme mesurée vaut 0,963 g : le capteur n'est pas calibré (offset et gain). C'est un bon support pédagogique (« g mesuré ≠ 1 g »).
- Pour la Rev2, `Arduino_BMI270_BMM150` fixe **100 Hz** (`BMI270.cpp:291`) [lu]. Les deux révisions n'ont donc pas la même cadence.

La carte contient actuellement ce sketch de diagnostic. Elle sera reflashée lors des tutoriels.

---

## 3. Analyse des sources existantes

Clone en lecture seule (hors dépôt) : `wld-code/TinyML-for-motor` (public, commit `d0b134a`, 17/12/2025).

### 3.1 Licences

| Source | Licence [lu] | Conséquence |
|---|---|---|
| TinyML-for-motor | Aucun fichier LICENSE | Le firmware `classify_imu.ino` dérive de l'exemple Arduino de D. Coleman et S. Mistry, déclaré « domaine public » dans son en-tête. On ne reprend que le concept |
| tflite-micro | Apache-2.0 | Conserver LICENSE et NOTICE dans tout arbre vendu |
| Arduino_LSM9DS1, Arduino_BMI270_BMM150 | LGPL-2.1 | Utilisées comme bibliothèques, non modifiées |
| ArduinoCore-mbed | Pas de SPDX détecté par GitHub (LGPL d'après le dépôt [à confirmer]) | Pas de redistribution |

**Il faut choisir la licence de TinyML2027 :** par exemple CC BY 4.0 pour les textes et MIT ou Apache-2.0 pour le code.

### 3.2 TinyML-for-motor — à ne pas recopier

- API TFLM supprimée : `MicroErrorReporter`, `AllOpsResolver`, `#include <TensorFlowLite.h>`, `version.h`. Ces fichiers n'existent plus dans `tflite-micro` HEAD [lu].
- Le commentaire « 119 échantillons ≈ 2 s à 50 Hz » est faux : la carte échantillonne à environ 119 Hz, donc environ 1 s.
- Le split est un mélange aléatoire de gestes, avec un risque de fuite. Le notebook suit des métriques de régression (MAE) pour une classification. Le port série est codé en dur. Le modèle pèse 148 Ko et `model.h` 900 Ko.
- À garder : l'idée d'un geste déclenché par seuil et d'un parcours guidé en français. Cela peut servir de variante `punch/flex` facultative.

---

## 4. État de l'art des technologies (vérifié le 23/11/2026)

### 4.1 Python

| Composant | Dernière version [lu] | Contraintes | Choix proposé |
|---|---|---|---|
| Python | 3.15 disponible | TensorFlow 2.21 : wheels macOS arm64 pour **3.10–3.13 seulement** ; NumPy 2.5 / SciPy 1.18 : ≥ 3.12 | **Python 3.12** (déjà installé via pyenv ; plan B 3.13) |
| TensorFlow | 2.21.0 (06/03/2026) | Sert uniquement à entraîner et convertir | Figer `2.21.0` |
| Keras | 3.15.1 ; tf-keras 2.21.0 | La version de Keras réellement résolue avec TF 2.21 reste [à tester] | Lockfile |
| ai-edge-litert | 2.4.0 (20/11/2026), cp310–cp314 arm64 | Interpréteur desktop qui remplace `tf.lite.Interpreter` | À utiliser pour les références FP32/INT8 desktop |
| tflite-micro (pip) | `0.dev20261119…` | Wheels **Linux x86_64 seulement** | Interpréteur TFLM réel en CI Ubuntu ; non disponible nativement sur le Mac |
| numpy / scipy / pandas / scikit-learn / matplotlib | 2.5.5 / 1.18.1 / 3.1.1 / 1.9.1 / 3.11.2 | pandas 3.x a changé des comportements par défaut (copy-on-write, dtype string) | Figer au lock |
| JupyterLab | 4.6.6 | | |
| pyserial | 3.5 (2020, toujours la référence) | | |

La compatibilité réelle de l'ensemble (résolution `uv`, import de TF, conversion INT8 d'un 4-8-3, exécution `ai_edge_litert`) est **[à tester]** dans l'essai E4. Les métadonnées seules ne suffisent pas.

### 4.2 Embarqué

| Composant | État [lu] | Analyse |
|---|---|---|
| ArduinoCore-mbed / `mbed_nano` | 4.6.0 (28/05/2026) | Même FQBN `arduino:mbed_nano:nano33ble` pour l'originale et la Rev2. Arm a annoncé la fin de vie de Mbed OS (date à recouper avant publication) : c'est un risque de pérennité, pas un blocage immédiat |
| CMSIS-DSP | `arm_math.h` absent du core installé | Ne pas compter sur `arm_rfft_fast_f32` |
| tflite-micro (GitHub) | Actif ; HEAD `38a8f0f873` du 19/11/2026 ; Apache-2.0 | La référence de l'état de l'art |
| Doc « LiteRT for Microcontrollers » (developers.google.com) | Les pages *Get started* et *Build and convert* montrent encore `MicroErrorReporter` et un constructeur `MicroInterpreter(…, error_reporter)` à 5 arguments | **Décalage avec le code** : ces symboles n'existent plus dans HEAD. Le cours suivra le code figé, pas ces pages, et le signalera aux étudiants |
| Bibliothèque `Arduino_TensorFlowLite` citée par la doc | Absente de l'index officiel des bibliothèques Arduino | Impossible de l'installer par Library Manager |
| Chirale_TensorFlowLite | 2.0.0, dernière publication 05/07/2024 | Instantané TFLM de 2024, installable en un clic, non maintenu depuis plus de 2 ans |
| Harvard_TinyMLx | TFLite 2.4.0-Alpha | Obsolète ; à exclure du parcours |

**API TFLM actuelle [lu dans `tensorflow/lite/micro/micro_interpreter.h` @ 38a8f0f] :**

```cpp
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_log.h"      // MicroPrintf
#include "tensorflow/lite/micro/system_setup.h"   // tflite::InitializeTarget()

tflite::MicroMutableOpResolver<2> resolver;  // opérateurs explicites
resolver.AddFullyConnected();
resolver.AddSoftmax();
tflite::MicroInterpreter interpreter(model, resolver, arena, kArenaSize);
if (interpreter.AllocateTensors() != kTfLiteOk) { /* échec affiché, pas masqué */ }
size_t used = interpreter.arena_used_bytes();  // dimensionnement mesuré de l'arène
```

`RecordingMicroInterpreter` sert à détailler la mémoire. Le dépôt fournit `tensorflow/lite/micro/tools/project_generation/create_tflm_tree.py`, qui extrait l'arbre minimal de sources. Il contient aussi `third_party/kissfft` et une bibliothèque `signal/` (RFFT, Window, Energy) [lu].

**Recommandation (à confirmer par l'essai E5) :**
- **Voie principale :** générer, à partir d'un **commit figé** de `tflite-micro`, une bibliothèque Arduino locale au dépôt (sources produites par `create_tflm_tree.py`, `.cc` renommés en `.cpp`, LICENSE Apache conservée, script de génération versionné). L'étudiant n'installe rien de plus : la bibliothèque est fournie, et le script permet à l'enseignant de la régénérer.
- **Plan B :** Chirale_TensorFlowLite 2.0.0, si la voie principale ne compile pas avec le core Mbed. Sa date sera documentée comme une limite.
- Dans les deux cas, désinstaller ou isoler Harvard_TinyMLx (environnement Arduino isolé, §1).

---

## 5. Contrat des quatre features : faisabilité et décisions à valider

Référence actuelle : `lab78.features()`. Elle prend un axe `ax_g` et 256 échantillons, retire la moyenne, calcule `rms_g` et `crest_factor`, puis une Welch à un seul segment (Hann, `scaling="density"`). La bande 0,5–10 Hz donne `dominant_hz` (argmax de la PSD) et `band_power_g2` (somme des bins × Δf).

### 5.1 Cadence (bloquant)

Les révisions ont des ODR différentes (119 contre 100 Hz), et la cadence observée n'est pas la cadence nominale. `dominant_hz = k·fs/256` dépend donc de `fs`. Proposition :
- **Abandonner la cible 50 Hz** et garder l'ODR native, sans modifier les registres. C'est plus simple et moins fragile pour un novice.
- **Définir `fs` par fenêtre, de façon identique en Python et en C++ :** `fs_win = (N−1) / ((t_us[N−1] − t_us[0]) · 1e-6)`. Ce calcul est déterministe et testable par golden vectors, et il ne dépend pas d'un fs « par enregistrement » que la carte ignore.
- Rejeter toute fenêtre dont un intervalle dépasse 1,5 × la médiane, avec la même règle des deux côtés.
- Une fenêtre de 256 échantillons dure environ 2,2 s sur l'originale et 2,56 s sur la Rev2. Le modèle sera entraîné et validé sur la révision mesurée. La généralisation d'une révision à l'autre est déclarée **non garantie**.

### 5.2 Spectre en C++ (faisable sur le papier, à mesurer)

- Coût : une RFFT de 256 points en float32 occupe environ 2 à 3 Ko de RAM pour les tampons. Elle prend probablement moins d'une milliseconde sur un Cortex-M4F à 64 MHz [à tester, essai E6].
- Implémentation : `kiss_fftr` (fourni avec TFLM, licence BSD) ou une radix-2 écrite pour le cours, plus lisible pédagogiquement.
- Côté Python, la référence sera une **formule NumPy explicite**, avec une PSD une face : `P[k] = c_k·|X[k]|² / (fs·Σw²)`, où `c_k = 2` sauf pour DC et Nyquist. Elle sera testée contre `scipy.signal.welch` à 1e-12 près. On évite ainsi de reproduire en C++ les conventions implicites de SciPy.
- **Instabilité de `dominant_hz` :** l'argmax peut sauter d'un bin entre float32 et float64 quand deux pics sont presque égaux. Règle de départage proposée : le plus petit indice. La parité de `dominant_hz` sera exigée à 1 bin près, avec un compte des fenêtres « ambiguës » (écart relatif entre les deux plus grands bins < 1e-4).
- **RMS = 0** (signal constant, possible après quantification) : `crest_factor` est fixé à 0 et un indicateur est levé. Pas de NaN dans le contrat embarqué. Le cas sera testé.

### 5.3 Protocole `impact` (pédagogique)

Avec 3 ou 4 tapotements en 15 s, la majorité des fenêtres ne contiennent aucun impact. Deux options :
- (a) tapotements doux et **réguliers pendant tout l'enregistrement**, environ un toutes les 0,5 à 1 s ;
- (b) étiquetage par fenêtre fondé sur un détecteur d'événement documenté.

Option (a) proposée pour le parcours obligatoire. Option (b) en question d'interprétation.

**Ces trois décisions doivent être validées avant tout entraînement.** L'essai E6 fournira les chiffres de ressources réels.

---

## 6. Architecture proposée

```text
TinyML2027/
├── pyproject.toml, uv.lock, .python-version (3.12)
├── arduino-cli.yaml                  # environnement Arduino isolé (data/user dans .arduino/, ignoré)
├── src/tinyml2027/                   # code Python testé, partagé par tous les modules
│   ├── serial_io.py                  # découverte de ports, protocole BEGIN/END, timeouts, pertes
│   ├── dataset.py                    # manifest, inspection, rejets explicites
│   ├── features.py                   # contrat des 4 features (référence NumPy)
│   ├── splits.py, train.py, export.py, quantize.py, golden.py
│   └── simulate.py                   # dataset synthétique, toujours marqué source=simulated
├── firmware/
│   ├── common/                       # imu.h (abstraction révision), features.h/.cpp, protocol.h
│   ├── libraries/tflm_<commit>/      # arbre TFLM figé + script de génération + LICENSE
│   └── sketches/                     # imu_capture, replay_features, infer_nano
├── tutorials/01-python-jupyter/      # notebooks, data/sample_acceleration.csv (synthétique)
├── tutorials/02-arduino-nano/        # sketches/board_identify, blink, imu_check
├── labs/01-…, 02-…, 03-…             # énoncés, notebooks, solutions séparées
├── advanced/edge-impulse, edge-mlops
├── tests/                            # pytest : features, dataset, split, quantification, parité
├── evidence/                         # logs et captures réels, nommés tpXX-etapeYY-os-carte
└── docs/ (AUDIT, COURSE_SPEC, DATA_CONTRACT, VALIDATION, REFERENCES)
```

**Abstraction IMU :** les deux bibliothèques déclarent chacune un objet global `IMU` de type différent, donc on ne peut pas les inclure dans le même sketch [lu]. On choisit à la compilation (`-DBOARD_REV2` ou un `#define` dans un seul en-tête `imu.h`). Le firmware vérifie au démarrage le registre d'identité (méthode du §2.2) et **refuse de fonctionner** si la bibliothèque compilée ne correspond pas à la carte. Il affiche alors un message explicite.

**Protocole série :** en-tête `BEGIN` avec version du firmware, révision détectée et ODR, puis lignes `seq,t_us,…` et `END`. Côté hôte, l'outil détecte les ports (filtre VID `0x2341`, choix explicite s'il y en a plusieurs) et ne code jamais un port en dur. Les trous de `seq`, les timestamps non monotones et les déconnexions sont signalés.

---

## 7. Stratégie de tests et de reproductibilité

| Niveau | Où | Ce qui est prouvé |
|---|---|---|
| Unitaires Python (pytest) | Mac + CI Ubuntu/Windows/macOS | Features sur signaux connus (constante, sinus à fréquence entière de bin, bruit, zéros), inspection (doublons, ordre, trous), split sans fuite, export, quantification et arrondis |
| Notebooks | CI (`nbclient`/`nbmake`) | Exécution intégrale depuis le haut, sans chemin absolu |
| Compilation firmware | Mac + CI (`arduino-cli compile`, originale **et** Rev2) | Compilation et tailles Flash/RAM ; pas le fonctionnement |
| Parité TFLM sur desktop | CI Ubuntu (`tflite-micro` pip) | Sorties INT8 TFLM = golden vectors |
| Replay sur carte | Mac + carte originale | Features C++ et scores INT8 = golden vectors, à tolérance déclarée |
| Live sur carte | Mac + carte originale | Cadence, classes, latence et arène mesurées |
| Rev2 matériel | **non disponible** | Marqué « compilé, non testé » |

Reproductibilité :
- lockfile `uv` ;
- core et bibliothèques Arduino aux versions figées dans un script `scripts/setup_arduino.sh` ;
- commit TFLM figé, seeds fixés ;
- `release_manifest.json` avec SHA-256 ;
- chaque preuve matérielle archivée dans `evidence/` avec OS, version du core, bibliothèque, commit et date.

---

## 8. Risques

**Embarqués :**
1. Les ODR différentes selon la révision et l'écart entre cadence nominale et observée faussent `dominant_hz` si le contrat ignore `fs` (§5.1).
2. L'arbre TFLM HEAD peut ne pas compiler avec la toolchain GCC du core Mbed (version C++ et options) [E5].
3. Conflit d'en-têtes avec Harvard_TinyMLx et Chirale dans le sketchbook actuel.
4. Mbed OS en fin de vie : le core peut ne plus évoluer.
5. Arène sous-dimensionnée ou opérateur non enregistré : l'échec doit être visible, jamais silencieux.
6. Sans tampon FIFO, la boucle d'inférence peut ralentir l'acquisition et perdre des échantillons LSM9DS1, ce que `seq` ne montre pas (le compteur est logiciel). Il faut surveiller la cadence pendant l'inférence.

**Pédagogiques :**
7. Les pages officielles LiteRT Micro sont désynchronisées du code : un étudiant qui suit la doc obtiendra des erreurs de compilation. Le cours doit l'expliquer.
8. Protocole `impact` mal étiqueté (§5.3).
9. Un dataset simulé peut être pris pour une preuve : marquage `source=simulated` obligatoire et visible dans les figures.
10. Une seule révision est testable : risque de déclarer la Rev2 « supportée » à tort.
11. Le « 100 % d'accuracy » probable sur un dataset trop facile : le test sur une session tenue à part est imposé, avec rotation des sessions.
12. La durée de 2 h du tutoriel Python peut être sous-estimée si TensorFlow s'installe mal sur certains postes Windows.

---

## 9. Essais à réaliser (Lot 0 restant)

| Id | Essai | Statut |
|---|---|---|
| E1 | Détection USB et identification de révision | **fait [mesuré]** : originale |
| E2 | Cadence IMU et cohérence `seq`/`t_us` au repos | **fait [mesuré]** : 114,2 Hz (médiane), 0 trou sur 10 s |
| E3 | IMU en mouvement : basculer la carte face X, Y, Z vers le haut (±1 g attendu sur chaque axe) ; balayage `periodic` ; tapotements | **partiel [mesuré]**, voir `evidence/lot0/README.md` : intégrité parfaite sur 120 s, ±X et ±Z observés, tapotements visibles (pics 0,1–0,26 g), bruit au repos ≤ 1 mg. **Manquent : ±Y et le mouvement gauche-droite**, à refaire |
| E4 | `.venv` uv Python 3.12 : TF 2.21 + ai-edge-litert 2.4 + pandas/sklearn ; conversion INT8 d'un 4-8-3 ; exécution LiteRT | **fait [mesuré]** : `tests/test_environment.py`, 3 tests réussis |
| E5 | Arbre TFLM figé → bibliothèque Arduino → compilation et exécution sur carte | **fait [mesuré]** : `tflm_smoke` status=PASS, 8/8 vecteurs bit-exacts avec TFLM (§11). Chirale non nécessaire |
| E6 | Sketch de mesure : RFFT 256 en float32, temps (`micros`), RAM, parité avec la référence NumPy sur des fenêtres connues | à faire |
| E7 | Cadence pendant un calcul de 1 à 5 ms dans la boucle (perte d'échantillons ?) | à faire |
| E8 | Microphone PDM : enregistrement d'une seconde, niveau RMS | Lot 6 |

---

## 10. Prochaines étapes

1. **Validation par l'enseignant** des décisions §1 (environnements isolés), §4.2 (voie TFLM), §5.1–5.3 (contrat) et du choix de licence.
2. Fin du Lot 0 : essais E3 à E7, générateur de dataset synthétique marqué, convention de documentation (gabarit d'étape), mise à jour de `DATA_CONTRACT.md` et `VALIDATION.md` avec les résultats.
3. Lot 1 (tutoriel Python), puis Lot 2 (tutoriel Arduino, qui intégrera `board_identify` et les observations du §2). Chaque lot se termine par fichiers, commandes, preuves et demande de validation.

---

## Références consultées (23/11/2026)

- LiteRT for Microcontrollers : https://developers.google.com/edge/litert/microcontrollers/overview (et pages *get_started*, *build_convert*, *library*)
- tflite-micro : https://github.com/tensorflow/tflite-micro (commit `38a8f0f87302817ddfa99e6a995c7b71ef7118fe`)
- PyPI : tensorflow, ai-edge-litert, tflite-micro, numpy, scipy, pandas, scikit-learn, matplotlib, jupyterlab, pyserial, pytest
- Index Arduino : https://downloads.arduino.cc/packages/package_index.json, https://downloads.arduino.cc/libraries/library_index.json
- ArduinoCore-mbed : https://github.com/arduino/ArduinoCore-mbed (release 4.6.0)
- Arduino CLI 1.6.0, Arduino IDE 2.3.11 (GitHub releases)
- Sources des bibliothèques installées : `Arduino_LSM9DS1/src/LSM9DS1.cpp`, `Arduino_BMI270_BMM150/src/BMI270.cpp`
- Nano 33 BLE Sense : https://docs.arduino.cc/hardware/nano-33-ble-sense/ ; Rev2 : https://docs.arduino.cc/hardware/nano-33-ble-sense-rev2/
- Sources du cours : `wld-code/TinyML-for-motor` (`d0b134a`)

---

## 11. Mise à jour du 23/11/2026 — décisions validées et essais E4/E5

### 11.1 Décisions validées par l'enseignant
- Environnements isolés `.venv/` (uv) et `.arduino/` : créés.
- Contrat des features §5.1 à §5.3 : cadence native et `fs` par fenêtre, tolérance d'un bin sur `dominant_hz`, `crest_factor = 0` si RMS = 0, protocole `impact` à tapotements réguliers. Reporté dans `DATA_CONTRACT.md`.
- Licence libre : MIT pour le code, CC BY 4.0 pour les contenus (`LICENSE`, `LICENSE-docs.md`).
- Installation système autorisée : GNU make 4.4.1 via Homebrew (`gmake`), utile seulement à l'enseignant. OrbStack/Docker démarré pour l'oracle TFLM.

### 11.2 Environnement Python verrouillé [mesuré]
`uv sync` avec Python 3.12.7 a résolu 140 paquets (`uv.lock`), dont : tensorflow 2.21.0, keras 3.15.1, ai-edge-litert 2.4.0, numpy 2.5.5, scipy 1.18.1, pandas 3.1.1, scikit-learn 1.9.1, matplotlib 3.11.2, jupyterlab 4.6.6, pyserial 3.5, pytest 9.2.0.

`uv run pytest -q` : **6 réussis**. On y trouve l'entraînement d'un réseau 4-8-3, la conversion full INT8 (entrée, sortie et poids int8, biais int32) et la parité FP32/INT8 sous LiteRT. Avertissement connu et sans effet : « Statistics for quantized inputs were expected ».

### 11.3 Le core Mbed ne compile pas en C++17 [mesuré], contournement validé
- Le core `mbed_nano` 4.6.0 utilise GCC **7.2.1 (2017-q4)** en `-std=gnu++14`.
- TFLM au commit `38a8f0f` **exige C++17** (`std::is_same_v`, paramètres `auto`) : en gnu++14, la compilation échoue dans `micro_common.h` et `kernels/internal/common.h`.
- En `-std=gnu++17`, **un sketch vide échoue avec 115 erreurs**. `Arduino.h` définit la macro `abs(x)`, et `<chrono>` en C++17 contient `std::chrono::abs`. Le core lui-même (`variant.cpp`) ne compile plus. C'est une limite connue du core Mbed, qui touche aussi d'autres runtimes C++17 comme ExecuTorch.
- **Contournement : `-include chrono`.** `<chrono>` est lu avant `Arduino.h`, donc avant la définition de la macro. Ses gardes d'inclusion empêchent ensuite une seconde lecture. Aucun fichier du core n'est modifié.
- Résultats avec `-std=gnu++17 -include chrono` :
  - sketch vide : 0 erreur ;
  - IMU LSM9DS1 et BMI270 : 0 erreur, 0 avertissement ;
  - PDM : 0 erreur ;
  - TFLM avec noyaux de référence et avec CMSIS-NN : 0 erreur, 0 avertissement.
- **Exécution :** le firmware IMU compilé en C++17 donne sur la carte la même cadence (114,13 Hz en médiane, aucun trou) que la version C++14.
- Toutes ces options passent par `scripts/compile.sh`, qui ajoute aussi les définitions lues dans `build_flags.txt` de la bibliothèque.
- **Limites :**
  - l'IDE Arduino ne passe pas ces options par défaut (à traiter au Lot 2 : `platform.local.txt` ou compilation par script uniquement) ;
  - le contournement dépend de la version de la libstdc++ fournie avec le core, il faut donc le revérifier à chaque mise à jour du core ;
  - seules les parties testées ci-dessus sont couvertes.
- Second correctif nécessaire, seulement pour la variante CMSIS-NN : GCC 7 ne fournit pas l'intrinsèque `__sxtb16`. Le script ajoute une définition de secours en une instruction SXTB16 (`PATCHES`, documenté dans `PROVENANCE.md`).
- **Plans de repli** si le contournement cédait (non testés) :
  - compiler TFLM en bibliothèque précompilée C++17 derrière une interface C++14 ;
  - revenir à un TFLM antérieur à l'exigence C++17 (Chirale 2.0.0, 2024) ;
  - surveiller le core Arduino basé sur Zephyr, dont la maturité pour la Nano 33 BLE n'a pas été évaluée.

### 11.4 Bibliothèque TFLM et parité sur la carte [mesuré]
- `scripts/build_tflm_arduino_lib.py` génère `firmware/libraries/TinyML2027_TFLM` :
  - commit `38a8f0f873`, cible `cortex_m_generic` Cortex-M4+FP, **noyaux de référence** ;
  - 451 fichiers, 5,1 Mo ;
  - `micro_time` et `system_setup` remplacés par une glue Arduino (`micros()`, `MicroPrintf` vers `Serial`) ;
  - `#include` tiers réécrits ; provenance et licences conservées.
- `tflm_smoke` (modèle 4-8-3 INT8 de 2 368 octets, données synthétiques) :
  - noyaux de référence : 130 080 octets de Flash (13 %), 48 880 octets de RAM globale (18 %), arène utilisée de 788 octets ;
  - Invoke en 233 à 280 µs ;
  - variante CMSIS-NN : 139 560 octets de Flash, Invoke en 113 à 142 µs, sorties identiques sur ces 8 vecteurs.
- **LiteRT desktop n'est pas un oracle bit-exact pour TFLM.** Sur 1 vecteur sur 8, la sortie diffère de 2 LSB, soit 0,008 en probabilité.
  - Cause localisée : la FULLY_CONNECTED par canal de TFLM requantifie un accumulateur int32 avec double arrondi (valeur exacte 28,4977 arrondie à 29), quand LiteRT donne 28.
  - Le runtime TFLM Python (`tflite-micro` pip, Docker linux/amd64) reproduit **8/8** sorties de la carte bit à bit. Détail : `evidence/lot0/lot0-e5-diagnostic.md`.
- **Règle adoptée pour les TP :**
  - golden vectors exacts produits par `tinyml2027.tflm_oracle` : TFLM Python, natif en CI Linux, via Docker sur macOS ;
  - LiteRT desktop en contrôle secondaire : même classe et écart ≤ 4 LSB, écart toujours affiché.
- Un écart d'un LSB sur un logit peut changer la classe quand deux scores sont proches. La comparaison FP32/INT8 du TP03 devra le montrer sur données réelles.

### 11.5 Essais restants du Lot 0
- E3 : compléter ±Y et le mouvement `periodic`.
- E6 : RFFT de 256 points sur la carte (temps, RAM, parité NumPy), avec kissfft déjà présent dans la bibliothèque.
- E7 : cadence pendant le calcul.
- Générateur de dataset synthétique marqué, gabarit de documentation, CI GitHub Actions (Ubuntu, avec l'oracle TFLM natif).

---

## 12. Décision du 23/11/2026 — voie A (bibliothèque officielle) et suppression de la voie B

Sur décision de l'enseignant, la chaîne de référence est la bibliothèque **officielle** `Arduino_TensorFlowLite` (dépôt archivé `tensorflow/tflite-micro-arduino-examples`), au commit `7948b85e020470a30a83bf00e10fc43b486bfcba`. Son code date de la synchronisation du 27/02/2023. Les versions sont figées dans `config/versions.lock`.

La voie B a été **supprimée du dépôt** à la demande de l'enseignant : bibliothèque `TinyML2027_TFLM` générée depuis `tflite-micro` HEAD, glue Arduino, script de génération, oracle Docker et sketch `tflm_smoke`. Les mesures du §11 restent valables comme constats et sont conservées dans `evidence/lot0/` :
- le core Mbed ne compile pas en C++17 sans `-include chrono` ;
- TFLM et LiteRT ne sont pas bit-exacts.

Elles ne décrivent plus la chaîne du cours.

Risques propres à la voie A, à vérifier en phases 3 et 7 :
- bibliothèque de 2023, jamais testée par Google avec `mbed_nano` 4.6.0 (sa CI utilisait l'ancien core `arduino:mbed`) ;
- **pas de quantification par canal des couches denses** dans ce runtime : la conversion INT8 devra utiliser `_experimental_disable_per_channel_quantization_for_dense_layers` (option présente dans TF 2.21) ;
- modèles convertis par TF 2.21 (2026) puis exécutés par un runtime de 2023 : opérateurs et schéma (version 3) à contrôler.
