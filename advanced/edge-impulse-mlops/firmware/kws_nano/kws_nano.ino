#include <PDM.h>
#include <Wire.h>
#include "lab_build.h"

constexpr size_t kSamples = 16000;
constexpr uint8_t kGain = 127;
constexpr float kThreshold = 0.6f;
constexpr uint32_t kCaptureTimeoutMs = 1600;
constexpr uint32_t kReplayTimeoutMs = 1600;
constexpr size_t kReplayChunk = 128; // capacité RX du core USB : 256 octets

static_assert(EI_CLASSIFIER_SENSOR == EI_CLASSIFIER_SENSOR_MICROPHONE, "Export audio requis");
static_assert(EI_CLASSIFIER_FREQUENCY == 16000 && EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE == kSamples,
              "Fenêtre PCM mono de 16 000 valeurs requise");
static_assert(EI_CLASSIFIER_LABEL_COUNT == 3 && EI_CLASSIFIER_QUANTIZATION_ENABLED,
              "Classifieur INT8 à trois classes requis");

int16_t window_pcm[kSamples];
int16_t pdm_block[256];
volatile size_t received = 0;
volatile bool capturing = false;
volatile uint32_t pdm_errors = 0;
volatile uint32_t pdm_samples = 0;
volatile uint32_t window_end_us = 0;
bool original_board = false;
bool mic_ok = false;
bool model_ok = false;
uint32_t seq = 0;
const char* labels[] = {"bruit", "go", "stop"};

bool is_original() {
  Wire1.beginTransmission(0x6B);
  Wire1.write(0x0F);
  return Wire1.endTransmission(false) == 0 &&
         Wire1.requestFrom(uint8_t(0x6B), uint8_t(1)) == 1 && Wire1.read() == 0x68;
}

void on_pdm_data() {
  while (PDM.available() > 0) {
    const int bytes = PDM.read(pdm_block, sizeof(pdm_block));
    if (bytes <= 0) {
      ++pdm_errors;
      return;
    }
    if (bytes % sizeof(int16_t) != 0) ++pdm_errors;
    const size_t count = bytes / sizeof(int16_t);
    pdm_samples += count;
    if (!capturing) continue;
    const size_t remaining = kSamples - received;
    const size_t copy_count = count < remaining ? count : remaining;
    memcpy(window_pcm + received, pdm_block, copy_count * sizeof(int16_t));
    received += copy_count;
    if (received == kSamples) {
      window_end_us = micros();
      capturing = false;
    }
  }
}

int get_audio(size_t offset, size_t length, float* out) {
  if (offset > kSamples || length > kSamples - offset) return -1;
  return numpy::int16_to_float(window_pcm + offset, out, length);
}

bool classify(ei_impulse_result_t& result, float (&scores)[3]) {
  signal_t signal;
  signal.total_length = kSamples;
  signal.get_data = &get_audio;
  if (run_classifier(&signal, &result, false) != EI_IMPULSE_OK) return false;
  bool found[3] = {};
  for (size_t i = 0; i < 3; ++i) {
    for (size_t j = 0; j < 3; ++j) {
      if (strcmp(result.classification[i].label, labels[j]) == 0) {
        scores[j] = result.classification[i].value;
        found[j] = isfinite(scores[j]);
      }
    }
  }
  return found[0] && found[1] && found[2];
}

void hello() {
  Serial.print("{\"event\":\"hello\",\"protocol\":2,\"firmware\":\"kws_nano 0.1.1\",\"release\":\"");
  Serial.print(KWS_RELEASE);
  Serial.print("\",\"export_sha256\":\"");
  Serial.print(KWS_EXPORT_SHA256);
  Serial.print("\",\"board\":\"");
  Serial.print(original_board ? "ABX00031" : "unknown");
  Serial.print("\",\"sample_rate_hz\":16000,\"samples\":16000,\"threshold\":0.6,\"mic_ok\":");
  Serial.print(mic_ok ? "true" : "false");
  Serial.print(",\"model_ok\":");
  Serial.print(model_ok ? "true" : "false");
  Serial.println("}");
}

void report_error(const char* code) {
  Serial.print("{\"event\":\"error\",\"seq\":");
  Serial.print(seq);
  Serial.print(",\"code\":\"");
  Serial.print(code);
  Serial.print("\",\"pdm_errors\":");
  Serial.print(pdm_errors);
  Serial.println("}");
}

uint32_t pcm_crc32() {
  uint32_t crc = 0xffffffffu;
  const uint8_t* bytes = reinterpret_cast<const uint8_t*>(window_pcm);
  for (size_t i = 0; i < sizeof(window_pcm); ++i) {
    crc ^= bytes[i];
    for (int bit = 0; bit < 8; ++bit) crc = (crc >> 1) ^ ((crc & 1) ? 0xedb88320u : 0);
  }
  return ~crc;
}

void report_prediction(const char* mode, uint32_t capture_us) {
  const uint32_t noise_errors_before = pdm_errors;
  const uint32_t samples_before = pdm_samples;
  const uint32_t start = micros();
  ei_impulse_result_t result = {};
  float scores[3] = {};
  if (!classify(result, scores)) {
    report_error("inference_failed");
    return;
  }
  const uint32_t inference_us = micros() - start;
  const uint32_t samples_during = pdm_samples - samples_before;
  if (pdm_errors != noise_errors_before) {
    report_error("pdm_read");
    return;
  }
  size_t best = 0;
  double square_sum = 0;
  for (size_t i = 0; i < 3; ++i) if (scores[i] > scores[best]) best = i;
  for (const int16_t sample : window_pcm) square_sum += double(sample) * sample;
  Serial.print("{\"event\":\"prediction\",\"seq\":");
  Serial.print(seq);
  Serial.print(",\"mode\":\"");
  Serial.print(mode);
  Serial.print("\",\"capture_us\":");
  Serial.print(capture_us);
  Serial.print(",\"inference_us\":");
  Serial.print(inference_us);
  Serial.print(",\"dsp_ms\":");
  Serial.print(result.timing.dsp);
  Serial.print(",\"classification_ms\":");
  Serial.print(result.timing.classification);
  Serial.print(",\"discarded_during_inference\":");
  Serial.print(samples_during);
  Serial.print(",\"pdm_errors\":");
  Serial.print(pdm_errors);
  Serial.print(",\"pcm_crc32\":");
  Serial.print(pcm_crc32());
  Serial.print(",\"rms_pcm\":");
  Serial.print(sqrt(square_sum / kSamples), 2);
  Serial.print(",\"scores\":{");
  for (size_t i = 0; i < 3; ++i) {
    if (i != 0) Serial.print(',');
    Serial.print('"');
    Serial.print(labels[i]);
    Serial.print("\":");
    Serial.print(scores[i], 6);
  }
  Serial.print("},\"prediction\":\"");
  Serial.print(scores[best] < kThreshold ? "uncertain" : labels[best]);
  Serial.println("\"}");
}

void capture() {
  if (!mic_ok) {
    report_error("pdm_unavailable");
    return;
  }
  const uint32_t errors_before = pdm_errors;
  noInterrupts();
  received = 0;
  const uint32_t started_us = micros();
  capturing = true;
  interrupts();
  Serial.print("{\"event\":\"capture_started\",\"seq\":");
  Serial.print(seq);
  Serial.println("}");
  const uint32_t started_ms = millis();
  while (capturing && millis() - started_ms < kCaptureTimeoutMs) delay(1);
  noInterrupts();
  capturing = false;
  const bool full = received == kSamples;
  interrupts();
  if (!full || pdm_errors != errors_before) {
    report_error(full ? "pdm_read" : "capture_timeout");
    return;
  }
  report_prediction("microphone", window_end_us - started_us);
}

void replay() {
  Serial.print("{\"event\":\"replay_ready\",\"seq\":");
  Serial.print(seq);
  Serial.print(",\"bytes\":32000,\"chunk_bytes\":");
  Serial.print(kReplayChunk);
  Serial.println("}");
  uint8_t* bytes = reinterpret_cast<uint8_t*>(window_pcm);
  size_t count = 0;
  while (count < sizeof(window_pcm)) {
    const size_t end = count + kReplayChunk;
    const uint32_t start = millis();
    while (count < end && millis() - start < kReplayTimeoutMs) {
      const int byte = Serial.read();
      if (byte >= 0) bytes[count++] = byte;
      else delay(1);
    }
    if (count != end) {
      report_error("replay_timeout");
      return;
    }
    if (count < sizeof(window_pcm)) {
      Serial.print("{\"event\":\"replay_chunk\",\"seq\":");
      Serial.print(seq);
      Serial.print(",\"received\":");
      Serial.print(count);
      Serial.println("}");
    }
  }
  report_prediction("replay", 0);
}

void setup() {
  Serial.begin(115200);
  Wire1.begin();
  delay(50);
  original_board = is_original();
  if (original_board) {
    PDM.onReceive(on_pdm_data);
    PDM.setBufferSize(sizeof(pdm_block));
    mic_ok = PDM.begin(1, EI_CLASSIFIER_FREQUENCY);
    if (mic_ok) PDM.setGain(kGain);
    ei_impulse_result_t result = {};
    float scores[3] = {};
    model_ok = classify(result, scores); // fenêtre PCM initialisée à zéro
  }
}

void loop() {
  const int command = Serial.read();
  if (command == 'I') {
    hello();
  } else if (command == 'C' || command == 'R') {
    ++seq;
    if (!model_ok) report_error("model_unavailable");
    else if (command == 'C') capture();
    else replay();
  }
  delay(1);
}
