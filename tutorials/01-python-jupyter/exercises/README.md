# Exercices du tutoriel 01

Les solutions sont dans [../solutions/solutions.ipynb](../solutions/solutions.ipynb). Cherchez d'abord !

1. **Durée d'une fenêtre.** Écrivez une fonction `duree(n, fs)` qui renvoie la durée en secondes de `n` mesures prises à `fs` Hz. Combien durent 256 mesures sur la Nano originale (116,2 Hz mesurés) ? Et sur une Rev2, en supposant 100 Hz ?
2. **RMS.** Calculez la RMS de la liste `[0.1, -0.2, 0.15, -0.05]` de deux façons : avec une boucle Python, puis avec NumPy. Vérifiez que vous obtenez la même valeur.
3. **Défauts cachés.** Dans le notebook 03, partie 4, trouvez la mesure manquante et les deux instants inversés. Donnez leurs numéros de ligne et de `seq`.
4. **Pour aller plus loin.** Dans le notebook 02, changez `fs` à 10 Hz et `f` à 6 Hz. Le signal tracé ressemble-t-il encore à une sinusoïde à 6 Hz ? Expliquez avec la fréquence de Nyquist (fs / 2).

## Corrigé

<details>
<summary>Afficher les réponses</summary>

1. La fonction peut renvoyer `n / fs`. Pour 256 mesures, cela donne environ 2,203 s à 116,2 Hz et 2,560 s à 100 Hz. Le temps entre le premier et le dernier échantillon couvre 255 intervalles. Ici, `n / fs` donne la durée nominale de la fenêtre.
2. La RMS vaut environ 0,13693. Avec une boucle, additionnez les carrés, divisez par quatre et prenez la racine carrée. Avec NumPy, utilisez `np.sqrt(np.mean(np.array(valeurs) ** 2))`.
3. Il manque `seq=400` entre les indices 399 et 400 du tableau, qui portent `seq=399` et `seq=401`. Les horodatages sont inversés entre les indices 699 et 700, pour `seq=700` et `seq=701`. Ces indices commencent à zéro et excluent l’en-tête du CSV.
4. À 10 Hz, la fréquence de Nyquist vaut 5 Hz. La sinusoïde à 6 Hz se replie à `10 − 6 = 4 Hz` dans les échantillons, avec une inversion de signe pour une sinusoïde de phase initiale nulle. C’est le repliement spectral. La courbe continue de référence peut toujours représenter le signal à 6 Hz si elle est tracée à partir d’un axe temporel plus fin.

</details>
