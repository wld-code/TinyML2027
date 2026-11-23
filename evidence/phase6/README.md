# Phase 6 — IMU LSM9DS1 sur la Nano 33 BLE Sense V1 : validé sur matériel

**Date :** 23/11/2026. **Poste :** macOS 15.6 (Apple Silicon). **Carte :** Nano 33 BLE Sense V1. **Firmware :** `examples/04_imu` 0.1.0, avec la bibliothèque `libraries/TinyML2027Imu` et Arduino_LSM9DS1 1.1.1.

## Compilation

| Cible | Flash | RAM statique | Statut |
|---|---|---|---|
| Originale (LSM9DS1) | 95 440 octets (9 %) | 45 992 octets (17 %) | compilé, téléversé, exécuté, **validé sur matériel** |
| Rev2 (BMI270), `REV=rev2` | 116 408 octets (11 %) | 46 656 octets (17 %) | **compilé seulement** : aucune carte Rev2 disponible |

## Cadence mesurée (carte immobile)

Le firmware compte les nouveaux échantillons sur des fenêtres de 1 s. Il mesure **115,8 à 116,9 Hz** pour l'accéléromètre comme pour le gyroscope, pour une cadence nominale annoncée de 119 Hz. C'est cohérent avec les 116,19 Hz mesurés sur 8 s par `imu_capture`, et avec E3 (lot 0).

## Contrôle des axes : position par position, conduit dans la conversation

L'enseignant mettait la carte en place, puis répondait « ok ». La mesure de 3 s était lancée seulement à ce moment-là, avec `tinyml2027.imu_check.snap`. Les mesures brutes sont dans `imu_steps-macos15.6-v1.jsonl`.

| Étape | Position | a moyen (g) | \|a\| (g) | Gravité |
|---|---|---|---|---|
| 1 | à plat, puces vers le haut | (−0,002 ; −0,010 ; +0,963) | 0,963 | +Z |
| 2 | à plat, retournée | (+0,003 ; −0,023 ; −1,036) | 1,037 | −Z |
| 3 | debout, câble USB en bas | (+0,983 ; −0,044 ; +0,025) | 0,985 | +X |
| 4 | debout, câble USB en haut | (−0,984 ; −0,032 ; +0,147) | 0,995 | −X |
| 5 | debout, câble USB à gauche, puces face à soi | (+0,020 ; −0,904 ; +0,358) | 0,973 | −Y |
| 6 | debout, câble USB à droite, puces face à soi | (−0,060 ; +0,943 ; +0,289) | 0,988 | +Y |
| 7 | rotation libre, 6 s | pics du gyroscope 35 / 54 / 89 °/s | — | 3 axes > 30 °/s |

**Résultat :** les 6 directions ±X, ±Y et ±Z apparaissent, chacune une seule fois. La norme reste comprise entre 0,96 et 1,04 g, et les trois axes du gyroscope réagissent.

**Repère des axes de la carte V1, tel que mesuré :**
- X suit la longueur de la carte : +X pointe à l'opposé du connecteur USB ;
- Y suit la largeur ;
- Z est perpendiculaire à la carte : +Z pointe du côté des composants.

**Écarts à connaître :**
- Carte à plat et immobile, |a| vaut 0,96 g en +Z mais 1,04 g en −Z. Cette asymétrie de ±4 % révèle un **décalage (offset) d'environ −0,04 g sur l'axe Z**, qui n'est pas corrigé. Les features du contrat retirent la moyenne de chaque fenêtre, si bien que ce décalage ne les affecte pas.
- Le gyroscope affiche un biais au repos d'environ 3,5 °/s sur X.

## Essai 1 : échec conservé

Le fichier `imu_check-essai1-echec-macos15.6-v1.txt` contient le premier essai, mené avec l'outil interactif `python -m tinyml2027.imu_check`. Il a échoué parce que la mesure démarrait juste après l'appui sur Entrée, alors que la carte était encore en mouvement, et parce que les consignes de position étaient ambiguës (« grand côté »). Les consignes ont été réécrites en termes de direction du câble USB, et des schémas ont été ajoutés.
