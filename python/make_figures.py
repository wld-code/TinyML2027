"""Génère les figures et GIF des TP à partir des VRAIES données et des journaux de la carte.

  uv run python python/make_figures.py

Entrées : data/ (acquisitions TP01), results/tp01/features.csv, artifacts/motion/,
evidence/tp03/ (sorties série du test live). Sorties : docs/figures/*.png et *.gif.

Deux familles d'images, à ne pas confondre :
- « schéma » : dessin explicatif (gestes, découpage, chaîne de traitement) ;
- « mesure » : tracé de données réellement enregistrées sur la Nano V1 le 23/11/2026.
Le titre de chaque image indique sa famille.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import animation, patches  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tinyml2027 import dataset, features as F, recording  # noqa: E402

OUT = ROOT / "docs/figures"
COL = {"stationary": "#4c72b0", "periodic": "#dd8452", "impact": "#55a868"}
FR = {"stationary": "immobile (stationary)", "periodic": "glisser (periodic)", "impact": "tapoter (impact)"}
plt.rcParams.update({"figure.dpi": 110, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def load(session: str, cond: str) -> pd.DataFrame:
    return recording.read_csv(dataset.recording_path(ROOT / "data", session, f"{session}_{cond}_t01", True))


def save(fig, name):
    fig.savefig(OUT / name, bbox_inches="tight")
    plt.close(fig)
    print("  ", name)


# ------------------------------------------------------------------ schémas animés

def draw_board(ax, x, y, w=1.6, h=0.65, angle=0.0):
    board = patches.FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02",
                                   fc="#1f7a8c", ec="#155866", lw=2)
    chip = patches.Rectangle((x - 0.25, y - 0.18), 0.36, 0.36, fc="#1c1f22")
    imu = patches.Rectangle((x + 0.25, y - 0.1), 0.18, 0.18, fc="#1c1f22")
    usb = patches.Rectangle((x - w / 2 - 0.18, y - 0.12), 0.2, 0.24, fc="#a9b2b8", ec="#666")
    for p in (board, chip, imu, usb):
        ax.add_patch(p)
    ax.plot([x - w / 2 - 0.18, x - w / 2 - 1.6], [y, y + 0.05], color="#222", lw=4, solid_capstyle="round")
    return [board, chip, imu, usb]


def gesture_gif(cond: str, name: str):
    fig, ax = plt.subplots(figsize=(4.8, 2.8))
    frames = 48

    def frame(i):
        ax.clear()
        ax.set_xlim(-3, 3)
        ax.set_ylim(-1.4, 1.6)
        ax.axis("off")
        ax.add_patch(patches.Rectangle((-3, -1.4), 6, 0.9, fc="#c9b59a", ec="#a8916f"))
        t = i / frames * 2  # 2 secondes simulées par boucle
        x = 0.0
        if cond == "periodic":
            x = 0.9 * np.sin(2 * np.pi * 1.0 * t)
            ax.annotate("", xy=(2.2, 1.15), xytext=(-2.2, 1.15),
                        arrowprops=dict(arrowstyle="<->", color="#c2410c", lw=2.5))
            ax.text(0, 1.35, "glisser dans le sens du câble, ~1 aller-retour / s", ha="center", color="#c2410c")
        jitter = 0.0
        if cond == "impact":
            phase = (t * 1.5) % 1.0
            finger_y = 0.2 + 0.9 * min(1, abs(phase - 0.1) * 4)
            ax.add_patch(patches.FancyBboxPatch((1.85, finger_y - 0.05), 0.3, 0.9, boxstyle="round,pad=0.05",
                                                fc="#f1c27d", ec="#b48a4f"))
            if phase < 0.15:
                jitter = 0.04 * np.sin(phase * 200)
                for r in (0.25, 0.45):
                    ax.add_patch(patches.Arc((2.0, -0.35), r * 2, r, theta1=0, theta2=180, color="#c2410c", lw=2))
            ax.text(-0.6, 1.35, "tapoter la table à ~10 cm, 1 à 2 fois / s", ha="center", color="#c2410c")
        if cond == "stationary":
            ax.text(0, 1.35, "ne rien toucher : ni la carte, ni le câble", ha="center", color="#c2410c")
        draw_board(ax, x, -0.25 + jitter)
        ax.text(0, -1.25, "schéma (dessin), pas une photo", ha="center", fontsize=7, color="#555")
        return []

    anim = animation.FuncAnimation(fig, frame, frames=frames, interval=1000 * 2 / frames)
    anim.save(OUT / name, writer=animation.PillowWriter(fps=frames / 2))
    plt.close(fig)
    print("  ", name)


def windowing_gif(df: pd.DataFrame, name: str):
    t = df.t_us.to_numpy() * 1e-6
    x = df.ax_g.to_numpy()
    starts = list(range(0, len(df) - F.N + 1, F.HOP))[:8]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7, 4.2), gridspec_kw={"height_ratios": [2, 1]})

    def frame(i):
        a1.clear(); a2.clear()
        s = starts[i]
        a1.plot(t, x, color="#999", lw=0.8)
        a1.plot(t[s:s + F.N], x[s:s + F.N], color=COL["periodic"], lw=1.2)
        a1.axvspan(t[s], t[s + F.N - 1], color=COL["periodic"], alpha=0.12)
        if i > 0:
            p = starts[i - 1]
            a1.axvspan(t[p], t[p + F.N - 1], color="#888", alpha=0.08)
        a1.set_xlim(0, t[starts[-1] + F.N - 1])
        a1.set_ylabel("ax (g)")
        a1.set_title(f"MESURE (s01, glisser) — fenêtre n°{i + 1} : échantillons {s} à {s + F.N - 1}", fontsize=10)
        ft = F.compute(x[s:s + F.N], F.fs_window(df.t_us.to_numpy()[s:s + F.N]))
        a2.axis("off")
        a2.text(0.0, 0.75, f"N = 256 échantillons ≈ {t[s + F.N - 1] - t[s]:.2f} s, pas = 128 (recouvrement 50 %)", fontsize=9)
        a2.text(0.0, 0.35, f"rms = {ft.rms_g:.4f} g    crest = {ft.crest_factor:.2f}    "
                           f"dominant = {ft.dominant_hz:.2f} Hz    band power = {ft.band_power_g2:.2e} g²", fontsize=9,
                family="monospace")
        a1.set_xlabel("temps (s)")
        return []

    anim = animation.FuncAnimation(fig, frame, frames=len(starts), interval=900)
    anim.save(OUT / name, writer=animation.PillowWriter(fps=1.1))
    plt.close(fig)
    print("  ", name)


# ------------------------------------------------------------------ figures de mesure

def fig_signals():
    fig, axs = plt.subplots(3, 1, figsize=(8, 6), sharex=True)
    for ax, cond in zip(axs, F.FEATURES and ("stationary", "periodic", "impact")):
        df = load("s01", cond)
        t = df.t_us * 1e-6
        for a, c in (("ax_g", "#c44e52"), ("ay_g", "#8172b2"), ("az_g", "#64b5cd")):
            ax.plot(t, df[a] - (1.0 if a == "az_g" else 0.0), color=c, lw=0.7, label=a + (" − 1 g" if a == "az_g" else ""))
        ax.set_title(f"MESURE — session s01, {FR[cond]}", fontsize=10, loc="left")
        ax.set_ylabel("g")
        ax.set_xlim(0, 10)
    axs[0].legend(ncol=3, fontsize=8, loc="upper right")
    axs[-1].set_xlabel("temps (s), 10 premières secondes")
    fig.suptitle("Accélération brute sur les 3 axes (az décalé de −1 g pour retirer la gravité)", fontsize=11)
    save(fig, "tp01-signaux-3-conditions.png")


def fig_psd():
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    for cond in ("stationary", "periodic", "impact"):
        df = load("s01", cond)
        s = 1024
        x = df.ax_g.to_numpy()[s:s + F.N]
        fs = F.fs_window(df.t_us.to_numpy()[s:s + F.N])
        f, P = F.psd_one_sided(x - x.mean(), fs)
        ax.semilogy(f[1:], P[1:], color=COL[cond], label=FR[cond])
        ft = F.compute(x, fs)
        ax.plot(ft.dominant_hz, P[int(round(ft.dominant_hz * F.N / fs))], "o", color=COL[cond])
    ax.axvspan(0.5, 10, color="#e0e0e0", alpha=0.5, label="bande 0,5–10 Hz")
    ax.set_xlabel("fréquence (Hz)")
    ax.set_ylabel("PSD (g²/Hz)")
    ax.set_title("MESURE — densité spectrale de ax, une fenêtre de 256 par condition (s01) ; ● = dominant_hz", fontsize=10)
    ax.legend(fontsize=8)
    save(fig, "tp01-psd-3-conditions.png")


def fig_spectrogram():
    df = load("s01", "impact")
    fs = df.shape[0] / (df.t_us.iloc[-1] * 1e-6)
    fig, ax = plt.subplots(figsize=(7.5, 3))
    ax.specgram(df.ax_g - df.ax_g.mean(), NFFT=64, Fs=fs, noverlap=48, cmap="viridis")
    ax.set_ylim(0, 40)
    ax.set_xlabel("temps (s)")
    ax.set_ylabel("fréquence (Hz)")
    ax.set_title("MESURE — spectrogramme de ax pendant « tapoter » (s01) : chaque tapotement = trait vertical", fontsize=10)
    save(fig, "tp01-spectrogramme-impact.png")


def fig_features(table: pd.DataFrame):
    v = table[table.valid]
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.8))
    marks = {"s01": "o", "s02": "s", "s03": "^", "s04": "D", "s05": "x"}
    for (cond, ses), g in v.groupby(["condition", "session_id"]):
        axs[0].scatter(g.rms_g, g.crest_factor, s=16, color=COL[cond], marker=marks[ses], alpha=0.8,
                       label=f"{cond} {ses}" if ses == "s01" else None)
        axs[1].scatter(g.dominant_hz, g.band_power_g2, s=16, color=COL[cond], marker=marks[ses], alpha=0.8)
    axs[0].set_xscale("log"); axs[0].set_xlabel("rms_g (g, échelle log)"); axs[0].set_ylabel("crest_factor")
    axs[1].set_yscale("log"); axs[1].set_xlabel("dominant_hz (Hz)"); axs[1].set_ylabel("band_power_g2 (g², log)")
    axs[0].legend(fontsize=7)
    fig.suptitle("MESURE — les 4 features des 255 fenêtres (5 sessions ; marqueur = session : ○ s01 □ s02 △ s03 ◇ s04 × s05)",
                 fontsize=10)
    save(fig, "tp01-features-nuage.png")


def fig_drift(table: pd.DataFrame):
    v = table[table.valid & (table.condition != "stationary")]
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    sessions = sorted(v.session_id.unique())
    for j, cond in enumerate(("periodic", "impact")):
        data = [np.log10(v[(v.session_id == s) & (v.condition == cond)].rms_g) for s in sessions]
        pos = np.arange(len(sessions)) * 3 + j
        bp = ax.boxplot(data, positions=pos, widths=0.8, patch_artist=True, showfliers=False)
        for b in bp["boxes"]:
            b.set_facecolor(COL[cond])
    ax.set_xticks(np.arange(len(sessions)) * 3 + 0.5, sessions)
    ax.set_ylabel("log10(rms_g)")
    ax.set_title("MESURE — énergie par session : en s03, « tapoter » (vert) atteint le niveau de « glisser » (orange)",
                 fontsize=10)
    ax.legend([patches.Patch(color=COL[c]) for c in ("periodic", "impact")], ["glisser", "tapoter"], fontsize=8)
    save(fig, "tp02-derive-s03.png")


def fig_split():
    fig, ax = plt.subplots(figsize=(8, 2.6))
    ax.axis("off")
    for i, s in enumerate(["s01", "s02", "s03", "s04", "s05"]):
        test = s == "s05"
        ax.add_patch(patches.FancyBboxPatch((i * 1.6, 0.3), 1.4, 1.0, boxstyle="round,pad=0.03",
                                            fc="#f3d1c8" if test else "#d6e6f2", ec="#555"))
        ax.text(i * 1.6 + 0.7, 0.95, s, ha="center", fontsize=11, weight="bold")
        ax.text(i * 1.6 + 0.7, 0.55, "TEST\n(jamais vu)" if test else "entraînement", ha="center", fontsize=8)
    ax.text(3.2, 1.6, "validation croisée : on laisse de côté 1 session d'entraînement à la fois (4 plis)",
            ha="center", fontsize=9)
    ax.set_xlim(-0.2, 8); ax.set_ylim(0, 1.9)
    ax.set_title("SCHÉMA — partition par session : aucune fenêtre d'une session de test n'est vue à l'entraînement",
                 fontsize=10)
    save(fig, "tp02-partition-sessions.png")


def fig_leak():
    fig, ax = plt.subplots(figsize=(8, 2.2))
    ax.axis("off")
    for k in range(6):
        y = 1.2 - (k % 2) * 0.45
        ax.add_patch(patches.Rectangle((k * 1.0, y), 2.0, 0.35, fc="#d6e6f2" if k != 3 else "#f3d1c8", ec="#555"))
        ax.text(k * 1.0 + 1.0, y + 0.12, f"fenêtre {k + 1}" + (" (test)" if k == 3 else ""), ha="center", fontsize=8)
    ax.annotate("50 % des échantillons de la fenêtre 4 sont aussi dans les fenêtres 3 et 5 (train) : fuite",
                xy=(3.5, 0.75), xytext=(0.0, 0.15), fontsize=9, arrowprops=dict(arrowstyle="->"))
    ax.set_xlim(-0.2, 7.5); ax.set_ylim(0, 1.7)
    ax.set_title("SCHÉMA — pourquoi on ne tire PAS les fenêtres au hasard entre train et test", fontsize=10)
    save(fig, "tp02-fuite-fenetres.png")


def fig_confusion():
    m = json.loads((ROOT / "artifacts/motion/metrics.json").read_text())["test"]["dense"]
    cm = np.array(m["confusion"])
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    ax.imshow(cm, cmap="Blues")
    labels = ["stationary", "periodic", "impact"]
    ax.set_xticks(range(3), labels, rotation=20); ax.set_yticks(range(3), labels)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, cm[i, j], ha="center", va="center", color="white" if cm[i, j] > 8 else "black", fontsize=12)
    ax.set_xlabel("prédit"); ax.set_ylabel("vrai")
    ax.set_title(f"MESURE — réseau 4-8-3, test s05\naccuracy {m['accuracy']:.3f}, macro-F1 {m['macro_f1']:.3f}",
                 fontsize=10)
    save(fig, "tp02-confusion-test-s05.png")


def fig_pipeline():
    steps = ["IMU\nax (g)", "fenêtre\n256 mesures", "4 features\nFFT kissfft", "log10 +\nstandardisation",
             "quantif.\nint8", "réseau\n4-8-3", "label +\nscores"]
    fig, ax = plt.subplots(figsize=(10, 1.9))
    ax.axis("off")
    for i, s in enumerate(steps):
        ax.add_patch(patches.FancyBboxPatch((i * 1.45, 0.2), 1.2, 0.9, boxstyle="round,pad=0.04",
                                            fc="#e8f1ec" if i in (2, 3, 4) else "#d6e6f2", ec="#555"))
        ax.text(i * 1.45 + 0.6, 0.65, s, ha="center", va="center", fontsize=8.5)
        if i:
            ax.annotate("", xy=(i * 1.45 - 0.02, 0.65), xytext=(i * 1.45 - 0.25, 0.65), arrowprops=dict(arrowstyle="->"))
    ax.text(2 * 1.45, 1.3, "vert : doit être IDENTIQUE en Python et en C++ (golden vectors)", fontsize=8.5)
    ax.set_xlim(-0.1, 10.2); ax.set_ylim(0, 1.5)
    ax.set_title("SCHÉMA — ce que calcule la Nano toutes les 128 mesures (≈ 1,1 s)", fontsize=10)
    save(fig, "tp03-chaine-embarquee.png")


def fig_quant():
    man = json.loads((ROOT / "artifacts/motion/release_manifest.json").read_text())
    s, z = man["int8_input"]["scale"], man["int8_input"]["zero_point"]
    x = np.linspace(-4, 4, 800)
    q = np.clip(np.round(x / s + z), -128, 127)
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    ax.plot(x, q, color="#4c72b0")
    ax.axhline(127, ls=":", color="#c44e52"); ax.axhline(-128, ls=":", color="#c44e52")
    ax.set_xlabel("entrée standardisée x (sans unité)")
    ax.set_ylabel("code int8 q")
    ax.set_title(f"MESURE (paramètres du modèle) — q = clamp(round(x / {s:.4f}) + ({z}), −128, 127)", fontsize=10)
    lo, hi = (-128 - z) * s, (127 - z) * s
    ax.text(hi, 100, f" saturation au-delà de x = {hi:.2f}", color="#c44e52", fontsize=8, ha="right")
    ax.text(lo, -110, f" en dessous de x = {lo:.2f}", color="#c44e52", fontsize=8)
    save(fig, "tp03-quantification-entree.png")


def fig_live():
    fig, axs = plt.subplots(1, 3, figsize=(10, 2.8), sharey=True)
    for ax, cond in zip(axs, ("stationary", "periodic", "impact")):
        lines = (ROOT / f"evidence/tp03/tp03-live-{cond}-macos15.6-v1.txt").read_text().splitlines()
        rows = [dict(re.findall(r"(stationary|periodic|impact)=([0-9.]+)", l)) for l in lines
                if l.startswith("LIVE ") and "=" in l]
        k = np.arange(1, len(rows) + 1) * 128 / 116.2
        for c in ("stationary", "periodic", "impact"):
            ax.plot(k, [float(r[c]) for r in rows], "o-", ms=3, color=COL[c], label=c)
        ax.set_title(f"consigne : {FR[cond]}", fontsize=9)
        ax.set_xlabel("temps (s)")
    axs[0].set_ylabel("score")
    axs[0].legend(fontsize=7)
    fig.suptitle("MESURE — scores affichés par la Nano en direct (une classification toutes les ≈ 1,1 s)", fontsize=10)
    save(fig, "tp03-live-scores.png")


def fig_resources():
    names = ["hello_world\nofficiel", "sinus FP32\n(ex. 03)", "sinus INT8\n(ex. 05)", "infer_nano\n(TP03)"]
    flash = [345384, 142464, 142136, 183872]
    fig, ax = plt.subplots(figsize=(6.5, 3))
    ax.bar(names, np.array(flash) / 1024, color=["#999", "#4c72b0", "#4c72b0", "#55a868"])
    for i, v in enumerate(flash):
        ax.text(i, v / 1024 + 5, f"{v / 1024:.0f} Ko", ha="center", fontsize=8)
    ax.set_ylabel("Flash utilisée (Ko) sur 960")
    ax.set_title("MESURE — taille des programmes compilés (arduino-cli 1.5.1, mbed_nano 4.6.0)", fontsize=10)
    save(fig, "tp03-flash-programmes.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    table = pd.read_csv(ROOT / "results/tp01/features.csv")
    print("figures ->", OUT.relative_to(ROOT))
    for c in ("stationary", "periodic", "impact"):
        gesture_gif(c, f"geste-{c}.gif")
    windowing_gif(load("s01", "periodic"), "tp01-fenetrage.gif")
    fig_signals(); fig_psd(); fig_spectrogram(); fig_features(table)
    fig_drift(table); fig_split(); fig_leak(); fig_confusion()
    fig_pipeline(); fig_quant(); fig_live(); fig_resources()
    fig_six_positions()




def fig_six_positions():
    """Schéma des 6 positions + valeurs MESURÉES (evidence/phase6/imu_steps-macos15.6-v1.jsonl)."""
    rows = [json.loads(l) for l in (ROOT / "evidence/phase6/imu_steps-macos15.6-v1.jsonl").read_text().splitlines()]
    best = {}
    for r in rows:                     # garde la dernière mesure de chaque étape (l'étape 1 a été refaite)
        if r["etape"] <= 6:
            best[r["etape"]] = r
    titles = {1: "à plat, puces en haut", 2: "à plat, retournée", 3: "debout, USB en bas",
              4: "debout, USB en haut", 5: "debout, USB à gauche", 6: "debout, USB à droite"}
    fig, axs = plt.subplots(2, 3, figsize=(9, 5.4))
    for k, ax in zip(range(1, 7), axs.flat):
        ax.set_xlim(-1.5, 1.5); ax.set_ylim(-1.5, 1.6); ax.set_aspect("equal"); ax.axis("off")
        ax.add_patch(patches.Rectangle((-1.5, -1.5), 3, 0.25, fc="#c9b59a"))
        if k in (1, 2):
            ax.add_patch(patches.Rectangle((-0.9, -1.25), 1.8, 0.18, fc="#1f7a8c" if k == 1 else "#155866"))
            if k == 1:
                ax.add_patch(patches.Rectangle((-0.2, -1.07), 0.35, 0.1, fc="#1c1f22"))
            else:
                ax.add_patch(patches.Rectangle((-0.2, -1.35), 0.35, 0.1, fc="#1c1f22"))
        else:
            vert = k in (3, 4)
            w, h = (0.7, 1.8) if vert else (1.8, 0.7)
            ax.add_patch(patches.FancyBboxPatch((-w / 2, -0.9), w, h, boxstyle="round,pad=0.02", fc="#1f7a8c"))
            ax.add_patch(patches.Rectangle((-0.15, -0.9 + h / 2 - 0.15), 0.3, 0.3, fc="#1c1f22"))
            ux, uy = {3: (0, -0.9), 4: (0, 0.9), 5: (-0.9, -0.55), 6: (0.9, -0.55)}[k]
            ax.add_patch(patches.Rectangle((ux - 0.12, uy - 0.12), 0.24, 0.24, fc="#a9b2b8", ec="#555"))
            if k == 4:
                ax.text(ux + 0.25, uy, "USB", ha="left", va="center", fontsize=7)
            else:
                ax.text(ux, uy - 0.3, "USB", ha="center", fontsize=7)
        r = best[k]
        a = r["a_mean"]
        ax.set_title(f"{k}. {titles[k]}", fontsize=9)
        ax.text(0, 1.35, f"gravité sur {r['gravity']}", ha="center", fontsize=10, weight="bold", color="#c2410c")
        ax.text(0, 1.05, f"a = ({a[0]:+.2f}, {a[1]:+.2f}, {a[2]:+.2f}) g", ha="center", fontsize=8, family="monospace")
    fig.suptitle("SCHÉMAS des positions + valeurs MESURÉES sur la Nano V1 (23/11/2026)", fontsize=10)
    save(fig, "tuto02-six-positions.png")


if __name__ == "__main__":
    main()
