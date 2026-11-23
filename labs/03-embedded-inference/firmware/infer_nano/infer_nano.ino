// TinyML2027 — TP03 : reconnaissance de mouvements sur la Nano 33 BLE Sense.
//
//
// Deux modes, choisis par une commande sur le port série (115200 bauds) :
//   R  REPLAY : rejoue les golden vectors (golden.h). Pour chaque fenêtre brute, la
//      carte calcule les features, les entrées standardisées, les codes int8 et la
//      sortie du réseau, et les compare aux valeurs Python/LiteRT. Termine par
//      « REPLAY STATUT OK » ou « REPLAY STATUT ECHEC ». Exécuté aussi au démarrage.
//   L  LIVE : lit l'accéléromètre en continu ; toutes les 128 nouvelles mesures,
//      classe la fenêtre des 256 dernières. Une nouvelle commande L arrête le live.
// Le modèle (model_data.h), le prétraitement (model_params.h) et les golden vectors
// sont générés par : uv run python -m tinyml2027.quantize_motion

#include <TensorFlowLite.h>

#include "features.h"
#include "golden.h"
#include "model_data.h"
#include "model_params.h"
#include "prediction.h"  // struct Prediction (dans un en-tête : l'IDE Arduino génère les prototypes avant le code)
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"

// ---- Choix de l'IMU selon la révision de la carte ---------------------------------
// Nano 33 BLE Sense originale (ABX00031) : rien à changer, IMU LSM9DS1.
// Nano 33 BLE Sense Rev2 (ABX00069)      : décommentez la ligne suivante, IMU BMI270.
//   (avec les scripts du dépôt : REV=rev2 ./scripts/compile.sh ... fait la même chose)
// #define NANO_REV2
#if defined(NANO_REV2)
#include <Arduino_BMI270_BMM150.h>  // bibliothèque officielle Arduino, Rev2
const char kImuName[] = "BMI270";
const char kBoardRevision[] = "rev2";
const char kWrongBoard[] = "BMI270 absent : carte originale ? Commentez #define NANO_REV2.";
#else
#include <Arduino_LSM9DS1.h>        // bibliothèque officielle Arduino, carte originale
const char kImuName[] = "LSM9DS1";
const char kBoardRevision[] = "original";
const char kWrongBoard[] = "LSM9DS1 absent : carte Rev2 ? Decommentez #define NANO_REV2.";
#endif
// Les deux bibliothèques offrent le même objet IMU : accélération en g, rotation en °/s.

// Lit une nouvelle mesure d'accélération si le capteur en a une ; false sinon.
static bool read_accel(float& x, float& y, float& z) {
  return IMU.accelerationAvailable() && IMU.readAcceleration(x, y, z) == 1;
}


namespace {
constexpr char kFirmware[] = "infer_nano 0.1.0";
constexpr int kArenaSize = 4096;
constexpr int kHop = 128;
constexpr float kGapFactor = 1.5f;      // contrat : intervalle > 1,5 × médiane = lacune
constexpr float kMinConfidence = 0.6f;  // en dessous : la prédiction est signalée « incertaine »

alignas(16) uint8_t tensor_arena[kArenaSize];
tflite::MicroInterpreter* interpreter = nullptr;
TfLiteTensor* input = nullptr;
TfLiteTensor* output = nullptr;
const char* init_error = nullptr;
motion::Extractor extractor;

// Tampon circulaire des dernières mesures (mode live).
float ring_ax[motion::kN];
uint32_t ring_t[motion::kN];
uint32_t n_samples = 0;    // nombre total de mesures depuis le début du live
uint32_t since_last = 0;   // mesures reçues depuis la dernière classification
bool live = false;
bool imu_ok = false;
float win_ax[motion::kN];
uint32_t win_t[motion::kN];
}  // namespace

// ---------- modèle ----------

static const char* init_model() {
  const tflite::Model* model = tflite::GetModel(g_model);
  if (model->version() != TFLITE_SCHEMA_VERSION) return "schema_incompatible";
  static tflite::MicroMutableOpResolver<2> resolver;  // exactement les opérateurs du modèle
  if (resolver.AddFullyConnected() != kTfLiteOk) return "resolver_fc";
  if (resolver.AddSoftmax() != kTfLiteOk) return "resolver_softmax";
  static tflite::MicroInterpreter static_interpreter(model, resolver, tensor_arena, kArenaSize);
  interpreter = &static_interpreter;
  if (interpreter->AllocateTensors() != kTfLiteOk) return "AllocateTensors";
  input = interpreter->input(0);
  output = interpreter->output(0);
  if (input->type != kTfLiteInt8 || output->type != kTfLiteInt8) return "type_tenseur";
  if (input->dims->data[input->dims->size - 1] != 4) return "dimension_entree";
  if (output->dims->data[output->dims->size - 1] != kNumClasses) return "dimension_sortie";
  return nullptr;
}

static int8_t quantize(float v) {
  const float q = roundf(v / input->params.scale) + input->params.zero_point;
  return q < -128.0f ? -128 : (q > 127.0f ? 127 : static_cast<int8_t>(q));
}

// Fenêtre brute -> features -> prétraitement -> int8 -> réseau -> scores.
static Prediction classify(const float* ax, const uint32_t* t_us) {
  Prediction r;
  uint32_t t0 = micros();
  r.f = extractor.compute(ax, t_us);
  const float raw[4] = {log10f(r.f.rms_g + kLogEpsRms), r.f.crest, r.f.dominant_hz,
                        log10f(r.f.band_power_g2 + kLogEpsBand)};
  for (int i = 0; i < 4; ++i) {
    r.x[i] = (raw[i] - kMean[i]) / kStd[i];
    r.xq[i] = quantize(r.x[i]);
    input->data.int8[i] = r.xq[i];
  }
  r.feat_us = micros() - t0;
  t0 = micros();
  r.ok = interpreter->Invoke() == kTfLiteOk;
  r.invoke_us = micros() - t0;
  r.label = 0;
  for (int c = 0; c < kNumClasses; ++c) {
    r.yq[c] = output->data.int8[c];
    r.p[c] = (r.yq[c] - output->params.zero_point) * output->params.scale;
    if (r.p[c] > r.p[r.label]) r.label = c;
  }
  return r;
}

// ---------- REPLAY ----------

static bool rel_ok(float got, float exp) {
  return fabsf(got - exp) <= kTolRelFeature * fabsf(exp) + 1e-12f;
}

static void replay() {
  Serial.println("REPLAY debut");
  Serial.println("nom,rms,crest,dominant_hz,band_power,features,xq,yq,classe,attendu,feat_us,invoke_us,statut");
  int n_ok = 0;
  uint32_t feat_max = 0, inv_max = 0;
  for (int g = 0; g < kNumGolden; ++g) {
    uint32_t t[motion::kN];
    for (int n = 0; n < motion::kN; ++n) t[n] = kGoldenT[g][n];
    const Prediction r = classify(kGoldenAx[g], t);
    const float* e = kGoldenFeat[g];
    bool feat_ok;
    if (e[0] < motion::kRmsEps) {
      feat_ok = r.f.rms_zero && r.f.crest == 0.0f && r.f.dominant_hz == 0.0f && r.f.band_power_g2 == 0.0f;
    } else {
      const float df = r.f.fs_hz / motion::kN;
      feat_ok = rel_ok(r.f.rms_g, e[0]) && rel_ok(r.f.crest, e[1]) && rel_ok(r.f.band_power_g2, e[3]) &&
                fabsf(r.f.dominant_hz - e[2]) <= kTolDominantBins * df * 1.0001f;
    }
    int dxq = 0, dyq = 0;
    for (int i = 0; i < 4; ++i) dxq = max(dxq, abs(r.xq[i] - kGoldenXq[g][i]));
    int exp_label = 0;
    for (int c = 0; c < kNumClasses; ++c) {
      dyq = max(dyq, abs(r.yq[c] - kGoldenYq[g][c]));
      if (kGoldenYq[g][c] > kGoldenYq[g][exp_label]) exp_label = c;
    }
    const bool ok = r.ok && feat_ok && dxq <= kTolInputLsb && dyq <= kTolOutputLsb && r.label == exp_label;
    n_ok += ok;
    feat_max = max(feat_max, r.feat_us);
    inv_max = max(inv_max, r.invoke_us);

    Serial.print(kGoldenName[g]);       Serial.print(',');
    Serial.print(r.f.rms_g, 7);          Serial.print(',');
    Serial.print(r.f.crest, 5);          Serial.print(',');
    Serial.print(r.f.dominant_hz, 4);    Serial.print(',');
    Serial.print(r.f.band_power_g2, 9);  Serial.print(',');
    Serial.print(feat_ok ? "OK" : "ECART"); Serial.print(',');
    Serial.print(dxq);                   Serial.print("lsb,");
    Serial.print(dyq);                   Serial.print("lsb,");
    Serial.print(kLabels[r.label]);      Serial.print(',');
    Serial.print(kLabels[exp_label]);    Serial.print(',');
    Serial.print(r.feat_us);             Serial.print(',');
    Serial.print(r.invoke_us);           Serial.print(',');
    Serial.println(ok ? "OK" : "ECART");
  }
  Serial.print("REPLAY RESUME n=");
  Serial.print(kNumGolden);
  Serial.print(" ok=");
  Serial.print(n_ok);
  Serial.print(" feat_us_max=");
  Serial.print(feat_max);
  Serial.print(" invoke_us_max=");
  Serial.println(inv_max);
  Serial.println(n_ok == kNumGolden ? "REPLAY STATUT OK" : "REPLAY STATUT ECHEC");
}

// ---------- LIVE ----------

// Copie les 256 dernières mesures dans l'ordre chronologique et vérifie la règle de
// validité du contrat (temps croissant, aucune lacune > 1,5 × médiane).
static bool snapshot_window() {
  const uint32_t start = n_samples % motion::kN;  // plus ancienne mesure du tampon
  for (int n = 0; n < motion::kN; ++n) {
    win_ax[n] = ring_ax[(start + n) % motion::kN];
    win_t[n] = ring_t[(start + n) % motion::kN];
  }
  static uint32_t dt[motion::kN - 1];
  for (int n = 0; n < motion::kN - 1; ++n) {
    if (win_t[n + 1] <= win_t[n]) return false;
    dt[n] = win_t[n + 1] - win_t[n];
  }
  // médiane approchée par comptage : l'intervalle nominal est ~8,6 ms, on prend la
  // valeur telle qu'au moins la moitié des intervalles lui soient inférieurs ou égaux.
  uint32_t lo = 0xFFFFFFFF, hi = 0;
  for (int n = 0; n < motion::kN - 1; ++n) { lo = min(lo, dt[n]); hi = max(hi, dt[n]); }
  while (lo < hi) {
    const uint32_t mid = lo + (hi - lo) / 2;
    int count = 0;
    for (int n = 0; n < motion::kN - 1; ++n) count += dt[n] <= mid;
    if (count >= (motion::kN - 1 + 1) / 2) hi = mid; else lo = mid + 1;
  }
  for (int n = 0; n < motion::kN - 1; ++n) {
    if (dt[n] > kGapFactor * lo) return false;
  }
  return true;
}

static void live_step() {
  float ax, ay, az;
  if (!read_accel(ax, ay, az)) return;
  const uint32_t now = micros();
  ring_ax[n_samples % motion::kN] = ax;
  ring_t[n_samples % motion::kN] = now;
  ++n_samples;
  ++since_last;
  if (n_samples < static_cast<uint32_t>(motion::kN) || since_last < kHop) return;
  since_last = 0;

  if (!snapshot_window()) {
    Serial.println("LIVE fenetre_invalide (lacune ou temps non croissant) : ignoree");
    return;
  }
  const Prediction r = classify(win_ax, win_t);
  if (!r.ok) {
    Serial.println("ERREUR invoke");
    return;
  }
  Serial.print("LIVE ");
  Serial.print(kLabels[r.label]);
  Serial.print(r.p[r.label] < kMinConfidence ? " (incertain)" : "");
  for (int c = 0; c < kNumClasses; ++c) {
    Serial.print(' ');
    Serial.print(kLabels[c]);
    Serial.print('=');
    Serial.print(r.p[c], 2);
  }
  Serial.print(" | rms=");
  Serial.print(r.f.rms_g, 4);
  Serial.print(" crest=");
  Serial.print(r.f.crest, 2);
  Serial.print(" dom=");
  Serial.print(r.f.dominant_hz, 2);
  Serial.print("Hz fs=");
  Serial.print(r.f.fs_hz, 1);
  Serial.print(" feat_us=");
  Serial.print(r.feat_us);
  Serial.print(" invoke_us=");
  Serial.println(r.invoke_us);
}

// ---------- démarrage et commandes ----------

static void print_header() {
  Serial.print("# firmware=");
  Serial.print(kFirmware);
  Serial.print(" board_revision=");
  Serial.print(kBoardRevision);
  Serial.print(" imu=");
  Serial.println(kImuName);
  Serial.print("# model_version=");
  Serial.println(kModelVersion);
  Serial.print("# model_sha256=");
  Serial.println(g_model_sha256);
  Serial.print("# model_bytes=");
  Serial.print(g_model_len);
  Serial.print(" arena_size=");
  Serial.print(kArenaSize);
  if (init_error == nullptr) {
    Serial.print(" arena_used=");
    Serial.println(static_cast<unsigned long>(interpreter->arena_used_bytes()));
  } else {
    Serial.println();
    Serial.print("ERREUR init=");
    Serial.println(init_error);
  }
  if (!imu_ok) {
    Serial.print("ERREUR imu_begin : ");
    Serial.println(kWrongBoard);
  }
  Serial.println("# commandes : R = replay des golden vectors, L = live marche/arret");
}

void setup() {
  Serial.begin(115200);
  const uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 3000) {
  }
  extractor.begin();
  imu_ok = IMU.begin();
  init_error = extractor.ready() ? init_model() : "kiss_fftr_alloc (fft_mem_ trop petit)";
  print_header();
  if (init_error == nullptr) replay();
}

void loop() {
  while (Serial.available() > 0) {
    const char c = Serial.read();
    if (c == 'R' || c == 'r') {
      live = false;
      print_header();
      if (init_error == nullptr) replay();
    } else if (c == 'L' || c == 'l') {
      if (init_error != nullptr || !imu_ok) {
        print_header();
      } else {
        live = !live;
        n_samples = since_last = 0;
        Serial.println(live ? "LIVE debut (premiere classification apres 256 mesures, ~2,2 s)" : "LIVE fin");
      }
    }
  }
  if (live) live_step();
}
