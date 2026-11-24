# Validation : ce qui a été testé, et où

Un résultat n'est annoncé que s'il a été obtenu pour de vrai. Chaque ligne porte l'un de ces statuts :

| Statut | Sens |
|---|---|
| **validé sur matériel** | exécuté sur une vraie carte, résultat observé et enregistré |
| **exécuté** | lancé sur l'ordinateur, sans carte |
| **compilé** | le firmware compile, mais n'a pas tourné sur une carte |
| **non testé** | rien n'a été lancé |

## Matrice systèmes × cartes

| Système | Sans carte | Nano 33 BLE Sense originale | Rev2 |
|---|---|---|---|
| macOS 15.6, Apple Silicon | exécuté | **validé sur matériel** (23/11/2026) | compilé |
| Linux Debian 12 arm64 (conteneur, clone neuf) | exécuté (23/11/2026) | non testé | non testé |
| Windows 10 Pro 22H2 | en cours ([consignes](TEST_WINDOWS.md)) | en cours | non testé |
| Windows 11, macOS Intel, Ubuntu x86-64 | non testé | non testé | non testé |

## Détail (macOS 15.6 + carte originale)

| Élément | Statut | Preuve |
|---|---|---|
| Installation, tests automatiques, 4 notebooks | exécuté | `uv run pytest`, `--nbmake` |
| Blink, identification de la carte | validé sur matériel | [phase2](../evidence/phase2/), [lot0](../evidence/lot0/) |
| Exemple officiel `hello_world` | validé sur matériel | [phase3](../evidence/phase3/) |
| Modèle sinus FP32 et INT8 (exemples 03 et 05) | validé sur matériel | [phase5](../evidence/phase5/) |
| IMU : cadence, 6 orientations, gyroscope | validé sur matériel | [phase6](../evidence/phase6/) |
| TP01 : 5 sessions enregistrées | validé sur matériel | [tp01](../evidence/tp01/) |
| TP02 : entraînement et test sur s05 | exécuté (données réelles) | [TP02](../labs/02-model-training/README.md) |
| TP03 : rejeu 8/8, direct sur 3 gestes | validé sur matériel | [tp03](../evidence/tp03/) |
| MLOps : refus, v1 → v2 → échec → retour à v1 | validé sur matériel | [mlops](../evidence/mlops/) |
| Micro PDM | validé sur matériel | [edge-impulse](../evidence/edge-impulse/) |
| Edge Impulse : Studio, export, essai sur la carte | validé sur matériel ; voix réelle médiocre sur « stop » | [edge-impulse](../evidence/edge-impulse/) |
| Firmwares Rev2 (`REV=rev2`) | compilé | — |

## Autres systèmes

- **Linux** ([preuves](../evidence/linux/)) : 9 étapes sur 9 sans carte. TP02 identique à macOS (test 0,961). Le modèle INT8 a la même taille mais un SHA-256 différent : l'entraînement n'est pas identique au bit près d'une machine à l'autre. `infer_nano` fait 171 152 octets de Flash contre 183 968 sur macOS : **écart non expliqué**.
- **Windows 10** : campagne en cours. Sans carte, les étapes testées donnent les mêmes chiffres que macOS. Deux défauts du dépôt ont été trouvés (fins de ligne CRLF, accents dans Git Bash) et corrigés ; la correction reste à revérifier sous Windows. Un prérequis manquait : le Visual C++ Redistributable.
- **CI GitHub Actions** ([workflow](../.github/workflows/ci.yml)) : écrite pour Windows, Linux et macOS, mais **jamais exécutée** (les jobs ne démarrent pas sur ce compte).

## Règle pour ajouter une ligne

Ne marquez une combinaison comme testée qu'avec : système et version, carte exacte, commandes lancées, date, résultats obtenus et journaux ou captures. Les tests sans carte ne prouvent pas que l'USB, le téléversement ou le capteur fonctionnent.
