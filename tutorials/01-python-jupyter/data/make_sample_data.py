"""Génère data/sample_acceleration.csv : un enregistrement SIMULÉ, avec deux défauts volontaires.

  uv run python tutorials/01-python-jupyter/data/make_sample_data.py

Données synthétiques (tinyml2027.simulate, seed 2027) : 10 s du geste « periodic »
(glissement d'environ 1 à 2 Hz sur ax) à ~114 Hz. On y introduit, pour l'exercice du
notebook 03 :
  - une mesure supprimée (seq 400 absent) ;
  - deux timestamps inversés (lignes de seq 700 et 701).
Ce fichier ne provient PAS de la carte : il sert à apprendre, pas à prouver.
"""
from pathlib import Path

from tinyml2027 import recording, simulate

df = simulate.recording("periodic", duration_s=10.0, seed=2027)
df = df[df.seq != 400].reset_index(drop=True)                    # mesure perdue
i = int(df.index[df.seq == 700][0])
df.loc[[i, i + 1], "t_us"] = df.loc[[i + 1, i], "t_us"].to_numpy()  # temps inversés
out = Path(__file__).with_name("sample_acceleration.csv")
recording.write_csv(df, out)
print(f"{out} : {len(df)} lignes")
