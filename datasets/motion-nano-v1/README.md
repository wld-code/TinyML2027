# Dataset de référence `motion-nano-v1`

Ce sont de **vraies mesures** de l'accéléromètre d'une Nano 33 BLE Sense **originale** (LSM9DS1), enregistrées le 23/11/2026 avec le firmware `labs/01-sensor-data/firmware/imu_capture` 0.1.0 et l'outil `tinyml2027.capture`, sur macOS 15.6.

Il permet de faire le TP02 et le TP03 **sans carte**, ou de comparer vos propres données à celles de la carte de référence.

```sh
uv run python -m tinyml2027.build_features --data datasets/motion-nano-v1 --out results/tp01-reference
uv run python -m tinyml2027.train_motion --features results/tp01-reference/features.csv --test-session s05
```

## Contenu

- 5 sessions (`s01` à `s05`) × 3 gestes (`stationary`, `periodic`, `impact`) × 20 s ≈ 2 315 mesures par fichier, à 116,2 Hz mesurés.
- Les 15 enregistrements ont passé le contrôle qualité : aucune lacune, aucune rupture de séquence, aucune saturation.
- `manifest.csv` : un enregistrement par ligne (format de `docs/DATA_CONTRACT.md`).
- `raw/<session>/<id>.csv` : `seq,t_us,ax_g,ay_g,az_g`.
- `raw/<session>/<id>.json` : les métadonnées et le contrôle qualité complet. Le champ `board_id` est une empreinte tronquée du numéro de série de la carte, qui n'identifie aucune personne.

## Protocole réellement suivi

Une seule personne, une seule carte, une seule table. Entre deux sessions, la carte a été déplacée et tournée d'un quart de tour. Pour `periodic` et `impact`, le geste était commencé environ 4 s avant le début de l'enregistrement.

| Session | Consigne particulière | Observation |
|---|---|---|
| s01–s02 | consigne standard | — |
| s03 | consigne standard | tapotements environ 10 fois plus énergiques que dans les autres sessions |
| s04 | glissement « lent », tapotements « forts » | glissement resté à environ 0,9 Hz ; tapotements moins forts qu'en s03 |
| s05 | glissement « rapide », tapotements « moyens » | **session de test** du TP02 (glissement à environ 1,4 Hz) |

## Limites

Les conditions sont uniques : une personne, une table, une carte originale. Ce jeu ne dit rien de la généralisation à d'autres personnes, d'autres surfaces ou une Rev2.

Dans les fichiers JSON, le champ `firmware` vaut `imu_capture` : le numéro de version, séparé par une espace dans la réponse de la carte, a été coupé. La version réelle est 0.1.0.

## Licence

CC BY 4.0, comme les contenus pédagogiques du dépôt (voir `LICENSE-docs.md`).
