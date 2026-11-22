# TP01 — Du capteur au dataset TinyML

**Statut : cahier des charges, pas encore une séance matériellement validée.** Durée cible : 4 h. Requis : Nano 33 BLE Sense originale ou Rev2, ordinateur, USB data, tutoriels préparatoires.

## Mission
Faire trois manipulations reproductibles (`stationary`, `periodic`, `impact`) en utilisant l'accéléromètre intégré. Contrôler les mesures, visualiser les composantes temporelles et fréquentielles, calculer les quatre caractéristiques du contrat et produire une table utilisable en TP02. Ne jamais confondre les trois manipulations avec des diagnostics moteur. Aucun moteur ni objet additionnel n'est requis.

## Objectifs
Savoir identifier les axes, unités, cadence; reconnaître acquisition valide/invalide; expliquer aliasing, Nyquist, choix de fenêtre, FFT/PSD/spectrogramme; calculer RMS, crest factor, fréquence dominante et puissance de bande.

## Protocole proposé
- `stationary` : carte immobile sur une table 15–20 s (sans perturber le câble).
- `periodic` : petits mouvements contrôlés et réguliers de gauche à droite en maintenant l'orientation du capteur; 15–20 s.
- `impact` : accélérations brèves mais **douces et sans choc matériel**, par exemple déplacer la carte par petites impulsions répétées, sans la heurter; 15–20 s.
- Réaliser plusieurs essais et sessions indépendantes pour chaque condition, avec consignes imagées. Repositionnement contrôlé entre sessions, protocole nominal consigné.
- Fréquence cible proposée 50 Hz **sous réserve de mesure et faisabilité**; pas de découpage par un nombre arbitraire de lignes série. La durée doit fournir plusieurs fenêtres de 256 échantillons; ajuster de façon explicite si nécessaire.

## Parcours étudiant (chaque point aura ses vrais screenshots, résultats et questions)
1. Vérifier Arduino, firmware, IMU, port série, capacité à produire données monotones. Lire g et deg/s; énoncer pourquoi TP01 utilise les trois axes accélération.
2. Expliquer comment les échantillons sont cadencés **sur la carte**; ajouter `seq`, `t_us` à chaque trame. Utiliser une structure de début/fin d'enregistrement, `recording_id`; documenter protocole et reprise.
3. Lancer un outil d'acquisition Python CLI convivial, éventuellement petite interface facultative, avec détection des ports, choix carte/classe/session et compte à rebours.
4. Chaque session : montrer consigne visuelle puis capturer. Permettre accepter/refuser l'essai après contrôle qualité; `manifest.csv` retrace provenance, cadence mesurée et rejets. Capturer captures de l'interface et exemple de CSV.
5. Explorer données dans Jupyter : fichiers, dimensions, pertes, outliers, dérive et distribution entre conditions. Graphes temporels ax/ay/az et effet de gravité; comparer sessions.
6. Expliquer fs, Nyquist et filtre anti-alias physique : un filtrage logiciel après acquisition ne répare **pas** une fréquence trop faible. Mesurer le jitter USB mais ne pas confondre temps de réception et temps d'échantillonnage.
7. Sur un axe `ax_g`, retrait DC et filtre causal **uniquement pour inspection**, comparer signal brut et filtré, préciser délai du filtre.
8. FFT amplitude, Welch PSD et spectrogramme STFT; distinguer spectre vs densité spectrale vs évolution temporelle. Vérifier l'hypothèse de cadence régulière ou décrire stratégie documentée.
9. Fenêtrer à N=256, hop=128, ne jamais franchir une coupure/transition; extraire les quatre features du contrat; vérifier un exemple numérique de chaque feature.
10. Exporter `features.csv` + manifest + `quality_report.md` + figures. Fournir la commande de test et les questions de bilan.

## Livrables attendus
`firmware/imu_capture/imu_capture.ino` (ou variantes matérielles); `capture.py`; `analysis/01-eda.ipynb`; `analysis/02-signal-features.ipynb`; `src/` traitement testé; simulateur clairement distinct; données exemple de référence; tests pytest; captures réelles; `results/` ignoré par Git; guide de dépannage pour Windows/macOS/Linux.

## Cas d'échec à provoquer
Port série absent/occupé; firmware erroné; Rev2 avec mauvaise librairie; échantillons dupliqués; timestamps hors ordre; dérive/fenêtre incomplète; aucun essai valide. Pas de sortie « réussite » silencieuse.

## Critères d'acceptation
Un étudiant peut obtenir une acquisition valide, reproduire les figures, identifier une acquisition invalide, expliquer les caractéristiques et produire un dataset compatible TP02. Le simulateur permet CI sans carte mais ne prouve rien pour le hardware. Les durées et seuils proposés doivent être revus à la lumière des acquisitions réelles.

## Réutiliser et vérifier
https://github.com/wld-code/AIoT-Book/tree/main/labs/ch07-08-acceleration-features
https://github.com/wld-code/TinyML-for-motor
