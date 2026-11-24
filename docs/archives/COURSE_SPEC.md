# TinyML 2027 — Spécification pédagogique

## Vision et périmètre
Construire un système TinyML de bout en bout sur **une seule Arduino Nano 33 BLE Sense (originale LSM9DS1 ou Rev2 BMI270)**. Aucun ESP32, breadboard, capteur, moteur ou serveur cloud payant requis. Un ordinateur Windows 11, macOS (Intel/Apple Silicon) ou Ubuntu Linux, un câble USB de données et la carte suffisent.

Le fil rouge est la reconnaissance de trois **conditions de mouvement**, réalisables sur table et avec prudence :
- `stationary` : carte immobile, posée sur une surface stable ;
- `periodic` : mouvement régulier gauche-droite, d'amplitude modérée ;
- `impact` : brèves impulsions contrôlées en tapotant légèrement la table ou en bougeant la carte par à-coups **sans frapper ni laisser tomber la carte**.

Les labels désignent uniquement des manipulations de laboratoire, jamais un diagnostic de santé d'un moteur. Privilégier un protocole sans équipement additionnel; proposer `punch/flex` du dépôt historique comme **variante** et non comme référence obligatoire : l'orientation des axes, la fixation et la segmentation sont à redéfinir et à tester.

## Contenu et durée cible
| Ordre | Module | Durée cible | Résultat |
|---|---|---|---|
| 0A | Tutoriel Python/Jupyter | 2 h | notebook et figures |
| 0B | Tutoriel Arduino | 30–45 min | Blink, identification carte, IMU |
| 1 | TP01 : du signal au dataset | 4 h | enregistrements CSV, manifest, features |
| 2 | TP02 : modèle TinyML | 4 h | baselines, réseau, évaluation, contrat export |
| 3 | TP03 : embarqué | 4 h | INT8, parité, firmware, mesures réelles |
| A | Extension Edge Impulse | 2–3 h facultatif | mots-clés audio, modèle Arduino |
| B | Extension Edge MLOps | 2–3 h facultatif | versionnage, mise à jour USB, reprise |

Les durées sont des cibles et ne seront confirmées qu'après réalisation complète du parcours.

## Objectifs observables
1. Installer outils et dépendances sans ambiguïté, sur l'OS utilisé.
2. Reconnaître la révision de la carte et lire des échantillons IMU avec unités explicites.
3. Expliquer la fréquence réelle, le fenêtrage, les lacunes et l'anti-aliasing.
4. Constituer un dataset traçable et mettre de côté les acquisitions invalides.
5. Réaliser analyses temporelles et spectrales; calculer les quatre caractéristiques.
6. Entraîner des baselines et un réseau compact; isoler correctement les sessions.
7. Comparer FP32 et INT8 sans toucher au test pour ajuster le modèle.
8. Reproduire le prétraitement en C++ et mesurer l'inférence **sur** la carte.
9. Discuter les limites : dérive, orientation, vitesse d'acquisition, inconnus, bruit, généralisation.

## Règles de documentation étudiante
Pour **chaque** sous-étape : Objectif → Explication courte → Prérequis → Actions numérotées → Commandes Windows/macOS/Linux → Capture vraie / schéma → Résultat attendu → Vérification concrète → Dépannage → Références.
- Écrire en français naturel, ton d'ingénieur, sans slogan et sans texte creux.
- Expliquer chaque commande, chemin, clic IDE et notion nouvelle.
- Décrire les unités, axes, durées, dépendances et hypothèses.
- Ne jamais exposer une capture simulée comme preuve réelle.
- Fournir des exemples de sorties comme **illustrations**, jamais comme résultats mesurés non obtenus.
- Les vrais GIF/illustrations peuvent expliquer les mouvements; les captures IDE et hardware doivent provenir de vrais essais.
- Les notions importantes du cours doivent être justifiées à proximité du code.
- Prévoir pour chaque section une mini-expérience et une question d'interprétation.
- Solutions séparées des énoncés; ne pas masquer du code essentiel derrière un service.
- Utiliser Markdown/MkDocs Material si publication : pas d'obligation de lancer un serveur local pour lire les instructions GitHub.

## Compatibilité et réalisme
- Carte originale : bibliothèque `Arduino_LSM9DS1`; Rev2 : `Arduino_BMI270_BMM150` (vérifier noms de bibliothèques, API et core exacts lors de l'essai).
- Ne pas confondre `Nano 33 BLE` sans Sense et `Nano 33 BLE Sense`; confirmer présence microphone pour extension Edge Impulse.
- `nRF52840` : contraintes RAM/Flash mesurées à la compilation et à l'exécution.
- Les modifications de la chaîne firmware doivent être vérifiées pour chaque révision, sans supposer la compatibilité d'anciennes bibliothèques TensorFlow.
- Les étapes cloud facultatives doivent être clairement séparées des TP principaux.

## Architecture de référence
Acquisition Arduino USB série → fichiers bruts + manifest → inspection/EDA → fenêtres et caractéristiques → splits **par session** → baselines et réseau → modèle float + contrat → quantification INT8 → tests de parité → en-tête C++ + firmware Nano → replay déterministe → acquisition réelle → latence, RAM, Flash.

## Réutilisation du livre et du dépôt historique
- Réutiliser et **adapter** `AIoT-Book/labs/ch07-08-acceleration-features`, `ch09-10-motion-classifier`, `ch11-int8-quantization` : ne pas recopier aveuglément.
- `ch12-nano-esp32-deployment` et `ch13-edge-model-update` sont des **spécifications**, pas une preuve que les firmwares existent.
- `TinyML-for-motor` fournit une variante gestuelle et l'idée de parcours interactif, mais contient des choix vieillissants (port série fixe, API TFLM, 119 échantillons, normalisation). Les refaire proprement.
- Attribution et licences : relever la licence de chaque source avant d'intégrer son code ou ses médias; à défaut reprendre le concept avec implémentation originale.
