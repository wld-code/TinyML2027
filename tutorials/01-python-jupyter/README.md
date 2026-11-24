# Tutoriel 01 — Python, Jupyter et premiers signaux

**Durée.** Environ 2 h. **Matériel.** Un ordinateur. **Prérequis.** Installez Git et uv selon le [guide d’installation](../../docs/INSTALLATION.md), puis clonez le dépôt. Sous Windows, utilisez Git Bash.

Nous allons ouvrir des notebooks, manipuler un signal échantillonné et vérifier un fichier de capteur avant de le tracer. Un notebook est un document qui réunit des cellules de texte, de code et de résultats.

## 1. Préparer Python

Si vous avez déjà lancé `./scripts/setup.sh`, passez au contrôle. Pour installer Python et les bibliothèques du cours seulement, lancez ces commandes depuis le dossier qui contient le dépôt.

```sh
cd TinyML2027
uv sync --frozen
```

Le fichier `uv.lock` fixe les versions des bibliothèques. L’environnement virtuel `.venv` isole le Python et les bibliothèques du projet.

```sh
uv run python --version          # Python 3.12.7
uv run python -c "import numpy, pandas, matplotlib, scipy; print('OK')"
```

Vérifiez que la première commande affiche Python 3.12.7 et que la seconde affiche `OK`.

## 2. Ouvrir JupyterLab

```sh
uv run jupyter lab tutorials/01-python-jupyter/notebooks
```

Dans le navigateur, ouvrez `01-python-basics.ipynb`. Exécutez la première cellule avec **Maj + Entrée**. Le *kernel* est le processus Python qui exécute les cellules. Vérifiez que la cellule affiche `Environnement : .venv`. Si elle signale un mauvais kernel, relancez JupyterLab avec la commande ci-dessus.

![Navigateur de fichiers, cellules et kernel dans JupyterLab](../../docs/screenshots/tuto01-etape02-jupyterlab-notebook03-macos.png)

Si vous utilisez VS Code, installez les extensions Python et Jupyter, ouvrez le dépôt et choisissez l’interpréteur avec **Select Kernel**. Sélectionnez `.venv/bin/python`, ou `.venv\Scripts\python.exe` sous Windows.

## 3. Lire et contrôler un signal

Ouvrez les trois notebooks dans l’ordre et exécutez les cellules en suivant les consignes.

1. [Bases de Python](notebooks/01-python-basics.ipynb) — manipulez des listes et des dictionnaires et écrivez des fonctions simples.
2. [NumPy et pandas](notebooks/02-numpy-pandas.ipynb) — construisez un signal à 1,5 Hz échantillonné à 100 Hz, soit 100 mesures par seconde. Comparez le signal bruité et la sinusoïde, puis calculez la moyenne, l’écart-type et la valeur efficace (RMS).
3. [Signaux de capteur](notebooks/03-sensor-signals.ipynb) — vérifiez les colonnes, les types et les valeurs manquantes du CSV, calculez la cadence et tracez le signal. Si le fichier est introuvable, vérifiez que vous avez ouvert le notebook depuis le dossier `notebooks/`.

Le fichier [sample_acceleration.csv](data/sample_acceleration.csv) est simulé dans le format du TP01. Il contient deux défauts introduits pour l’exercice. À la fin du notebook 03, vérifiez que les défauts apparaissent entre les lignes `(399, 400)` et `(699, 700)`. La plus longue portion continue va de 700 à 1138, soit 439 mesures. Vérifiez la présence de `signal.png` et de `sample_acceleration_clean.csv` dans `tutorials/01-python-jupyter/output/`.

## 4. Vérifier la reproductibilité

Dans chaque notebook, choisissez **Kernel → Restart Kernel and Run All Cells**. Les cellules doivent s’exécuter dans l’ordre. Si une variable manque, vérifiez qu’une cellule précédente la définit.

```sh
uv run pytest --nbmake tutorials/01-python-jupyter
```

Attendez `4 passed`. Le test inclut le notebook de solutions.

## Exercices

Faites les [exercices](exercises/README.md), puis comparez vos réponses aux [solutions](solutions/solutions.ipynb).

1. Quel rôle joue l’environnement virtuel lorsque Jupyter exécute une cellule ?
2. Combien de mesures attendez-vous sur deux secondes à 100 Hz ?
3. Pourquoi vérifier les numéros de mesure et les horodatages avant de tracer le signal ?
