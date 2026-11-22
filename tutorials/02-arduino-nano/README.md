# Tutoriel 02 — Préparer l'Arduino Nano 33 BLE Sense

**Statut : spécification, firmware et hardware non vérifiés dans TinyML2027.** Durée : 30–45 minutes. Une Nano **Sense** originale ou Rev2 et un câble USB de données; pas de circuit externe.

## Déroulé à rédiger et à tester
1. Identifier visuellement la carte, la référence et la révision; comparer Sense/Rev2 et exclure les cartes sans Sense dans les parcours microphone. Vérifier révision par l'inscription/identifiant produit, jamais seulement par la présence d'un port.
2. Installer Arduino IDE 2 et, éventuellement, Arduino CLI, sur Windows/macOS/Linux; noter versions.
3. Installer et vérifier le package Arduino Mbed OS Nano Boards et la cible exacte. Ajouter dépannage bootloader/USB et gestion des drivers.
4. Branchez la carte avec un câble USB **data**; sélectionner port détecté. Ne jamais fixer COM3 ou /dev/ttyACM0 dans un script.
5. Compiler et téléverser Blink, décrire LED intégrée et résultat attendu, documenter bootloader si upload échoue.
6. Installer `Arduino_LSM9DS1` pour originale **ou** `Arduino_BMI270_BMM150` pour Rev2. Fournir deux sketches minimalistes, sélectionner le bon `#include`; tester l'accéléromètre et, si utile, le gyroscope.
7. Afficher six valeurs avec unités g et deg/s, version firmware et cadence. Vérifier que la carte répond aux mouvements; mesurer la fréquence effective.
8. Vérifier le port série depuis Python avec `python -m serial.tools.list_ports -v` et expliquer port occupé, timeout, permissions Linux, double appui reset.
9. Sur original et Rev2 : test matériel à réaliser individuellement. Ne jamais marquer les deux validées sans logs.
10. Introduire l'orientation et la gravité : l'accéléromètre mesure aussi la gravité, la direction des axes varie si l'on retourne la carte.

## Documentation OS et captures
Captures du téléchargement Arduino, Boards Manager, sélection board/port, upload Blink, moniteur série avec les 6 axes et erreur/résolution. Les écrans doivent être réels, datés, anonymisés et associés aux versions.
Windows PowerShell, macOS Terminal, Ubuntu Terminal : commandes séparées dès qu'elles divergent. Permissions série Linux traitées par diagnostic, pas par une commande `chmod 777`.

## Références
https://docs.arduino.cc/hardware/nano-33-ble-sense/
https://docs.arduino.cc/hardware/nano-33-ble-sense-rev2/
https://docs.arduino.cc/tutorials/nano-33-ble-sense/cheat-sheet
https://docs.arduino.cc/tutorials/nano-33-ble-sense-rev2/cheat-sheet
https://github.com/wld-code/AIoT-Book/blob/main/labs/tutorials/arduino-nano33ble-startup.md
