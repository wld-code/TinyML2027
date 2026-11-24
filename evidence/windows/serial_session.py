"""Envoie une commande à la carte et journalise ce qu'elle répond (preuves de la campagne Windows).

usage : uv run python evidence/windows/serial_session.py COM12 R 20 sortie.txt
        uv run python evidence/windows/serial_session.py COM12 L 75 sortie.txt --guide
--guide affiche, pendant le mode direct, quel geste faire (20 s chacun après 10 s d'attente).
"""
import sys
import time

import serial

port, cmd, duration, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
guide = "--guide" in sys.argv
steps = [(0, "IMMOBILE : posez la carte à plat, ne touchez à rien"),
         (25, "GLISSER : en avant / en arrière dans le sens du câble, ~1 aller-retour/s"),
         (50, "TAPOTER : la TABLE à 10 cm de la carte, 1 à 2 fois/s (jamais la carte)")]
with serial.Serial(port, 115200, timeout=0.2) as s, open(out, "w", encoding="utf-8", newline="\n") as f:
    time.sleep(2.0)
    s.reset_input_buffer()
    f.write(f"$ envoi '{cmd}' sur {port}, lecture {duration:.0f} s\n")
    s.write((cmd + "\n").encode())
    t0 = time.time()
    shown = -1
    while time.time() - t0 < duration:
        el = time.time() - t0
        if guide:
            for i, (t, msg) in enumerate(steps):
                if el >= t and i > shown:
                    shown = i
                    banner = f"\n>>>>>> [{el:4.0f} s] {msg}\n"
                    print(banner, flush=True)
                    f.write(f"# opérateur{banner}")
        line = s.readline().decode("utf-8", "replace").rstrip()
        if line:
            print(line, flush=True)
            f.write(line + "\n")
    if cmd == "L":
        # L est une bascule : on la renvoie pour laisser la carte à l'arrêt (sinon le L suivant l'arrête).
        s.write(b"L\n")
        t1 = time.time()
        while time.time() - t1 < 3:
            line = s.readline().decode("utf-8", "replace").rstrip()
            if line:
                f.write(line + "\n")
                if line.startswith("LIVE fin"):
                    print(line, flush=True)
                    break
print("fin de la lecture")
