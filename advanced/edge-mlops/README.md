# Pour aller plus loin B — Edge MLOps sur **une seule Nano**

**Statut : spécification optionnelle.** Durée cible : 2–3 h. Matériel : **la même** Nano 33 BLE Sense avec connexion USB; pas d'ESP32, pas de cloud ni OTA obligatoire.

## Mission
Démontrer que déployer un modèle ne suffit pas : il faut pouvoir identifier la version réellement utilisée, valider un candidat, tracer son origine et restaurer une version précédente quand un déploiement échoue.

## Déroulé
1. Exporter une release immuable `motion-v1` avec firmware compilé, SHA-256, modèle INT8, scaler, labels, feature contract, build toolchain et preuves d'évaluation.
2. Entraîner un candidat `motion-v2` avec nouvelle session ou changement contrôlé; conserver le jeu test intact et comparer sur un nouveau jeu d'évaluation si l'on ajuste après comparaison.
3. Générer `release_manifest.json` qui précise model_version, firmware_version, model_hash, board_revision, board_core, runtime, feature_schema, labels, tested_OS, acceptance_status.
4. Vérifier manifeste, taille, compatibilité carte/runtime, présence golden vectors et build. Rejeter volontairement manifest corrompu ou modèle dont le schéma diffère **avant** flash.
5. Mettre à jour la Nano par un upload USB **supervisé**; ce n'est pas une OTA. Le firmware annonce au démarrage la version et le hash du modèle en cours.
6. Rejouer vecteurs témoins et vérifier les scores/labels; distinguer état **souhaité** et état **confirmé par la carte**.
7. Déclencher volontairement un échec d'acceptation sans endommager la carte, puis **reflasher** v1 par USB; observer la restauration.
8. Écrire un rapport de release et de rollback. Si possible ajouter un mini-script `release.py` idempotent qui valide et affiche les étapes avant toute action irréversible.
9. Extension théorique : comment faire une OTA sécurisée, signatures, authentification, double banque, watchdog et atomicité, mais **ne pas prétendre l'implémenter**.

## Livrables
`releases/motion-v1`, `releases/motion-v2` (artefacts de démonstration), `scripts/validate_release.py`, `scripts/flash_release.py` avec avertissements, logs de validation, tests manifestes invalides et preuve USB/retour v1.

## Critère d'acceptation
Le système refuse un mauvais contrat, atteste le firmware réellement démarré et restaure v1 avec preuve de l'état observé sur la Nano. La réussite d'une commande upload n'est pas une preuve du modèle exécuté.

## Source
https://github.com/wld-code/AIoT-Book/tree/main/labs/ch13-edge-model-update
