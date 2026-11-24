# Campagne de test Windows — rapport

Consignes suivies : `docs/TEST_WINDOWS.md`. Branche `test-windows`. Date : 2026-11-24.

## Poste

| Élément | Valeur |
|---|---|
| Windows | Windows 10 Professionnel, `ver` = 10.0.19045.6456 (consignes écrites pour Windows 11 : **pas testé sous Windows 11**) |
| Processeur | Intel Core i7-3740QM 2,70 GHz (x86_64) |
| Git for Windows | 2.25.1.windows.1 (Git Bash) |
| uv | 0.13.9 |
| Python / TensorFlow / NumPy | 3.12.16 / 2.21.0 / 2.5.5 (installés par `setup.sh`) |
| arduino-cli | 1.5.1 (archive vérifiée SHA-256 par `setup.sh`) |
| Cœur / bibliothèques | `arduino:mbed_nano` 4.6.0 ; Arduino_LSM9DS1 1.1.1 ; Arduino_BMI270_BMM150 1.2.4 ; Arduino_TensorFlowLite 2.4.0-ALPHA |
| Carte | Nano 33 BLE Sense **originale** (`verdict=nano33ble_sense_original`, LSM9DS1), port **COM12**, VID_2341 PID_805A |
| Arduino IDE 2 | non installé : étape 8 non faite |

## Résultats par étape

| # | Étape | Résultat | Preuve |
|---|---|---|---|
| 1 | `setup.sh` | **ÉCHEC** au 1er essai (CRLF), puis **OK** après correctif (3 min 24 s) | `01_setup_echec_crlf.txt`, `01_setup.txt` |
| 2 | Notebooks tutoriel 01 | OK, 4 passed (30 s) | `02_tuto01_notebooks.log` |
| 3 | `pytest -q` | OK, 38 passed, 1 skipped (23 s) | `03_tests.log` |
| 4 | Carte vue | OK, COM12, pilote USB Windows natif (pas de pilote à installer) | `04_board_list.txt` |
| 5 | Blink | OK, téléversement 3,5 s ; LED L ~1 Hz confirmée par la personne présente | `05_blink.txt` |
| 6 | Révision | OK, originale (LSM9DS1 0x68/0x3D, pas de BMI270) | `06_board_identify.txt` |
| 7 | IMU | OK, ~10 lignes/s, carte à plat : az ≈ 0,96 g, orientation `+Z` | `07_imu.txt` |
| 4-8 | Compilations tutoriel 02 (originale + rev2) | OK (567 s) | `04-08_tuto02_compilation.log` |
| 8 | Arduino IDE (captures) | **non fait** (IDE absent) | — |
| 9 | Exemples 03 et 05 (train, convert, compile) | **OK à tort** dans le 1er parcours : la compilation de l'exemple 03 avait échoué (`exit status 0xc0000142`, échec ponctuel de création de processus Windows) mais `compile.sh … \| tail -2` masquait le code de sortie (défaut 6). 2e compilation OK (Flash 142 552 o) | `09_exemples_03_05.log`, `03_custom_model.log`, `09b_*.txt` |
| 9 | Upload + `verify.py` | OK : 03 FP32 écart Nano/LiteRT 2,4·10⁻⁷, `Invoke()` médiane 159 µs, arena 880 o ; 05 INT8 écart ≤ 1 LSB (22/23 codes identiques), médiane 149 µs, arena 820 o | `09_upload_verify.txt`, `09b_*.txt`, `09_verify_*_carte.txt` |
| 10 | TP01 `capture info` | OK : `imu_capture 0.1.0 board_revision=original imu=LSM9DS1 odr_nominal_hz=119.00` | `10_capture_info.txt` |
| 10 | Session guidée, 1er lancement | interrompu avant le 1er geste (`EXIT=127` via `bash.exe` lancé depuis PowerShell, Ctrl-C de l'outil de terminal), rien enregistré ; relancé directement dans PowerShell | `10_guided.sh`, terminal |
| 10 | Session guidée w01 | OK, 3/3 VALIDE : 116,1 Hz mesurés (CV 0,027), 0 rupture, 0 lacune, 17 fenêtres par essai. Le geste `periodic` a été fait dans le sens du câble (écart-type ax 0,105 g contre ay 0,014 g). Hors ligne, le modèle classe les 3 essais 17/17 | `10_capture_guided_w01.txt`, `10_data_w01/` |
| 11 | TP01 features (dataset du dépôt) | OK (3 s) | `11_TP01_features.log` |
| 12 | TP02 | OK : test s05 accuracy **0,961**, macro-F1 0,961, CV 0,864 (= README) | `12_TP02_entrainement.log` |
| 13 | TP03 INT8 + compile `infer_nano` | OK (1148 s) : FP32 0,961 / INT8 0,961, accord 1,000 ; INT8 2176 octets ; Flash 171 504 o (17 %) avec 2 golden vectors (défaut 3), **184 088 o (18 %)** avec les 8 après correctif ; RAM 61 792 o (23 %). Après correctifs : `pytest -q` 39 passed, 1 skipped | `13_*.log`, `13b_*.txt`, `13c_*.txt` |
| 13 | `test_features_cpp.py` | **non exécuté** (skipped : pas de `g++`/`clang++` sous Windows) | `13_TP03_int8_cpp_firmware.log` |
| 13 | Upload `infer_nano` (en-têtes régénérés sous Windows) | OK | `13d_*.txt` |
| 13 | Rejeu `R` | **8/8 OK**, 0 LSB d'écart en entrée et en sortie ; features ≤ 670 µs, `Invoke()` ≤ 136 µs | `13e_rejeu_R_windows.txt` |
| 13 | Direct `L`, 1er essai (3 gestes guidés, 78 s) | immobile : stationary 19/21 ; glisser : periodic 12/23 (+4 fenêtres invalides « lacune » rejetées) ; tapoter : **impact 2/21**. Pendant les tapotements, rms = 0,0005 g = bruit de la carte immobile : les coups n'arrivaient pas sur ax (voir point 9). Prédictions avant les bandeaux : gestes anticipés | `13f_direct_L_windows.txt` |
| 13 | Direct `L`, tapoter seul (35 s) | 2e essai vide : `L` est une bascule et la carte était restée en mode direct (défaut de mon script, corrigé). 3e essai : **impact 28/30** (les 2 autres = fenêtres avant le 1er coup), rms 0,006-0,009 g | `13g_*.txt`, `13h_*.txt` |
| 14 | MLOps `motion-win` | quantize, compile, build, validate OK. `flash` : 1er essai bloqué sur la question de confirmation (masquée par mon script), 2e essai **ÉCHEC `WinError 193`** (défaut 7), 3e essai après correctif **CONFIRMÉ** (version, SHA-256 `c9219c49…`, rejeu OK) ; `status` : souhaité = confirmé = annoncé = motion-win | `14_mlops.txt`, `14b_*.txt`, `14c_*.txt` |
| 15 | Remise du firmware du cours | OK : en-têtes du dépôt restaurés, compile (184 088 o), upload, `R` : `model_version=motion-v1`, sha `023e01b8…`, rejeu 8/8. `release status` signale bien l'écart (souhaité/confirmé motion-win, carte motion-v1) : un `upload.sh` hors `release flash` ne met pas à jour l'état MLOps | `15_remise_motion_v1.txt`, `15b_rejeu_motion_v1.txt` |

Parcours sans carte relancé en un bloc par `bash evidence/windows/parcours.sh` : `parcours-sans-carte-windows10.txt`.

## Défauts trouvés sous Windows et correctifs (non committés)

1. **Fins de ligne CRLF** — Git for Windows active `core.autocrlf=true` ; `config/versions.lock` arrive en CRLF et `setup.sh` échoue (`printf: \`': not a valid identifier`). Correctifs : `.gitattributes` (`config/versions.lock text eol=lf`) et `tr -d '\r'` dans `setup.sh`, `setup_esp.sh`, `compile.sh`, `upload.sh` (défense si le fichier a déjà été extrait en CRLF).
2. **Encodage cp1252** — 66 lectures/écritures de fichiers texte sans `encoding=` dans `python/`, `src/`, `tests/`. Sous Windows, les en-têtes générés (`model_data.h`, `test_vectors.h`, `golden.h`, `model_params.h`) étaient réécrits en ISO-8859/cp1252 (« g�n�r� ») et en CRLF ; un caractère hors cp1252 aurait fait planter l'écriture. Correctif : `encoding="utf-8"` partout, `newline="\n"` sur toutes les écritures (mêmes octets sur les 3 OS) ; nouveau test `tests/test_text_encoding.py` (66 oublis détectés sur l'ancien code, 0 après).
3. **Golden vectors réduits en silence** — `quantize_motion` lit `data/` par défaut. Dans un clone neuf (parcours sans carte), `data/` n'existe pas : `golden.h` ne contenait que les **2** vecteurs synthétiques au lieu de 8, sans erreur. Pas propre à Windows. Correctif : arrêt explicite avec message (`--data datasets/motion-nano-v1`). Avec cette option, `golden.h` régénéré sous Windows est **identique** à celui du dépôt (hors fins de ligne) : prétraitement Python identique macOS/Windows.
4. **Chemin Windows dans un artefact** — `training_config.json` contenait `"results\\tp01\\features.csv"` ; correctif : `as_posix()`.
6. **Échec de compilation masqué (dans mon script de campagne, pas dans le cours)** — `bash -c "… | tail -2"` sans `pipefail` a noté OK une compilation échouée. `evidence/windows/parcours.sh` utilise maintenant `bash -o pipefail`. `compile.sh` renvoie bien le bon code.
7. **`release flash` impossible sous Windows** — `release.py` lançait `scripts/arduino.sh` par `subprocess` : `OSError: [WinError 193]`. Correctif : fonction `arduino_cli()` qui appelle `arduino-cli(.exe)` avec le même environnement isolé, sans bash (depuis PowerShell, `bash` peut être celui de WSL). Test `tests/test_arduino_cli_python.py`.
8. **Consigne de glissement contradictoire** — `capture.py` affichait « de gauche à droite », le README du TP01 dit « dans le sens du câble ». Le modèle n'utilise que `ax` : glisser en travers donnerait un `periodic` faible. Texte de l'outil aligné sur le README.
9. **Risque pédagogique, `impact` sur `ax` seul** — les tapotements se voient surtout sur `az` (w01 : écart-type 0,013 g contre 0,004 g sur ax). Des coups plus doux, ou un autre point de la table, donnent `stationary` (1er essai en direct : 2/21). À documenter dans le TP03 (« tapotez comme à la capture »), ou à reprendre dans le contrat de features.
5. Affichage console : sans `PYTHONIOENCODING=utf-8`, les accents des messages Python sont mal affichés dans Git Bash (cosmétique, journaux 09 et 13). Non corrigé : à décider (variable dans `scripts/` ou consigne dans le tutoriel).

## Différences avec macOS

- Les poids réentraînés diffèrent légèrement (SHA-256 INT8 Windows `c9219c49…` contre `023e01b8…` dans le dépôt ; exemple 03 `8adc218b…` contre `6990a391…`) : TensorFlow/oneDNN n'est pas bit-à-bit reproductible entre OS/CPU. Les métriques TP02/TP03 sont identiques. Les en-têtes du dépôt (motion-v1) restent la référence ; ils doivent être remis avant le rejeu (étape 15).
- Compilation ~3× plus lente que sur le Mac (CPU de 2012).

## Reste à faire

- Étape 8 (captures Arduino IDE) : IDE non installé.
- `tests/test_features_cpp.py` sous Windows : demande un compilateur C++ hôte (MSYS2/MinGW). Décision de l'enseignant.
- Carte Rev2 et Windows 11 : non testés.
- README à reprendre après relecture : `--data datasets/motion-nano-v1` pour le TP03 sans carte ; consigne « tapotez comme à la capture » ; risque `impact` lié à `ax` seul.

Les en-têtes générés pendant la campagne (modèles réentraînés sous Windows) ont été remis à la version du dépôt : seuls les correctifs de code et les preuves sont committés.
