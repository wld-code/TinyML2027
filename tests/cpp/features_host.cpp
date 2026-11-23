// Test hôte (Mac/Linux) : features.h (float32) contre les golden vectors Python (float64).
// Compilé et lancé par tests/test_features_cpp.py ; imprime une ligne par fenêtre.
#include <cstdio>
#include <cmath>
#include "../../labs/03-embedded-inference/firmware/infer_nano/features.h"
#include "../../labs/03-embedded-inference/firmware/infer_nano/golden.h"

int main() {
  static motion::Extractor ex;
  ex.begin();
  if (!ex.ready()) { std::printf("ERREUR kiss_fftr_alloc\n"); return 1; }
  for (int g = 0; g < kNumGolden; ++g) {
    uint32_t t[256];
    for (int n = 0; n < 256; ++n) t[n] = static_cast<uint32_t>(kGoldenT[g][n]);
    const motion::Features f = ex.compute(kGoldenAx[g], t);
    std::printf("%s %.9g %.9g %.9g %.9g %.9g\n", kGoldenName[g], f.rms_g, f.crest, f.dominant_hz,
                f.band_power_g2, f.fs_hz);
  }
  return 0;
}
