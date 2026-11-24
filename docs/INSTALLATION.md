# Installation

Tout s'installe **dans le dossier du projet**. Votre Python système et votre installation Arduino ne sont pas modifiés.

| Dossier | Contenu | Taille |
|---|---|---|
| `.venv/` | Python 3.12 et les bibliothèques verrouillées (TensorFlow, NumPy, Jupyter…) | 1,8 Go |
| `.arduino/` | Arduino CLI 1.5.1, core Mbed OS Nano 4.6.0, compilateur ARM, bibliothèques | 0,9 Go |

Prévoyez **3 Go libres** et une connexion Internet. Ensuite, tout fonctionne hors ligne. Pour repartir de zéro : supprimez ces deux dossiers et relancez `./scripts/setup.sh`.

## 1. Outils de base

Il faut `git` et le gestionnaire Python [uv](https://docs.astral.sh/uv/).

**macOS**
```sh
xcode-select --install      # git ; ignorez l'erreur s'il est déjà installé
brew install uv             # Homebrew : https://brew.sh
```

**Linux (Debian, Ubuntu)**
```sh
sudo apt install git curl g++
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows 10 ou 11**
1. Installez [Git for Windows](https://git-scm.com/download/win). Il fournit **Git Bash** : toutes les commandes du cours se lancent dans Git Bash, pas dans PowerShell.
2. Installez uv, dans PowerShell :
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
3. Installez le [Visual C++ Redistributable x64](https://aka.ms/vs/17/release/vc_redist.x64.exe) récent. Sans lui, TensorFlow ne se charge pas (`DLL load failed`).

**Contrôle :** `git --version` et `uv --version` affichent une version.

## 2. Récupérer le dépôt

```sh
git clone https://github.com/wld-code/TinyML2027.git
cd TinyML2027
```

Toutes les commandes du cours se lancent **depuis ce dossier**.

## 3. Tout installer

```sh
./scripts/setup.sh
```

Le script :
1. télécharge Arduino CLI 1.5.1 et **s'arrête si son empreinte SHA-256 n'est pas la bonne** ;
2. installe le core `arduino:mbed_nano@4.6.0` et les bibliothèques des deux IMU ;
3. récupère `Arduino_TensorFlowLite` au commit figé ;
4. crée `.venv/` avec `uv sync --frozen`, qui refuse toute version différente de `uv.lock`.

**Résultat attendu (fin de la sortie) :**
```text
arduino:mbed_nano 4.6.0
Arduino_LSM9DS1        1.1.1
Arduino_TensorFlowLite 2.4.0-ALPHA
Python 3.12.7 | TensorFlow 2.21.0 | NumPy 2.5.5
```

**Contrôle :**
```sh
uv run pytest -q
```
Tous les tests passent (un test est ignoré tant que le TP03 n'a pas généré ses golden vectors).

> N'utilisez pas `pip install` dans le Python du système : `uv run` utilise toujours le Python du projet.

## 4. Brancher la carte

La suite (Blink, identification de la carte, lecture de l'IMU) est dans le [tutoriel 02](../tutorials/02-arduino-nano/README.md).

## Arduino IDE 2 (facultatif)

Le cours utilise les scripts du dépôt, dont les versions sont figées. Vous pouvez aussi travailler à la souris dans [Arduino IDE 2](https://www.arduino.cc/en/software) : le [tutoriel 02](../tutorials/02-arduino-nano/README.md#arduino-ide-pas-à-pas) montre chaque clic. L'IDE utilise ses propres dossiers, pas ceux du projet.

## Dépannage

| Problème | Solution |
|---|---|
| `uv: command not found` | rouvrez le terminal après l'installation de uv |
| Windows : `printf: '': not a valid identifier` | clone fait avant la correction des fins de ligne : refaites un `git clone` |
| Windows : `DLL load failed while importing _pywrap_tensorflow_internal` | installez le Visual C++ Redistributable x64 récent |
| Windows : compilation en échec avec `exit status 0xc0000142` | échec ponctuel au lancement d'un processus Windows : relancez la même commande |
| `Espace insuffisant sur le disque` / `No space left on device` | libérez 3 Go |
| Linux : port série `permission denied` | ajoutez-vous au groupe `dialout` (`sudo usermod -aG dialout $USER`), puis rouvrez la session ; jamais `chmod 777` |
| Clone HTTPS refusé (`could not read Username`) | le dépôt est privé : connectez-vous à GitHub ou utilisez l'adresse SSH `git@github.com:wld-code/TinyML2027.git` |

## Versions figées

| Composant | Version | Fichier |
|---|---|---|
| Arduino CLI | 1.5.1 (SHA-256 vérifié) | `config/versions.lock` |
| Core | `arduino:mbed_nano@4.6.0` | `config/versions.lock` |
| Arduino_LSM9DS1 / Arduino_BMI270_BMM150 | 1.1.1 / 1.2.4 | `config/versions.lock` |
| Arduino_TensorFlowLite | commit `7948b85e` (dépôt officiel) | `config/versions.lock` |
| Python | 3.12 | `.python-version` |
| TensorFlow / NumPy | 2.21.0 / 2.5.5 | `uv.lock` |

**Pourquoi Python 3.12 ?** TensorFlow 2.21 ne publie ses paquets que pour Python 3.10 à 3.13, et NumPy 2.5 exige au moins 3.12.
