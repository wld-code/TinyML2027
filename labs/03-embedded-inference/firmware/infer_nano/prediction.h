// Résultat d'une classification : tout ce qui est affiché ou comparé aux golden vectors.
#pragma once
#include <stdint.h>
#include "features.h"
#include "model_params.h"

struct Prediction {
  motion::Features f;
  float x[4];              // entrées standardisées
  int8_t xq[4];            // entrées quantifiées
  int8_t yq[kNumClasses];  // sorties int8 du réseau
  float p[kNumClasses];    // scores dé-quantifiés (≈ probabilités softmax)
  int label;
  uint32_t feat_us, invoke_us;
  bool ok;
};
