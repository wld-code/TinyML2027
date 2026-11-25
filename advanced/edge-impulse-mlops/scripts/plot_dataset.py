"""Trace des clips de promotion et les niveaux mesurés sur leurs WAV."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import SymLogNorm
import numpy as np
from scipy.fft import dct
from scipy.signal import stft

from prepare_dataset import LABELS, SR, fixed_clip, read_wav


def spectral_views(signal):
    frequency, time, spectrum = stft(signal, fs=SR, nperseg=320, noverlap=160, nfft=512)
    power = np.abs(spectrum) ** 2
    mel_high = 2595 * np.log10(1 + (SR / 2) / 700)
    edges = 700 * (10 ** (np.linspace(0, mel_high, 34) / 2595) - 1)
    lower, center, upper = edges[:-2, None], edges[1:-1, None], edges[2:, None]
    filters = np.maximum(0, np.minimum((frequency - lower) / (center - lower),
                                      (upper - frequency) / (upper - center)))
    mfcc = dct(np.log(np.maximum(filters @ power, 1e-12)), axis=0, norm="ortho")[:13]
    return frequency, time, 10 * np.log10(np.maximum(power, 1e-12)), mfcc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=Path("data/edge-impulse-mlops/datasets"), type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    with (args.data / "manifest.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    def read(row):
        return fixed_clip(read_wav(args.data / row["split"] / f'{row["sample_id"]}.wav'))

    clean = next(row for row in rows if row["split"] == "evaluation-clean" and row["label"] == "stop")
    shifted = next(row for row in rows if row["split"] == "evaluation-shifted" and row["pair_id"] == clean["pair_id"])
    args.out.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(3, 2, figsize=(10, 7), layout="constrained")
    fig.suptitle(f'Commande « stop » · paire {clean["pair_id"]}')
    for column, row in enumerate((clean, shifted)):
        samples = read(row)
        frequency, time, power, mfcc = spectral_views(samples)
        axes[0, column].set_title("Propre" if column == 0 else f'Dégradée · SNR {row["snr_db"]} dB')
        axes[0, column].plot(np.arange(SR) / SR, samples, linewidth=0.55)
        axes[0, column].set(ylabel="Amplitude normalisée", ylim=(-1, 1))
        spec = axes[1, column].pcolormesh(time, frequency, power, vmin=-85, vmax=-20, cmap="magma")
        axes[1, column].set(ylabel="Fréquence (Hz)")
        coeff = axes[2, column].pcolormesh(time, np.arange(13), mfcc, cmap="coolwarm", norm=SymLogNorm(linthresh=5, vmin=-90, vmax=90))
        axes[2, column].set(xlabel="Temps (s)", ylabel="Indice MFCC", yticks=(0, 3, 6, 9, 12))
    fig.colorbar(spec, ax=axes[1], label="Puissance (dB, réf. 1)")
    fig.colorbar(coeff, ax=axes[2], label="Coefficient")
    fig.savefig(args.out / "audio-paire.png", dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(9, 3), sharex=True, layout="constrained")
    for ax, label in zip(axes, LABELS):
        for split, title in (("evaluation-clean", "Propre"), ("evaluation-shifted", "Dégradée")):
            levels = [20 * np.log10(max(np.sqrt(np.mean(read(row) ** 2)), 1e-6))
                      for row in rows if row["label"] == label and row["split"] == split]
            ax.hist(levels, bins=np.arange(-90, 1, 5), histtype="step", linewidth=1.6, label=title)
        ax.set(title=label, xlabel="RMS (dBFS)")
    axes[0].set_ylabel("Nombre de clips")
    axes[-1].legend()
    fig.savefig(args.out / "distribution-rms.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
