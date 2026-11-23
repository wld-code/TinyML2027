// Caractéristiques du contrat de données v0.2, en float32, pour la Nano.
// Référence : src/tinyml2027/features.py (float64). Les deux sont comparés par les
// golden vectors (mode REPLAY du firmware).
//
// Fenêtre de N = 256 échantillons x[n] (g) de l'axe ax, horodatés t_us[n] (µs).
//   fs      = (N − 1) / ((t[N−1] − t[0]) · 1e−6)                 (Hz)
//   c[n]    = x[n] − moyenne(x)
//   rms     = sqrt(moyenne(c²))                                  (g)
//   crest   = max|c| / rms ; si rms < 1e−6 g : crest = dominant_hz = band_power = 0
//   X[k]    = Σ c[n]·w[n]·e^(−2iπkn/N), w = Hann périodique
//   P[k]    = a_k·|X[k]|² / (fs·Σw²), a_k = 1 si k ∈ {0, N/2}, 2 sinon   (g²/Hz)
//   bande B = {k : 0,5 ≤ k·fs/N ≤ 10 Hz}
//   dominant_hz = f[argmax_{k∈B} P[k]] (plus petit indice si égalité)
//   band_power  = Σ_{k∈B} P[k] · fs/N                            (g²)
//
// La FFT est kissfft (FFT réelle kiss_fftr), livrée avec la bibliothèque officielle
// Arduino_TensorFlowLite (dossier third_party/kissfft). Elle est compilée en float par
// kissfft_float.cpp, dans ce dossier de sketch.
#pragma once

#include <math.h>
#include <stdint.h>

#include "third_party/kissfft/kiss_fft.h"
#include "third_party/kissfft/tools/kiss_fftr.h"

namespace motion {

constexpr int kN = 256;
constexpr int kLog2N = 8;
constexpr float kBandLowHz = 0.5f;
constexpr float kBandHighHz = 10.0f;
constexpr float kRmsEps = 1e-6f;  // contrat v0.3

struct Features {
  float fs_hz;
  float rms_g;
  float crest;
  float dominant_hz;
  float band_power_g2;
  bool rms_zero;
};

class Extractor {
 public:
  void begin() {
    sum_w2_ = 0.0f;
    for (int n = 0; n < kN; ++n) {
      window_[n] = 0.5f - 0.5f * cosf(2.0f * static_cast<float>(M_PI) * n / kN);
      sum_w2_ += window_[n] * window_[n];
    }
    size_t len = sizeof(fft_mem_);
    cfg_ = kiss_fftr_alloc(kN, 0, fft_mem_, &len);  // nullptr si fft_mem_ est trop petit
  }

  bool ready() const { return cfg_ != nullptr; }

  // x : N accélérations (g) ; t_us : N instants (µs), croissants.
  Features compute(const float* x, const uint32_t* t_us) {
    Features f;
    f.fs_hz = (kN - 1) / ((t_us[kN - 1] - t_us[0]) * 1e-6f);

    float mean = 0.0f;
    for (int n = 0; n < kN; ++n) mean += x[n];
    mean /= kN;

    float sum_c2 = 0.0f, max_abs = 0.0f;
    for (int n = 0; n < kN; ++n) {
      const float c = x[n] - mean;
      sum_c2 += c * c;
      if (fabsf(c) > max_abs) max_abs = fabsf(c);
      xw_[n] = c * window_[n];
    }
    f.rms_g = sqrtf(sum_c2 / kN);
    f.rms_zero = f.rms_g < kRmsEps;
    if (f.rms_zero) {  // fenêtre constante au bruit d'arrondi près : pas de spectre exploitable
      f.crest = f.dominant_hz = f.band_power_g2 = 0.0f;
      return f;
    }
    f.crest = max_abs / f.rms_g;

    kiss_fftr(cfg_, xw_, spec_);  // X[k], k = 0..N/2

    const float df = f.fs_hz / kN;
    const float scale = 1.0f / (f.fs_hz * sum_w2_);
    float best = -1.0f, band = 0.0f;
    int best_k = -1;
    for (int k = 0; k <= kN / 2; ++k) {
      const float fk = k * df;
      if (fk < kBandLowHz || fk > kBandHighHz) continue;
      const float a = (k == 0 || k == kN / 2) ? 1.0f : 2.0f;
      const float p = a * (spec_[k].r * spec_[k].r + spec_[k].i * spec_[k].i) * scale;
      band += p;
      if (p > best) {  // strictement supérieur : on garde le plus petit indice en cas d'égalité
        best = p;
        best_k = k;
      }
    }
    f.dominant_hz = best_k < 0 ? 0.0f : best_k * df;
    f.band_power_g2 = band * df;
    return f;
  }

 private:
  float window_[kN];
  float sum_w2_ = 0.0f;
  float xw_[kN];                 // signal centré et fenêtré
  kiss_fft_cpx spec_[kN / 2 + 1];  // spectre une face
  alignas(8) uint8_t fft_mem_[3072];  // 2 848 octets mesurés sur Mac 64 bits, moins sur la Nano (pointeurs 32 bits)
  kiss_fftr_cfg cfg_ = nullptr;
};

}  // namespace motion
