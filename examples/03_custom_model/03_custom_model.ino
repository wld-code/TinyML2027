// TinyML2027 — Phase 4/5 : notre modèle sinus FP32 sur la Nano 33 BLE Sense.
//
// Le modèle (model_data.h) et les valeurs attendues (test_vectors.h) sont générés
// par python/convert.py --mode fp32. Au démarrage, puis à chaque caractère reçu
// sur le port série, le firmware :
//   1. exécute le modèle sur les 23 entrées de test ;
//   2. affiche pour chacune : entrée, prédiction, valeur attendue (LiteRT desktop),
//      écart absolu, durée de Invoke() en µs et statut OK/ECART ;
//   3. termine par une ligne RESUME analysée par python/verify.py.
// Toute erreur (schéma, allocation, Invoke) est affichée, jamais masquée.

#include <TensorFlowLite.h>

#include "model_data.h"
#include "test_vectors.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"

namespace {
// Taille réservée pour les tenseurs intermédiaires. La valeur réellement utilisée
// est affichée (arena_used) : on peut ensuite réduire cette réserve en connaissance de cause.
constexpr int kArenaSize = 4096;
alignas(16) uint8_t tensor_arena[kArenaSize];

tflite::MicroInterpreter* interpreter = nullptr;
TfLiteTensor* input = nullptr;
TfLiteTensor* output = nullptr;
const char* init_error = nullptr;  // nullptr = initialisation réussie
}  // namespace

static uint32_t float_bits(float f) {
  uint32_t u;
  memcpy(&u, &f, sizeof u);
  return u;
}

static void print_hex32(uint32_t u) {
  char buf[11];
  snprintf(buf, sizeof buf, "0x%08lx", static_cast<unsigned long>(u));
  Serial.print(buf);
}

static const char* init_model() {
  const tflite::Model* model = tflite::GetModel(g_model);
  if (model->version() != TFLITE_SCHEMA_VERSION) return "schema_incompatible";

  // Seul l'opérateur réellement présent dans le modèle est enregistré
  // (FULLY_CONNECTED, ReLU fusionné). Un opérateur manquant ferait échouer AllocateTensors().
  static tflite::MicroMutableOpResolver<1> resolver;
  if (resolver.AddFullyConnected() != kTfLiteOk) return "resolver";

  static tflite::MicroInterpreter static_interpreter(model, resolver, tensor_arena, kArenaSize);
  interpreter = &static_interpreter;
  if (interpreter->AllocateTensors() != kTfLiteOk) return "AllocateTensors";

  input = interpreter->input(0);
  output = interpreter->output(0);
  if (input->type != kTfLiteFloat32 || output->type != kTfLiteFloat32) return "type_tenseur";
  return nullptr;
}

static void print_header() {
  Serial.println("# TinyML2027 examples/03_custom_model (FP32)");
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
  Serial.println("i,x,y,y_hex,y_attendu,ecart_abs,us,statut");
  int n_ok = 0, n_err = 0;
  float max_err = 0.0f;
  uint32_t us_min = UINT32_MAX, us_max = 0, us_sum = 0;

  for (int i = 0; i < kNumTests; ++i) {
    input->data.f[0] = kTestX[i];
    const uint32_t t0 = micros();
    const TfLiteStatus st = interpreter->Invoke();
    const uint32_t dt = micros() - t0;
    if (st != kTfLiteOk) {
      ++n_err;
      Serial.print(i);
      Serial.println(",,,,,,,ERREUR_INVOKE");
      continue;
    }
    const float y = output->data.f[0];
    const float err = fabsf(y - kExpectedY[i]);
    const bool ok = err <= kTolAbs;
    n_ok += ok;
    if (err > max_err) max_err = err;
    if (dt < us_min) us_min = dt;
    if (dt > us_max) us_max = dt;
    us_sum += dt;

    Serial.print(i);                 Serial.print(',');
    Serial.print(kTestX[i], 6);      Serial.print(',');
    Serial.print(y, 6);              Serial.print(',');
    print_hex32(float_bits(y));      Serial.print(',');
    Serial.print(kExpectedY[i], 6);  Serial.print(',');
    Serial.print(err, 9);            Serial.print(',');
    Serial.print(dt);                Serial.print(',');
    Serial.println(ok ? "OK" : "ECART");
  }

  Serial.print("RESUME mode=fp32 n=");
  Serial.print(kNumTests);
  Serial.print(" ok=");
  Serial.print(n_ok);
  Serial.print(" erreurs_invoke=");
  Serial.print(n_err);
  Serial.print(" ecart_max=");
  Serial.print(max_err, 9);
  Serial.print(" tolerance=");
  Serial.print(kTolAbs, 9);
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
  // Relance la série de tests à chaque caractère reçu (Entrée dans le moniteur).
  if (Serial.available() > 0) {
    while (Serial.available() > 0) Serial.read();
    run_tests();
  }
}
