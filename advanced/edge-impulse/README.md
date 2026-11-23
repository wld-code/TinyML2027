# Pour aller plus loin A — Reconnaître des mots avec Edge Impulse

**Durée :** 2 à 3 h. **Matériel :** la même Nano 33 BLE **Sense**, avec son microphone intégré, plus une connexion Internet et un compte Edge Impulse. Facultatif : les TP01 à TP03 fonctionnent sans ce service.

**Statut au 23/11/2026 :**

| Partie | Statut |
|---|---|
| Microphone de la carte (`mic_check`) | **exécuté** sur la Nano V1 : environ 16 000 échantillons/s reçus, niveau ambiant mesuré ([evidence](../../evidence/edge-impulse/)) |
| Compte, collecte, entraînement et export Edge Impulse | **non testé** : demande le compte de l'enseignant et une session en ligne |
| Bibliothèque Arduino exportée, sur l'originale et la Rev2 | **non testé** |

Les étapes 2 à 6 décrivent la démarche. Elles seront complétées avec les vraies captures d'écran et versions lors d'une séance avec l'enseignant : `TODO: CAPTURE RÉELLE`.

## Ce que vous allez faire

Comparer le travail « à la main » des TP01 à TP03 (features, entraînement, conversion, firmware) avec une plateforme qui automatise ces étapes. Le but est de reconnaître **« start »**, **« stop »** et une classe **« bruit / inconnu »**, puis de **mesurer** la qualité obtenue, au-delà de la simple démonstration.

---

## Étape 1 — Vérifier le microphone (sans Internet)

```sh
./scripts/compile.sh advanced/edge-impulse/sketches/mic_check
./scripts/upload.sh  advanced/edge-impulse/sketches/mic_check
./scripts/arduino.sh monitor -p PORT -c baudrate=115200
```

Le sketch utilise la bibliothèque **PDM**, fournie avec le core officiel `arduino:mbed_nano`. Rien n'est à installer.

**Sortie réelle (pièce calme, carte de référence) :**
```text
t_ms,rms,crete,echantillons_par_s
4016,310.5,370,16384
4516,217.4,282,15360
5266,27.7,66,16384
6266,6.7,13,16384
7266,17.7,50,16384
```

- `echantillons_par_s` alterne entre 15 360 et 16 384, car le micro livre ses données par blocs de 512 octets (256 échantillons). La moyenne est bien d'environ 16 000.
- Les premières lignes sont plus fortes : c'est la mise en route du micro, qui se stabilise en environ 1 s.
- Dans le calme, le niveau RMS reste autour de 10 (unités brutes, sur une échelle de 0 à 32 767).

**À faire vous-même :** claquez des mains près de la carte. La crête doit monter nettement. Une carte **sans Sense** n'a pas de micro : le sketch affiche alors `ERREUR PDM.begin`.

---

## Étape 2 — Compte Edge Impulse

Créez un compte sur <https://studio.edgeimpulse.com>. **Avant de commencer, vérifiez** les points suivants et notez-les :
- l'offre gratuite disponible et ses limites ;
- où les données sont stockées ;
- la version du Studio (en bas de page).

Il s'agit d'un service en ligne : ne déposez pas de voix sans le **consentement** de la personne enregistrée.

## Étape 3 — Collecter les données

- **Classes :** `start`, `stop` et `bruit` (bruit de la pièce, autres mots, silence).
- **Format :** clips de 1 s, 16 kHz, mono.
- **Quantité :** plusieurs dizaines de clips par classe, avec **plusieurs personnes** si possible.
- **Test indépendant :** gardez les clips d'**une personne** uniquement pour le test, de la même façon qu'au TP02 avec une session de test.
- **Alternative sans voix réelle :** le jeu public *Speech Commands* (Google, licence CC BY 4.0), qui contient les mots « stop » et « go ». Vérifiez sa licence au moment de l'utiliser.

**Ne mettez jamais les enregistrements de voix dans Git.**

## Étape 4 — Créer l'« Impulse »

Dans le Studio : fenêtre de 1 s, bloc de traitement audio (MFE ou MFCC) et bloc de classification. Notez chaque paramètre, ainsi que l'estimation de RAM, de Flash et de latence affichée par le Studio. Vous la comparerez ensuite aux **mesures réelles** sur la carte.

## Étape 5 — Évaluer

Matrice de confusion sur le test, **faux positifs** (un « start » reconnu alors que personne ne l'a dit), puis un essai avec une voix jamais utilisée.

## Étape 6 — Déployer sur la Nano

Exportez une **bibliothèque Arduino**, compilez avec `scripts/compile.sh` et téléversez. Mesurez la Flash, la RAM et la latence réelles, puis comparez-les aux estimations du Studio. **Testez séparément sur une carte originale et sur une Rev2** avant d'affirmer que les deux fonctionnent.

## Limites

- Le service peut changer ses offres, son interface ou ses formats d'export : chaque version doit être notée.
- Sans Internet ni compte, cette extension n'est pas réalisable. La solution de repli, sans service en ligne, consiste à appliquer la démarche des TP01 à TP03 à l'audio. Elle ne donne pas le même résultat et demande plus de travail.

## Sources

<https://docs.edgeimpulse.com/> · <https://docs.arduino.cc/tutorials/nano-33-ble-sense/edge-impulse> · <https://docs.arduino.cc/hardware/nano-33-ble-sense/>
