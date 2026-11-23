// Généré par python -m tinyml2027.quantize_motion : ne pas modifier à la main.
// Prétraitement appris sur les sessions s01, s02, s03, s04 (artifacts/motion/preprocessing.json).
#pragma once
constexpr char kModelVersion[] = "motion-v1";
constexpr char kFeatureSchema[] = "log10(rms_g + 1e-6);crest_factor;dominant_hz;log10(band_power_g2 + 1e-12)";
constexpr int kNumClasses = 3;
const char* const kLabels[kNumClasses] = {"stationary", "periodic", "impact"};
constexpr float kLogEpsRms = 1e-06f;
constexpr float kLogEpsBand = 1e-12f;
const float kMean[4] = {-2.23938078f, 4.4306824f, 5.41916659f, -5.0699798f};
const float kStd[4] = {0.797792693f, 2.05859123f, 3.66939897f, 1.8247279f};
