# Lot 4 — Inférence et monitoring sur Nano V1

Essais sur le Mac et sur l’Arduino Nano 33 BLE Sense originale le 25 novembre 2026. Le téléversement par USB identifie le nRF52840. Le firmware reconnaît le LSM9DS1 interne et annonce `ABX00031`. `monitor.py check` confirme `kws-v1`, son empreinte d’export et les états `mic_ok=true` et `model_ok=true`. La carte est équipée de `kws_nano 0.1.1`, protocole 2.

| Vérification | Résultat | Preuve |
|---|---|---|
| Compilation | 171 784 octets de Flash, 81 672 octets de RAM statique, tampon audio de 32 000 octets compris | [Sortie Arduino CLI](kws-v1-compile.log) |
| Téléversement et démarrage | Nano V1, microphone et première inférence opérationnels | [Téléversement](kws-v1-upload.log) et [identité USB](kws-v1-identity.json) |
| Rejeu numérique | 12 CRC32 vérifiés, 12 décisions identiques à Studio, écart maximal de score d’environ 0,000005 | [Trames JSONL](kws-v1-replay.jsonl) · [Résumé](kws-v1-replay-summary.json) |
| Microphone en ambiance | 10 fenêtres acquises, aucune erreur PDM, inférence p95 142,74 ms, acquisition + inférence p95 1 149,68 ms | [Trames JSONL](kws-v1-ambient.jsonl) · [Résumé](kws-v1-ambient-summary.json) |
| Haut-parleurs du Mac | 6 clips publics joués à un gain `afplay` de 0,25, 6 réponses incertaines et 4 commandes manquées parmi les 4 commandes jouées | [Trames JSONL](kws-v1-speaker-exploratory.jsonl) · [Résumé](kws-v1-speaker-exploratory-summary.json) |

Le scénario aux haut-parleurs est exploratoire. La distance, l’orientation et le niveau du système n’ont pas été mesurés. L’étiquette correspond au clip joué. La [photo du montage](../../advanced/edge-impulse-mlops/figures/montage-nano-v1.jpg) montre la Nano branchée et posée près du Mac. La distance exacte n’a pas été mesurée.

Le DSP a pris 136 ms et la classification 6 ms sur chaque fenêtre de l’essai. Les 10 fenêtres ambiantes ont écarté chacune 2 048 échantillons pendant l’inférence. La solution couvre l’acquisition par fenêtres déclenchées, avec un temps mort entre elles. L’acquisition et le calcul ont donc pris environ 1,15 s au p95, hors transmission et délai du poste.

## Diagnostic du rejeu USB

Le [premier envoi en bloc de 32 000 octets](kws-v1-replay-initial-timeout.jsonl) et le [second en blocs de 128 octets écrits d’un seul coup](kws-v1-replay-block-timeout.jsonl) ont produit des délais d’attente sur la carte. Le protocole retenu confirme chaque bloc de 128 octets. Le client émet ce bloc par écritures de 32 octets avec vidage et pause de 3 ms. La série de 12 fenêtres a ensuite réussi avec les mêmes fichiers. Le CRC32 atteste la concordance des octets reçus avec le WAV sélectionné. La comparaison des scores porte sur le calcul numérique sur ces octets.

Le binaire correspondant à la dernière mesure est conservé localement dans `artifacts/edge-impulse-mlops/kws-v1/firmware/kws_nano.ino.bin`. SHA-256 `828a0c02d19aff90e89787254ff05f61534ca1060addd238d92b3d0a0a772747`. v2 reste archivée comme candidat refusé. Le retour arrière sur le binaire de référence est prévu au lot 5.

## Reprise avec le montage photographié

Les six mêmes clips ont été relus avec un gain `afplay` de 0,5, sur les haut-parleurs intégrés. CoreAudio a indiqué 50 % et sortie active avant la série, puis 0 % et sortie muette après. Le moment du changement est inconnu. Les six fenêtres ont été acquises, avec cinq réponses incertaines et une classe `bruit`. Ces trames servent au diagnostic du montage. Les conditions de lecture ne permettent pas de mesurer la reconnaissance à volume fixe. [Trames de la reprise](kws-v1-speaker-adjacent.jsonl) · [Résumé](kws-v1-speaker-adjacent-summary.json)

## Contrôle du volume clip par clip

Une nouvelle série a été lancée avec la Nano dans la position photographiée. Le niveau CoreAudio valait 0,5594 au départ et le gain de lecture `afplay` était fixé à 0,5. Les deux premiers clips `bruit` ont donné `uncertain`, avec un niveau système identique avant et après chaque lecture. Après le troisième clip, le niveau système était passé à 0,9320. La série a été interrompue. Les deux premiers clips seuls satisfont le contrôle de niveau avant et après lecture. Le troisième et les trois clips restants ne sont pas retenus pour cette mesure. [Trames et mesures de niveau](kws-v1-speaker-fixed.jsonl)

## Essai à volume système vérifié

Les six mêmes clips propres ont été rejoués avec la Nano dans la position photographiée, à côté du Mac, avec le microphone vers le haut. La distance exacte n’a pas été mesurée. Le volume des haut-parleurs intégrés a été réglé à 50 % dans CoreAudio et vérifié avant et après chaque clip, avec un gain `afplay` de 0,5. Le volume initial mesuré (0,9320 sur l’échelle CoreAudio) a été rétabli après l’essai.

Les six captures se sont terminées sans erreur PDM. La Nano a reconnu un `stop` et répondu `uncertain` pour les cinq autres fenêtres. Trois commandes sur quatre ont été manquées. Aucun des deux clips `bruit` n’a déclenché de commande. Le p95 de l’inférence est de 142,65 ms. Cette série documente un essai acoustique court et ne sert pas à mesurer une accuracy générale. [Trames et contrôles du niveau](kws-v1-speaker-50pct.jsonl) · [Résumé](kws-v1-speaker-50pct-summary.json)
