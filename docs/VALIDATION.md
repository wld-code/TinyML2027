# Validation, systèmes et captures — registre initial

**État au 23/11/2026.** Une seule combinaison est validée sur matériel : **macOS 15.6 (Apple Silicon) + Nano 33 BLE Sense originale (LSM9DS1)**. Les références du livre ne constituent pas une validation du présent dépôt.

| Élément | macOS Apple Silicon + originale | Preuve |
|---|---|---|
| Installation `scripts/setup.sh`, 39 tests pytest, 4 notebooks | exécuté | `uv run pytest`, `--nbmake` |
| Blink, identification de la carte | validé sur matériel | evidence/phase2, evidence/lot0 |
| `hello_world` officiel TFLM | validé sur matériel (LED) | evidence/phase3 |
| Modèle sinus FP32 et INT8 (exemples 03 et 05) | validé sur matériel | evidence/phase5 |
| IMU : cadence, 6 orientations, gyroscope | validé sur matériel | evidence/phase6 |
| TP01 : acquisition de 5 sessions | validé sur matériel | evidence/tp01 |
| TP03 : rejeu 8/8, direct sur 3 gestes | validé sur matériel | evidence/tp03 |
| MLOps : refus avant téléversement, v1 → v2 → échec → retour à v1 | validé sur matériel | evidence/mlops |
| Micro PDM | validé sur matériel (niveau ambiant et claquements de mains) | evidence/edge-impulse |
| Edge Impulse (Studio, export) | validé sur matériel (Nano V1, macOS 15.6) : test Studio 80,67 %, export compilé et exécuté ; voix réelle médiocre sur « stop » ; Rev2 non testée | evidence/edge-impulse |
| Firmwares Rev2 (`REV=rev2`) | compilé seulement | build logs |
| CI GitHub Actions (`.github/workflows/ci.yml`, Windows/Linux/macOS) | **non exécutée** : les jobs ne démarrent pas (facturation du compte GitHub, dépôt privé) | — |
| Parcours sans carte dans un **Linux neuf** (Debian 12 arm64, conteneur, clone propre) | exécuté : 9/9 étapes OK, TP02 test 0,961 / CV 0,864 comme sur macOS ; modèle INT8 de même taille mais SHA-256 différent ; `infer_nano` 171 152 octets contre 183 968 sur macOS (écart non expliqué) | evidence/linux |

## Matrice de vérification
| Cas | Sans matériel (CI) | Originale LSM9DS1 | Rev2 BMI270 |
|---|---|---|---|
| Windows 11 | à réaliser (consignes : docs/TEST_WINDOWS.md) | à réaliser | à réaliser |
| macOS Intel | à réaliser | à réaliser | à réaliser |
| macOS Apple Silicon | exécuté en local (CI non lancée) | **validé** (23/11/2026) | compilé seulement |
| Ubuntu LTS | Debian 12 arm64 en conteneur : exécuté (23/11/2026) ; Ubuntu x86-64 à réaliser | à réaliser | à réaliser |

Ne cocher une combinaison qu'avec OS/version, carte exacte, paquet Arduino, bibliothèque IMU, runtime, commandes, date, résultats et captures/logs correspondants. Les tests CI ne prouvent pas que l'USB, la compilation ou le capteur fonctionnent.

## Tests automatisés requis
1. Environnement Python : imports, versions pinées, installation propre, exécution `pytest`.
2. Série : liste des ports, protocole, timeout, erreurs CRC/format si protocole encadré, perte d'une trame, déconnexion simulée.
3. Dataset : échantillon invalide, doublons, timestamps non-monotones, fréquence réelle, annotation simulée.
4. Features : vecteur constant, sinusoïde connue, bruit, zéros, fenêtre incomplète, FFT/PSD; référence numérique vérifiable.
5. Apprentissage : split par session, fuite impossible, métriques, export cohérent, ordre des classes.
6. Quantification : int8 réel de bout en bout, opérateurs supportés, scales et zero-points, parité sur golden vectors.
7. Firmware : compilation Arduino CLI originale et Rev2 au minimum lorsque toolchain disponible; parité replay sur carte réelle à part.
8. Docs : liens internes, blocs de commande, assets présents, captures légendées.

## Preuves et screenshots
Chaque screenshot : nom `tpXX-etapeYY-os-carte.png`; légende avec OS/version et étape; ne jamais fabriquer une réussite.
- Python : version de Python, environnement actif, notebook exécuté, figures signal.
- Arduino : Boards Manager, sélection révision/port, compilation, téléversement, moniteur série IMU.
- TP01 : sélection port, enregistrement, QC, EDA, FFT, PSD, spectrogramme, `features.csv`.
- TP02 : partition par session, baseline, courbes, matrice, fichier modèle et contrat.
- TP03 : quantification et inspection, compilation Nano, sortie replay/parité, classes en live, occupation flash/RAM, latence.
- Extensions : acquisition Edge Impulse, DSP et déploiement; MLOps v1/v2, erreur de manifeste et restauration USB.

Tout élément non capturé est un `TODO: CAPTURE RÉELLE` explicite. Une image de terminal générée artificiellement est interdite comme preuve.

## Critères de fin
Une personne novice doit pouvoir cloner, préparer l'environnement, identifier sa carte, capturer, inspecter, entraîner, quantifier, téléverser, rejouer un vecteur témoin, observer les prédictions, et comprendre les limites. Le parcours ne dépend pas d'une seconde carte ni d'un logiciel payant.

## Bugs documentés
Chaque incident : version/OS/carte, procédure de reproduction, sortie brute, hypothèse, correction, retest. Ne déclarer « supporté » qu'après retest.
