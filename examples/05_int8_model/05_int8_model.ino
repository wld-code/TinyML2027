// TinyML2027 — Phase 7 : le même modèle sinus, quantifié en INT8 complet.
//
// Le modèle (model_data.h) et les codes attendus (test_vectors.h) sont générés par
// python/convert.py --mode int8. Différences avec examples/03_custom_model :
//   - l'entrée float est quantifiée sur la carte : q = round(x / scale) + zero_point,
//     saturée à [-128, 127] ;
//   - la sortie int8 est dé-quantifiée : y = (q - zero_point) * scale ;
//   - la comparaison avec LiteRT desktop porte sur le code int8 (tolérance kTolLsb).
// Au démarrage, puis à chaque caractère reçu, la série de 23 tests est exécutée.

#include <TensorFlowLite.h>

#include "model_data.h"
#include "test_vectors.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"

namespace {
constexpr int kArenaSize = 4096;
alignas(16) uint8_t tensor_arena[kArenaSize];

tflite::MicroInterpreter* interpreter = nullptr;
TfLiteTensor* input = nullptr;
TfLiteTensor* output = nullptr;
const char* init_error = nullptr;
}  // namespace

static const char* init_model() {
  const tflite::Model* model = tflite::GetModel(g_model);
  if (model->version() != TFLITE_SCHEMA_VERSION) return "schema_incompatible";

  static tflite::MicroMutableOpResolver<1> resolver;
  if (resolver.AddFullyConnected() != kTfLiteOk) return "resolver";

  static tflite::MicroInterpreter static_interpreter(model, resolver, tensor_arena, kArenaSize);
  interpreter = &static_interpreter;
  if (interpreter->AllocateTensors() != kTfLiteOk) return "AllocateTensors";

  input = interpreter->input(0);
  output = interpreter->output(0);
  if (input->type != kTfLiteInt8 || output->type != kTfLiteInt8) return "type_tenseur";
  return nullptr;
}

// Quantification de l'entrée avec arrondi au plus proche et saturation explicite :
// une valeur hors de la plage de calibration n'est pas « inventée », elle est bornée.
static int8_t quantize_input(float x) {
  const float q = roundf(x / input->params.scale) + input->params.zero_point;
  if (q < -128.0f) return -128;
  if (q > 127.0f) return 127;
  return static_cast<int8_t>(q);
}

static void print_header() {
  Serial.println("# TinyML2027 examples/05_int8_model (INT8)");
  Serial.print("# model_sha256=");
  Serial.println(g_model_sha256);
  Serial.print("# model_bytes=");
  Serial.print(g_model_len);
  Serial.print(" schema=");
  Serial.print(TFLITE_SCHEMA_VERSION);
  Serial.print(" arena_size=");
  Serial.print(kArenaSize);
  if (init_error == nullptr) {
    Serial.print(" arena_used=");
    Serial.println(static_cast<unsigned long>(interpreter->arena_used_bytes()));
    Serial.print("# in_scale=");
    Serial.print(input->params.scale, 9);
    Serial.print(" in_zero_point=");
    Serial.print(input->params.zero_point);
    Serial.print(" out_scale=");
    Serial.print(output->params.scale, 9);
    Serial.print(" out_zero_point=");
    Serial.println(output->params.zero_point);
  } else {
    Serial.println();
  }
}

static void run_tests() {
  print_header();
  if (init_error != nullptr) {
    Serial.print("ERREUR init=");
    Serial.println(init_error);
    return;
  }
  Serial.println("i,x,x_q,y_q,y,attendu_q,ecart_lsb,us,statut");
  int n_ok = 0, n_err = 0, max_lsb = 0;
  uint32_t us_min = UINT32_MAX, us_max = 0, us_sum = 0;

  for (int i = 0; i < kNumTests; ++i) {
    const int8_t xq = quantize_input(kTestX[i]);
    input->data.int8[0] = xq;
    const uint32_t t0 = micros();
    const TfLiteStatus st = interpreter->Invoke();
    const uint32_t dt = micros() - t0;
    if (st != kTfLiteOk) {
      ++n_err;
      Serial.print(i);
      Serial.println(",,,,,,,,ERREUR_INVOKE");
      continue;
    }
    const int8_t yq = output->data.int8[0];
    const float y = (yq - output->params.zero_point) * output->params.scale;
    const int lsb = abs(static_cast<int>(yq) - static_cast<int>(kExpectedQ[i]));
    const bool ok = lsb <= kTolLsb;
    n_ok += ok;
    if (lsb > max_lsb) max_lsb = lsb;
    if (dt < us_min) us_min = dt;
    if (dt > us_max) us_max = dt;
    us_sum += dt;

    Serial.print(i);              Serial.print(',');
    Serial.print(kTestX[i], 6);   Serial.print(',');
    Serial.print(xq);             Serial.print(',');
    Serial.print(yq);             Serial.print(',');
    Serial.print(y, 6);           Serial.print(',');
    Serial.print(kExpectedQ[i]);  Serial.print(',');
    Serial.print(lsb);            Serial.print(',');
    Serial.print(dt);             Serial.print(',');
    Serial.println(ok ? "OK" : "ECART");
  }

  Serial.print("RESUME mode=int8 n=");
  Serial.print(kNumTests);
  Serial.print(" ok=");
  Serial.print(n_ok);
  Serial.print(" erreurs_invoke=");
  Serial.print(n_err);
  Serial.print(" ecart_max_lsb=");
  Serial.print(max_lsb);
  Serial.print(" tolerance_lsb=");
  Serial.print(kTolLsb);
  Serial.print(" us_min=");
  Serial.print(us_min);
  Serial.print(" us_max=");
  Serial.print(us_max);
  Serial.print(" us_moy=");
  Serial.println(static_cast<float>(us_sum) / kNumTests, 1);
  Serial.println(n_ok == kNumTests ? "STATUT OK" : "STATUT ECHEC");
}

void setup() {
  Serial.begin(115200);
  const unsigned long t0 = millis();
  while (!Serial && millis() - t0 < 3000) {
  }
  init_error = init_model();
  run_tests();
}

void loop() {
  if (Serial.available() > 0) {
    while (Serial.available() > 0) Serial.read();
    run_tests();
  }
}
