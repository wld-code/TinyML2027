# Lot 3 — Vérification du client Edge Impulse

Sur le Mac, le client a interrogé en HTTPS le projet privé 1173087 avec une clé existante transmise par variable d’environnement. Les écritures cloud restent couvertes par tests simulés pendant ce lot. Les expériences de référence ont été produites dans Studio au lot 2.

- `check` a confirmé le nom, l’identifiant et la visibilité privée.
- `results 1` et `results 2` ont récupéré 300 résultats INT8 chacun via des requêtes paginées. Les deux CSV recalculés avec `score_studio.py` sont identiques aux CSV du lot 2.
- `download 2` a téléchargé le ZIP Arduino EON INT8. `cmp` a confirmé son identité binaire avec le ZIP du lot 2.
- Le [dry-run d’import](api-dry-run.txt) a validé les empreintes des 300 WAV correctifs et affiché la destination Training sans connexion.
- Le [rapport réel](gates-v2.json) conclut au rejet. Le [rapport avec injection](gates-injection.json) force le taux de faux déclenchements dégradés à 100 % pour éprouver le pipeline. Cette valeur est une simulation. La création d’un manifeste candidat à partir de ce rapport est refusée.
- Le manifeste local du candidat réel a été produit avec la version du déploiement Studio 2 et les empreintes du ZIP, du manifeste de données, des métriques et de la décision. Son statut est `rejected`. Aucun binaire ni essai sur carte n’est associé à ce lot.

Le test final reste réservé.
