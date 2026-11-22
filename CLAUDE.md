# Mission Claude Code — Construire TinyML2027

Tu es chargé de transformer les cahiers des charges du dépôt en **véritables tutoriels et TP TinyML prêts pour l'enseignement**. Ton objectif est d'obtenir des contenus pédagogiques clairs, actuels, exécutables et robustes sur Windows/macOS/Linux avec **une seule Arduino Nano 33 BLE Sense** (originale ou Rev2). Ne développe pas tout d'un coup. Les documents sont actuellement des spécifications, pas des résultats validés.

## Obligations initiales
1. Lire intégralement `README.md`, `docs/COURSE_SPEC.md`, `docs/DATA_CONTRACT.md`, `docs/VALIDATION.md`, les deux tutoriels, trois TP et deux extensions.
2. Auditer les sources existantes `wld-code/AIoT-Book/labs` (ch07-08, ch09-10, ch11, ch12, ch13 et tutoriels Arduino) et `wld-code/TinyML-for-motor`. Vérifier leurs licences et conserver les attributions.
3. Vérifier en ligne **au moment de l'implémentation** les versions Python, TensorFlow/LiteRT, TFLM, Arduino CLI, Arduino Mbed OS Nano, bibliothèques IMU/PDM, dépendances et support OS. Figer un environnement réellement compatible (versions et lockfile). N'affirme pas une compatibilité sur la base d'un exemple ancien.
4. Proposer d'abord un rapport `docs/AUDIT.md` : état de l'existant, changements, risques, dépendances, choix de modèle et matrice de tests. Aucune migration aveugle.
5. Confirmer le contrat des quatre features du livre et sa faisabilité **C++ sur Nano**, en particulier fréquence dominante et band power qui exigent une méthode spectrale. Si trop coûteux, proposer et tester un autre contrat **avant** d'entraîner quoi que ce soit; documenter les conséquences.
6. Toute nouvelle fonctionnalité doit inclure tests reproductibles, documentation et critère d'acceptation observable.

## Démarche par lots validés
Lot 0 — audit, versions, matrice, générateur dataset d'exemple et convention de documentation.
Lot 1 — tutoriel Python avec notebooks autonomes et tests sur 3 OS.
Lot 2 — tutoriel Arduino avec sketches Blink + IMU et tests de compilation; **demander à l'enseignant de connecter sa carte** pour les tests physiques.
Lot 3 — TP01 acquisition, séquences, fenêtres, figures, protocole des mouvements, données et tests.
Lot 4 — TP02 split, apprentissage, baselines, export float et golden vectors.
Lot 5 — TP03 INT8, replay, firmware TFLM, mesures hardware, revue sécurité/robustesse.
Lot 6 — Edge Impulse facultatif, capture audio intégrée, documentation et vérifications.
Lot 7 — MLOps facultatif, manifest, mise à jour USB et rollback, tests.
Lot 8 — QA transversale, documentation MkDocs, CI, captures réelles, parcours complet de zéro.

**À la fin de chaque lot :** fournir fichiers modifiés, commandes exécutées, environnement précis, tests réussis/échoués, preuves, points restant à tester matériellement et demander validation avant lot suivant. Ne pas développer tous les lots simultanément ni déclarer le cours « terminé » sans preuves.

## Rédaction
Texte en français technique, naturel et pédagogique; pas de prose publicitaire ou de « style IA ». Chaque étape : objectif, pourquoi, matériel/prérequis, actions numérotées, commande ou clic exact Windows/macOS/Linux, figure/screenshot, résultat attendu, contrôle, dépannage, référence. Préférer phrases et schémas simples. Les définitions mathématiques doivent mentionner unités, hypothèses et indices. Chaque notebook doit pouvoir être exécuté intégralement depuis le haut.

Captures d'écran **réelles**, associées à une version vérifiée; ne jamais générer de fausses preuves de build ou de matériel. Si tu ne peux pas agir sur une carte/OS, insérer une tâche explicite et demander la manipulation manuelle à l'enseignant. Ajouter si nécessaire GIF originaux / schémas pour `stationary`, `periodic`, `impact`; ne pas réutiliser sans vérifier droits. Indiquer les limites des jeux de données synthétiques.

## Restrictions techniques
- Pas d'ESP32, moteurs, shield, breadboard, micro externe, capteur externe, AWS ou autre cloud payant dans le parcours obligatoire.
- Les deux révisions de la Nano Sense ont des IMU différentes; créer une couche d'abstraction claire, et compiler/tester chacune.
- Ne pas forcer un port série, une fréquence ou un modèle supposés compatibles.
- Ne pas masquer une déconnexion, perte de trame, erreur de cadence, ensemble de test contaminé, erreur d'opérateur TFLM ou échec d'allocation mémoire.
- Prétraitement de la carte = celui de Python, avec golden vectors, tests de tolérance et manifest des paramètres.
- Réaliser replay numérique C++ **avant** acquisition live. Aucun « 100 % d'accuracy » sans test indépendant.
- Ne pas contaminer le jeu de test avec calibration, standardisation ou réglage d'hyperparamètres.
- Comparer FP32 vs INT8 sur mêmes fenêtres; INT8 ne garantit pas un fichier plus petit pour de très petits modèles.
- Déploiement, versionnement et rollback MLOps doivent utiliser **USB supervisé**, pas une OTA imaginée.
- L'extension Edge Impulse peut nécessiter Internet et un compte; les 3 TP doivent fonctionner hors service cloud.
- Ne jamais effacer des fichiers historiques ou mélanger les sources sans demande explicite.
- CI GitHub Actions pour code sans matériel; matériel requis pour la validation réelle de chaque combinaison OS/révision.

## Critères finaux
Un étudiant novice peut, sans modifier de constantes secrètes, préparer son poste, identifier sa carte, vérifier les capteurs, enregistrer des mouvements contrôlés, contrôler son dataset, calculer features, entraîner un modèle, mesurer ses erreurs, quantifier en INT8, téléverser et observer inférence live; une personne sans carte peut exécuter les parties prévues pour simulation sans confondre simulation et expérience.

## Première mission à effectuer
**Commence uniquement par le Lot 0.** Rédige `docs/AUDIT.md` avec références et versions, propose un plan de modernisation vérifiable, liste les questions/essais matériels à effectuer, et soumets les risques pédagogiques et embarqués. N'implémente pas encore les huit lots.
