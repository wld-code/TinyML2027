"""Analyse E3 : orientations statiques, mouvement périodique, tapotements."""
import sys
import numpy as np
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as exc:  # environnement global incomplet : pas de figure
    plt = None
    print(f"(figure désactivée : {exc})")

path, fig_path = sys.argv[1], sys.argv[2]
raw = np.loadtxt(path, delimiter=",", skiprows=1)
seq, t_us = raw[:, 0].astype(np.int64), raw[:, 1].astype(np.int64)
t = (t_us - t_us[0]) * 1e-6
a = raw[:, 2:5]
dt = np.diff(t)
print(f"samples={len(raw)} duration_s={t[-1]:.1f} seq_first={seq[0]} seq_gaps={int((np.diff(seq)-1).sum())} "
      f"non_monotonic_t={int((dt<=0).sum())} fs_median={1/np.median(dt):.2f} fs_mean={(len(t)-1)/t[-1]:.2f} "
      f"dt_max_ms={dt.max()*1e3:.1f} gaps>1.5med={int((dt>1.5*np.median(dt)).sum())}")

fs = 1 / np.median(dt)
w = int(round(0.5 * fs))  # fenêtre glissante 0,5 s
def rolling_std(x, w):
    c1 = np.cumsum(np.insert(x, 0, 0.0)); c2 = np.cumsum(np.insert(x * x, 0, 0.0))
    m = (c1[w:] - c1[:-w]) / w; v = (c2[w:] - c2[:-w]) / w - m * m
    out = np.full(len(x), np.nan); h = w // 2
    out[h:h + len(v)] = np.sqrt(np.maximum(v, 0) * w / (w - 1))
    return out
roll_std = np.nanmax(np.stack([rolling_std(a[:, j], w) for j in range(3)]), axis=0)
roll_std = np.nan_to_num(roll_std, nan=1.0)
still = roll_std < 0.01

# segments immobiles >= 2 s
segs, start = [], None
for i, s in enumerate(still):
    if s and start is None:
        start = i
    if (not s or i == len(still) - 1) and start is not None:
        end = i
        if t[end] - t[start] >= 2.0:
            segs.append((start, end))
        start = None
print("\nSegments immobiles (>= 2 s) : orientation moyenne")
print(" debut_s  fin_s   ax_g    ay_g    az_g   |a|_g  axe_dominant")
for s, e in segs:
    m = a[s:e].mean(axis=0)
    k = int(np.argmax(np.abs(m)))
    print(f" {t[s]:6.1f} {t[e]:6.1f} {m[0]:+.3f} {m[1]:+.3f} {m[2]:+.3f}  {np.linalg.norm(m):.3f}  "
          f"{'+' if m[k]>0 else '-'}{'XYZ'[k]}")

# activité dynamique : écart-type glissant élevé
moving = roll_std > 0.05
print(f"\nDurée en mouvement (std 0,5 s > 0,05 g) : {moving.sum()/fs:.1f} s")

# mouvement périodique : plus long bloc continu de mouvement
best, cur_s = (0, 0), None
for i, m in enumerate(np.append(moving, False)):
    if m and cur_s is None:
        cur_s = i
    if not m and cur_s is not None:
        if i - cur_s > best[1] - best[0]:
            best = (cur_s, i)
        cur_s = None
s, e = best
if e - s > 2 * fs:
    seg = a[s:e] - a[s:e].mean(axis=0)
    ax_var = seg.var(axis=0)
    k = int(np.argmax(ax_var))
    x = seg[:, k] * np.hanning(len(seg))
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X = np.abs(np.fft.rfft(x))
    band = (f >= 0.3) & (f <= 10)
    fd = f[band][np.argmax(X[band])]
    print(f"Plus long mouvement continu : {t[s]:.1f}-{t[e-1]:.1f} s, axe le plus actif {'XYZ'[k]}, "
          f"écart-type par axe (g) = {np.sqrt(ax_var).round(3)}, fréquence dominante ≈ {fd:.2f} Hz")

# tapotements : pics de la dérivée hors du bloc périodique, après celui-ci
d = np.abs(np.diff(a, axis=0)).max(axis=1)
after = np.arange(len(d)) > e
thr = 0.03
idx = np.where((d > thr) & after)[0]
peaks = []
for i in idx:
    if not peaks or t[i] - t[peaks[-1]] > 0.15:
        peaks.append(i)
if peaks:
    span = t[peaks[-1]] - t[peaks[0]]
    print(f"Événements brefs après le mouvement (|Δa| > {thr} g) : {len(peaks)} sur {span:.1f} s "
          f"(≈ {len(peaks)/span if span>0 else 0:.2f} /s), |Δa| max = {d[after].max():.3f} g")
print(f"Pic absolu |a| max sur l'enregistrement : {np.linalg.norm(a,axis=1).max():.3f} g "
      f"(saturation à ±4 g : {'oui' if np.abs(a).max()>=3.99 else 'non'})")

if plt is None:
    sys.exit(0)
fig, axs = plt.subplots(2, 1, figsize=(12, 6), sharex=True, constrained_layout=True)
for j, n in enumerate(["ax_g", "ay_g", "az_g"]):
    axs[0].plot(t, a[:, j], lw=0.8, label=n)
for s_, e_ in segs:
    axs[0].axvspan(t[s_], t[e_], color="0.9", zorder=0)
axs[0].set_ylabel("accélération (g)")
axs[0].legend(loc="upper right")
axs[0].set_title("E3 — Nano 33 BLE Sense originale (LSM9DS1), mesure réelle — zones grises : immobile ≥ 2 s")
axs[1].plot(t, roll_std, lw=0.8, color="k")
axs[1].set_yscale("log")
axs[1].axhline(0.01, ls="--", color="tab:green")
axs[1].axhline(0.05, ls="--", color="tab:red")
axs[1].set_ylabel("écart-type glissant 0,5 s (g)")
axs[1].set_xlabel("temps carte t_us − t0 (s)")
fig.savefig(fig_path, dpi=120)
print(f"\nfigure: {fig_path}")
