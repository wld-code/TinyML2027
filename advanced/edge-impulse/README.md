# Extension — Reconnaître des mots avec Edge Impulse

**Objectif.** Entraîner un classifieur audio et comparer ses résultats sur des clips de test et sur le microphone de la Nano.

**Durée.** 2 à 3 h. **Matériel.** Une Nano 33 BLE Sense avec son microphone intégré et un câble USB de données. **Prérequis.** Un poste préparé selon le [guide d’installation](../../docs/INSTALLATION.md), une connexion Internet et un compte Edge Impulse. Lancez les commandes depuis la racine du dépôt.

Nous utiliserons trois classes, `go`, `stop` et `bruit`. Le Studio prépare les entrées du modèle, l’entraîne et exporte une bibliothèque Arduino. Nous reprenons ainsi sur des signaux audio les étapes des TP01 à TP03.

## 1. Vérifier le microphone (sans Internet)

```sh
./scripts/compile.sh advanced/edge-impulse/sketches/mic_check
./scripts/upload.sh  advanced/edge-impulse/sketches/mic_check
./scripts/arduino.sh monitor -p PORT -c baudrate=115200
```

`-p PORT` sélectionne automatiquement le port si une seule Nano est détectée. Le sketch utilise la bibliothèque PDM du support Arduino Mbed Nano. Attendez que le microphone se stabilise, puis observez le niveau RMS et la crête au calme et pendant quelques claquements de mains. Vérifiez que les crêtes augmentent et que la cadence moyenne est proche de 16 000 échantillons par seconde. Les valeurs fluctuent d’une ligne à l’autre car le microphone livre les données par blocs. Une erreur `PDM.begin` signale un échec d’initialisation. Vérifiez que vous utilisez bien une carte **Sense**.

## 2. Compte et projet Edge Impulse

Fermez le moniteur série après le contrôle du microphone. Créez un projet **Personal** et **Private** dans [Edge Impulse Studio](https://studio.edgeimpulse.com). Vérifiez la visibilité dans **Sharing**. Utilisez les clips publics du jeu fourni et gardez vos enregistrements personnels hors du service et de Git. Notez la date de la séance et vérifiez les conditions d’utilisation de votre offre avant d’importer les données.

Dans le Studio, choisissez la cible **Arduino Nano 33 BLE Sense (Cortex-M4F 64MHz)** (en haut à droite) : les estimations de RAM, de Flash et de latence en dépendent.

## 3. Préparer et importer les données

Utilisez le jeu public **Speech Commands v0.02** (Google, Pete Warden, CC BY 4.0). La classe `bruit` regroupe des bruits de fond découpés en clips d’une seconde et les mots yes, no, up, down, left et right.

1. Téléchargez `speech_commands_v0.02.tar.gz` (2,3 Go) depuis le [serveur TensorFlow](https://storage.googleapis.com/download.tensorflow.org/data/speech_commands_v0.02.tar.gz) et décompressez-le **hors du dépôt Git**.
2. Construisez le sous-ensemble :
   ```sh
   uv run python advanced/edge-impulse/prepare_speech_commands.py --src CHEMIN/speech_commands --out CHEMIN/ei_kws
   ```
   Choisissez un dossier de sortie vide. Le script produit des WAV mono de 1 s à 16 kHz, avec 200 clips d’entraînement et 50 de test par classe. Il vérifie que les locuteurs sont distincts entre les deux ensembles.
3. Dans **Data acquisition → Add existing data → Upload data**, importez les fichiers de `test/` avec **Test** et **Infer from filename**, puis ceux de `train/` avec **Training**. Gardez cette séparation pour évaluer des voix absentes de l’entraînement.

Vérifiez que le Studio affiche 600 clips d’entraînement et 150 de test, répartis entre les trois classes. Gardez le dossier de sortie hors du dépôt Git.

## 4. Créer l'« Impulse »

Dans **Create impulse**, choisissez une fenêtre de **1000 ms** à **16 000 Hz**, le bloc **Audio (MFCC)** et le bloc **Classification**, puis cliquez sur **Save Impulse**. Les MFCC sont des coefficients qui résument la forme du spectre audio sur une échelle liée à la perception des fréquences.

Dans **MFCC**, gardez 13 coefficients, des trames de 20 ms, 32 filtres et une FFT de 256 points. Cliquez sur **Save parameters**, puis **Generate features**. Dans **Classifier**, gardez deux couches de convolution 1D à 8 et 16 filtres, 100 époques et un taux d’apprentissage de 0,0001. Cliquez sur **Save & train**.

Vérifiez que l’entraînement se termine. Le Studio calcule son score de validation sur une partie des données d’entraînement. Un même locuteur peut apparaître dans les deux parties. Utilisez l’étape suivante pour évaluer les clips de locuteurs réservés au test.

## 5. Évaluer sur le test

**Model testing → Classify all.** Pour évaluer aussi le modèle int8 (celui qui sera déployé), cochez **Test 'Quantized (int8)' model** dans la roue dentée, puis relancez.

![Résultat du test, modèle int8](../../docs/screenshots/edgeimpulse-etape05-test-int8-studio.png)

*Modèle int8, 150 clips de locuteurs jamais vus. Le float32 donne exactement la même matrice.*

Le modèle INT8 de référence a classé correctement 80,67 % des clips du test. Dans la matrice de confusion, repérez les faux positifs, c’est-à-dire les clips de bruit pris pour une commande. Dans l’essai de référence, 10 % des clips de bruit sont classés `go` et 2 % `stop`. La colonne « incertain » correspond aux clips dont aucun score ne dépasse 0,6.

## 6. Déployer sur la Nano et mesurer

**Deployment** : cible **Arduino library**, moteur **EON Compiler**, modèle **Quantized (int8)**, puis **Build**. Le Studio télécharge un ZIP.

Décompressez le ZIP **dans un dossier temporaire**, sans l'installer dans vos bibliothèques Arduino, puis compilez l'exemple micro avec l'environnement du cours :

```sh
./scripts/compile.sh CHEMIN/TinyML2027-mots_inferencing/examples/nano_ble33_sense/nano_ble33_sense_microphone \
    --library CHEMIN/TinyML2027-mots_inferencing
./scripts/upload.sh  CHEMIN/.../nano_ble33_sense_microphone
```

Dans les deux commandes, remplacez `CHEMIN` par le dossier d’extraction et adaptez le nom de la bibliothèque à celui de l’archive. Pour le téléversement, remplacez `CHEMIN/...` par le chemin complet vers le même dossier de sketch qu’à la compilation. Ouvrez ensuite le moniteur série avec la commande de l’étape 1 et observez les scores au silence, puis en prononçant `go` et `stop`.

L’exemple écoute pendant une seconde, puis fait une pause. Certaines fenêtres tombent entre deux mots. Dans l’essai de référence sur la carte originale, `stop` arrive en tête dans 1 fenêtre sur 12 pendant l’essai vocal, alors que 88 % des clips `stop` du Studio sont correctement classés. Pour comparer les performances sur carte, il faudrait disposer de fenêtres étiquetées et synchronisées avec les mots prononcés. Relevez aussi les temps de traitement et de classification. Les chiffres de mémoire de la compilation incluent le programme complet. Retrouvez les [mesures et journaux de la Nano originale](../../evidence/edge-impulse/). L’export reste à tester sur Rev2.

Après l’essai, restaurez le programme d’inférence du cours. Si vous disposez de la release `motion-v1`, utilisez la commande suivante. Sinon, recompilez et téléversez le firmware selon le [TP03](../../labs/03-embedded-inference/README.md).

```sh
uv run python -m tinyml2027.release flash releases/motion-v1
```

## Questions

1. Pourquoi séparer les locuteurs entre entraînement et test ?
2. Comment constituer un test étiqueté avec le microphone de la Nano ? Comment compter les déclenchements au silence et les mots manqués ?

Les noms des menus peuvent évoluer. Consultez la [documentation Edge Impulse](https://docs.edgeimpulse.com/) et le [guide Arduino](https://docs.arduino.cc/tutorials/nano-33-ble-sense/edge-impulse).

## Corrigé

<details>
<summary>Afficher les réponses</summary>

1. La voix d’une personne se retrouve dans plusieurs clips. Si elle figure dans l’entraînement et le test, le modèle peut exploiter des caractéristiques propres à cette voix. La séparation par locuteur permet d’évaluer la reconnaissance sur de nouvelles voix.
2. Enregistrez localement des clips associés à des étiquettes définies à l’avance, avec les mêmes conditions de capture que sur la Nano. Repérez les fenêtres contenant un mot entier et celles contenant seulement du bruit ou du silence. Comptez les prédictions `go` ou `stop` sur les fenêtres sans mot pour mesurer les faux déclenchements. Pour chaque mot, comptez les fenêtres étiquetées avec ce mot où il n’a pas été reconnu, y compris les réponses « incertain ». Rapportez chaque compte au nombre de fenêtres concernées.

</details>
