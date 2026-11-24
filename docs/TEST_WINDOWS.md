# Campagne de test Windows — consignes pour l'agent (ou la personne) qui teste

> **Première campagne faite** le 24/11/2026 sur Windows 10 : voir le [rapport](../evidence/windows/RAPPORT.md). À refaire sur un clone neuf pour confirmer les correctifs, puis sous Windows 11 et avec une Rev2.

**But :** refaire tout le parcours du cours sur un **vrai PC Windows**, avec la carte Nano 33 BLE Sense, et rapporter des **preuves réelles** (journaux et captures d'écran). Ces consignes peuvent être suivies par une personne ou par Claude Code lancé sur le PC Windows.

## Règles (non négociables)

1. **Aucune capture ni aucun résultat inventé.** Une étape qui échoue est notée ÉCHEC, avec le message exact. Ne jamais « arranger » une sortie.
2. Ne rien installer ni modifier en dehors de ce qui est listé ci-dessous. Ne pas toucher à une installation Arduino existante (`%LOCALAPPDATA%\Arduino15`, `Documents\Arduino`).
3. Toute action sur la carte (brancher, appuyer sur RESET, faire un geste) : **demander à la personne présente**, une action à la fois, et attendre sa réponse.
4. Ne **jamais** pousser sur `main` ni sur `cours-v1-nano`. Les résultats vont sur une branche **`test-windows`**, poussée seulement avec l'accord de la personne.
5. Ne pas mettre de chemin contenant le nom d'utilisateur Windows dans les captures (utiliser `cd` puis des chemins relatifs ; recadrer sinon).

## 0. Prérequis (une fois)

| Outil | Comment | Vérification |
|---|---|---|
| Git for Windows (fournit **Git Bash**) | <https://git-scm.com/download/win> | `git --version` |
| uv | PowerShell : `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` | `uv --version` |
| Microsoft Visual C++ Redistributable x64 **récent** (TensorFlow en a besoin) | <https://aka.ms/vs/17/release/vc_redist.x64.exe> | Paramètres → Applications : « Microsoft Visual C++ 2015-2022 Redistributable (x64) », 14.40 ou plus |
| Arduino IDE 2 (pour la partie IDE) | <https://www.arduino.cc/en/software> | menu Aide → À propos |

Prévoir **environ 3 Go libres** : 1,8 Go pour `.venv` (TensorFlow) et 0,9 Go pour `.arduino`.

Toutes les commandes du cours se lancent dans **Git Bash**, pas dans PowerShell ni cmd.

Tant que le dépôt est **privé**, le clone HTTPS demande une connexion GitHub ; sans elle, il échoue avec « could not read Username for 'https://github.com' ». Utiliser alors l'adresse SSH `git@github.com:wld-code/TinyML2027.git` (clé SSH enregistrée sur GitHub).

```sh
git clone https://github.com/wld-code/TinyML2027.git
cd TinyML2027
git checkout cours-v1-nano
git checkout -b test-windows
mkdir -p evidence/windows docs/screenshots/windows
```

Notez dans `evidence/windows/README.md` : version de Windows (`cmd /c ver`), processeur, version de Git, uv, Arduino IDE, et la révision de la carte (originale ou Rev2, voir tutoriel 02 étape 3).

## 1. Captures d'écran sous Windows

Terminal : capturer **uniquement la fenêtre** Git Bash, après avoir lancé la commande. Sans outil graphique, cette commande PowerShell capture la fenêtre au premier plan :

```powershell
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class W { [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
public struct R { public int L, T, Ri, B; } }
"@
Start-Sleep 2; $r = New-Object W+R; [W]::GetWindowRect([W]::GetForegroundWindow(), [ref]$r) | Out-Null
$b = New-Object Drawing.Bitmap ($r.Ri-$r.L), ($r.B-$r.T); $g = [Drawing.Graphics]::FromImage($b)
$g.CopyFromScreen($r.L, $r.T, 0, 0, $b.Size); $b.Save("$PWD\capture.png")
```

Nommage : `docs/screenshots/windows/<étape>-windows11-<original|rev2>.png` (par exemple `tuto02-etape01-board-list-windows11-original.png`). Une capture par étape listée ci-dessous.

## 2. Parcours à refaire (dans l'ordre)

Pour chaque étape : lancer la commande, comparer au « résultat attendu » du README correspondant, enregistrer la sortie complète dans `evidence/windows/<étape>.txt`, faire la capture, noter OK / ÉCHEC.

| # | Étape | Commande(s) | Carte ? |
|---|---|---|---|
| 1 | Préparer le poste | `./scripts/setup.sh` | non |
| 2 | Tutoriel 01 — notebooks | `uv run pytest --nbmake tutorials/01-python-jupyter -q` puis `uv run jupyter lab tutorials/01-python-jupyter/notebooks` (capture du notebook 03) | non |
| 3 | Tests automatiques | `uv run pytest -q` | non |
| 4 | Tutoriel 02 étape 1 — la carte est vue | `./scripts/arduino.sh board list` (port `COMx`) | **oui** |
| 5 | Tutoriel 02 étape 2 — Blink | `./scripts/compile.sh examples/01_blink` puis `./scripts/upload.sh examples/01_blink` ; la LED L clignote ? (demander) | **oui** |
| 6 | Tutoriel 02 étape 3 — révision | `board_identify` (compile, upload, moniteur, Entrée) | **oui** |
| 7 | Tutoriel 02 étape 4 — IMU | `examples/04_imu` + moniteur 115200 | **oui** |
| 8 | Tutoriel 02 — Arduino IDE | refaire les 8 captures de la section « Arduino IDE pas à pas » (gestionnaire de cartes, bibliothèques, choix du port COM, Verify, Upload, moniteur) | **oui** |
| 9 | Exemples 03 et 05 | `python/train.py`, `convert.py --mode fp32/int8`, compile, upload, `python/verify.py --mode … --port COMx` | **oui** |
| 10 | TP01 — acquisition | `uv run python -m tinyml2027.capture info` puis **une** session guidée courte `capture guided --session w01` (la personne fait les gestes) | **oui** |
| 11 | TP01 sans carte | `uv run python -m tinyml2027.build_features --data datasets/motion-nano-v1` | non |
| 12 | TP02 | `uv run python -m tinyml2027.train_motion --test-session s05` (comparer aux chiffres du README : test 0,961) | non |
| 13 | TP03 | `quantize_motion --data datasets/motion-nano-v1`, `pytest tests/test_features_cpp.py`, compile + upload `infer_nano`, moniteur : `R` (rejeu 8/8 attendu) puis `L` (direct, 3 gestes) | **oui** |
| 14 | MLOps | `release build --version motion-win`, `validate`, `flash`, `status` | **oui** |
| 15 | Fin | remettre le firmware du cours : `git checkout labs/03-embedded-inference/firmware/infer_nano` (en-têtes motion-v1 du dépôt), puis `compile.sh` + `upload.sh` de `infer_nano` ; vérifier `# model_version=motion-v1` avec `R` | **oui** |

Une carte **Rev2** : ajouter `REV=rev2` devant chaque `compile.sh` / `upload.sh`, et noter les résultats séparément.

## 3. Points Windows à surveiller (et à noter s'ils arrivent)

Déjà rencontrés lors du premier essai (Windows 10 Pro 22H2, 24/11/2026) :

| Symptôme | Cause | Remède |
|---|---|---|
| `setup.sh: line 14: printf: '': not a valid identifier` | Git for Windows extrait les fichiers en CRLF (`core.autocrlf=true`) | corrigé dans le dépôt (`.gitattributes` : LF partout ; `setup.sh` tolère le CRLF). Sur un clone fait avant la correction, **sans modification locale** à garder : `git pull` puis `git rm --cached -r -q . && git reset --hard` (attention : efface les modifications non commitées des fichiers suivis) |
| `ImportError: DLL load failed while importing _pywrap_tensorflow_internal` | Visual C++ Redistributable trop ancien (14.28) | installer le Redistributable x64 récent (prérequis ci-dessus) |
| `Espace insuffisant sur le disque (os error 112)` pendant `uv sync` | disque presque plein | libérer environ 3 Go |
| accents cassés dans Git Bash (« fen▒tres ») | Python écrit en cp1252 hors console Windows | corrigé dans le dépôt (sortie forcée en UTF-8) |
| en-têtes `.h` générés en cp1252 et CRLF (« g�n�r� ») | fichiers ouverts sans `encoding=` | corrigé : UTF-8 et LF imposés, test `tests/test_text_encoding.py` |
| `release flash` : `OSError: [WinError 193]` | Python lançait `scripts/arduino.sh`, que Windows ne sait pas exécuter | corrigé : `release.py` appelle `arduino-cli.exe` directement |
| compilation : `exit status 0xc0000142` | échec ponctuel au lancement d'un processus | relancer ; vérifier le code de sortie (`set -o pipefail` si la sortie passe par `tail`) |

- Ports `COMx` et pilote USB de la carte (Gestionnaire de périphériques).
- Fins de ligne : erreur `$'\r': command not found` dans un script `.sh`.
- Chemins avec espaces ou accents dans le nom d'utilisateur.
- `uv sync` : une dépendance sans paquet pour Windows (par exemple LiteRT).
- Port occupé : fermer le moniteur série de l'IDE avant les scripts Python.
- Antivirus qui bloque `arduino-cli.exe` ou le téléversement.

## 4. Rapport

`evidence/windows/RAPPORT.md` : tableau des 15 étapes (OK / ÉCHEC / non fait), messages d'erreur exacts, chiffres obtenus (TP02, TP03 rejeu, tailles Flash/RAM), différences avec macOS. Puis, **avec l'accord de la personne** :

```sh
git add evidence/windows docs/screenshots/windows
git commit -m "Test Windows : journaux et captures"
git push -u origin test-windows
```

Ne modifier aucun README : l'intégration dans le cours se fera après relecture.
