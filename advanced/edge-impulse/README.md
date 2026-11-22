# Pour aller plus loin A — Reconnaissance audio avec Edge Impulse

**Statut : protocole optionnel à confirmer sur les cartes.** Durée cible : 2–3 h. Matériel : la même Nano 33 BLE **Sense**, microphone PDM intégré, USB, ordinateur et connexion Internet pour Edge Impulse. Ne pas exiger de capteur audio externe ni d'ESP32.

## Mission
Comparer un workflow de traitement construit en TP01–03 avec une plateforme ML intégrée : apprendre à reconnaître des mots **« start » / « stop »** et une condition `noise/unknown` définie par les données. Les résultats et les latences doivent être évalués, pas uniquement la démonstration.

## Parcours
1. Vérifier version Arduino Sense et le fonctionnement du microphone avec un sketch minimal PDM adapté; ne pas supposer que la carte sans Sense dispose du capteur.
2. Créer un compte Edge Impulse en tenant compte du plan disponible, des contraintes de confidentialité et des restrictions éventuelles. Documenter la version actuelle du Studio.
3. Collecter clips avec consentement, plusieurs répétitions, bruit ambiant et un vrai groupe de test indépendant. Ne pas pousser de données personnelles/voix identifiables dans Git; proposer une alternative pédagogique sans voix réelle ou un dataset public correctement licencié.
4. Expliquer sample rate, durée des clips, format audio, échantillons de bruit et classe inconnue explicite.
5. Créer l'Impulse : traitement spectral/MFCC/MFE selon compatibilité choisie, classifieur, fenêtre, stride, paramètres et coût estimé.
6. Séparer entraînement et test par session/personne si possible; évaluer matrice de confusion et false positives. Faire un test voix jamais utilisée.
7. Déployer par bibliothèque Arduino ou artefact compatible avec la Nano, compiler et téléverser; l'export doit être testé sur **originale** et **Rev2** séparément avant de déclarer le support.
8. Afficher classification live + score et rejets; tester bruit, distance et changements de voix.
9. Documenter limites du service cloud et une piste de repli sans prétendre à une équivalence de fonctionnement.

## Livrables
Guide illustré Edge Impulse, firmware PDM, protocole capture, paramètres du projet, métriques, screenshots réels et journal de compilation. **Pas de capture d'écran inventée** ni de publication de voix collectées sans autorisation.

## Sources
https://docs.arduino.cc/tutorials/nano-33-ble-sense/edge-impulse
https://docs.edgeimpulse.com/
https://docs.arduino.cc/hardware/nano-33-ble-sense/
https://docs.arduino.cc/hardware/nano-33-ble-sense-rev2/
