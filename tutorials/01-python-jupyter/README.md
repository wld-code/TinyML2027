# Tutoriel 01 — Python, Jupyter et premiers signaux

**Statut : spécification à développer par Claude Code.** Durée cible : 2 h. Matériel : ordinateur seulement. Objectif : rendre autonome un débutant face à un notebook d'analyse de signaux.

## Pourquoi
Ce tutoriel prépare le TP01; ce n'est pas un cours Python exhaustif. Les étudiants doivent comprendre les outils, manipuler un tableau numérique, lire un CSV et interpréter des courbes.

## Déroulé attendu
1. Expliquer les concepts : interpréteur, terminal, environnement virtuel, dépendances, kernel Jupyter, cellule Markdown/code, chemin de fichier.
2. Installer Python **dans une version réellement compatible avec la chaîne ML du TP02**. Vérifier version, architecture et `pip`; ne pas imposer un dernier Python incompatible.
3. Créer `.venv`; documenter l'activation sous PowerShell, macOS et Linux, et la commande d'installation avec `python -m pip`.
4. Installer et vérifier JupyterLab ou VS Code + extensions Python/Jupyter, NumPy, Pandas, Matplotlib, SciPy et ipykernel; aider au choix du kernel. Une voie d'exécution suffit, l'autre est documentée.
5. Fonctions, listes et tableaux, slicing, opérations vectorielles, différence entre listes Python et `ndarray`; mini-exercices corrigés séparément.
6. Construire une série temporelle à fréquence connue, ajouter un bruit reproductible, expliquer t, amplitude, unité et `fs`.
7. Charger `sample_acceleration.csv` fourni dans le dépôt; vérifier colonnes, NaN, types et dimensions.
8. Produire un graphique `ax,ay,az` en fonction de `t`, une moyenne, l'écart-type et une RMS.
9. Faire un exercice autonome : repérer une erreur de timestamp ou un échantillon manquant, corriger ou exclure avec justification.
10. Exporter une figure PNG, un CSV nettoyé et redémarrer un kernel avant « Run all ».

## Contenu à générer
- `notebooks/01-python-basics.ipynb`, `02-numpy-pandas.ipynb`, `03-sensor-signals.ipynb`.
- `data/sample_acceleration.csv` explicitement synthétique et documenté, avec script de génération à seed fixe.
- `exercises/README.md` et `solutions/` distincts, tests de notebooks, requirements verrouillés et README avec procédures 3 OS.
- Captures réelles de création de l'environnement, sélection kernel et sorties Jupyter; captures non validées marquées TODO.
- Questions : pourquoi utiliser un venv ? pourquoi un signal de 100 Hz contient 100 échantillons par seconde ? que signifie g ? pourquoi la figure ne suffit pas à valider la qualité du CSV ?

## Critère de réussite
Installer proprement, ouvrir et exécuter les trois notebooks depuis zéro, expliquer les figures et produire un petit CSV/PNG. CI pour notebooks sans capteur, avec vérification d'outputs et absence de chemins absolus utilisateur.

## Références
Python venv : https://docs.python.org/3/library/venv.html
Jupyter : https://jupyterlab.readthedocs.io/
NumPy : https://numpy.org/doc/stable/
Pandas : https://pandas.pydata.org/docs/
Matplotlib : https://matplotlib.org/stable/
