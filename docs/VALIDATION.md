# Validation, systèmes et captures — registre initial

**État actuel : aucun des nouveaux TP de TinyML2027 n'a encore été testé sur du matériel.** Les références du livre ne constituent pas une validation du présent dépôt.

## Matrice de vérification
| Cas | Sans matériel (CI) | Originale LSM9DS1 | Rev2 BMI270 |
|---|---|---|---|
| Windows 11 | à réaliser | à réaliser | à réaliser |
| macOS Intel | à réaliser | à réaliser | à réaliser |
| macOS Apple Silicon | à réaliser | à réaliser | à réaliser |
| Ubuntu LTS | à réaliser | à réaliser | à réaliser |

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
