// TinyML2027 — Extension Edge Impulse : vérifier le microphone PDM de la Nano 33 BLE Sense.
//
// Bibliothèque : PDM, fournie avec le core officiel arduino:mbed_nano (aucune installation).
// Le micro (MP34DT05 sur l'originale, MP34DT06JTR sur la Rev2) n'existe que sur les
// versions **Sense**. Sur une Nano 33 BLE sans Sense, PDM.begin() échoue ou le signal reste nul.
//
// Toutes les 250 ms, une ligne : niveau RMS et crête des échantillons 16 bits reçus,
// et nombre d'échantillons reçus (pour vérifier la cadence de 16 000 par seconde).
#include <PDM.h>

constexpr int kSampleRate = 16000;  // Hz, cadence habituelle des modèles audio d'Edge Impulse
short buffer[512];
volatile int samples_read = 0;
double sum_sq = 0;
long peak = 0;
unsigned long n_total = 0;
unsigned long t_last = 0;

void on_pdm_data() {
  const int bytes = PDM.available();
  PDM.read(buffer, bytes);
  samples_read = bytes / 2;
}

void setup() {
  Serial.begin(115200);
  const unsigned long t0 = millis();
  while (!Serial && millis() - t0 < 3000) {
  }
  PDM.onReceive(on_pdm_data);
  if (!PDM.begin(1, kSampleRate)) {  // 1 canal (mono)
    Serial.println("ERREUR PDM.begin : pas de microphone ? (carte non Sense)");
    while (true) delay(1000);
  }
  Serial.println("# mic_check 0.1.0 : rms et crete en unites brutes 16 bits (0..32767)");
  Serial.println("t_ms,rms,crete,echantillons_par_s");
  t_last = millis();
}

void loop() {
  if (samples_read) {
    for (int i = 0; i < samples_read; ++i) {
      sum_sq += static_cast<double>(buffer[i]) * buffer[i];
      peak = max(peak, static_cast<long>(abs(buffer[i])));
    }
    n_total += samples_read;
    samples_read = 0;
  }
  const unsigned long now = millis();
  if (now - t_last >= 250 && n_total > 0) {
    Serial.print(now);
    Serial.print(',');
    Serial.print(sqrt(sum_sq / n_total), 1);
    Serial.print(',');
    Serial.print(peak);
    Serial.print(',');
    Serial.println(n_total * 1000.0 / (now - t_last), 0);
    sum_sq = 0;
    peak = 0;
    n_total = 0;
    t_last = now;
  }
}
