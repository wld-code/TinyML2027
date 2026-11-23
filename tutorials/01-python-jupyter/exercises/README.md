# Exercices du tutoriel 01

Les solutions sont dans [../solutions/solutions.ipynb](../solutions/solutions.ipynb). Cherchez d'abord !

1. **Durée d'une fenêtre.** Écrivez une fonction `duree(n, fs)` qui renvoie la durée en secondes de `n` mesures prises à `fs` Hz. Combien durent 256 mesures sur la Nano originale (116,2 Hz mesurés) ? Et sur une Rev2, en supposant 100 Hz ?
2. **RMS.** Calculez la RMS de la liste `[0.1, -0.2, 0.15, -0.05]` de deux façons : avec une boucle Python, puis avec NumPy. Vérifiez que vous obtenez la même valeur.
3. **Défauts cachés.** Dans le notebook 03, partie 4, trouvez la mesure manquante et les deux instants inversés. Donnez leurs numéros de ligne et de `seq`.
4. **Pour aller plus loin.** Dans le notebook 02, changez `fs` à 10 Hz et `f` à 6 Hz. Le signal tracé ressemble-t-il encore à une sinusoïde à 6 Hz ? Expliquez avec la fréquence de Nyquist (fs / 2).
