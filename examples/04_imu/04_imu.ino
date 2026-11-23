// TinyML2027 — Phase 6 : lire l'IMU (accéléromètre + gyroscope) avec unités et cadence mesurée.
//
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

static bool read_gyro(float& x, float& y, float& z) {
  return IMU.gyroscopeAvailable() && IMU.readGyroscope(x, y, z) == 1;
}

// Une ligne CSV toutes les 100 ms :
//   t_ms, ax_g, ay_g, az_g, gx_dps, gy_dps, gz_dps, fs_acc_hz, fs_gyr_hz, gravite
// - ax..az : dernier échantillon d'accélération, en g ;
// - gx..gz : dernier échantillon de vitesse angulaire, en °/s ;
// - fs_acc_hz / fs_gyr_hz : cadence MESURÉE sur la dernière seconde écoulée
//   (nombre de nouveaux échantillons / durée), à comparer à la cadence nominale ;
// - gravite : l'axe qui porte l'essentiel de la gravité (+X, -X, ..., ou "?" si
//   aucun axe ne dépasse 0,8 g, c'est-à-dire carte en mouvement ou inclinée).

constexpr char kFirmware[] = "04_imu 0.1.0";
constexpr uint32_t kPrintPeriodMs = 100;
constexpr uint32_t kRateWindowUs = 1000000;

float ax, ay, az, gx, gy, gz;
uint32_t n_acc = 0, n_gyr = 0;           // échantillons dans la fenêtre de mesure courante
uint32_t window_start_us = 0;
float fs_acc = NAN, fs_gyr = NAN;         // NAN tant qu'une seconde complète n'est pas écoulée
uint32_t last_print_ms = 0;
bool imu_ok = false;

static const char* gravity_axis() {
  const float v[3] = {ax, ay, az};
  const char* names[3] = {"X", "Y", "Z"};
  for (int i = 0; i < 3; ++i) {
    if (v[i] > 0.8f) { static char s[3]; s[0] = '+'; s[1] = names[i][0]; s[2] = 0; return s; }
    if (v[i] < -0.8f) { static char s[3]; s[0] = '-'; s[1] = names[i][0]; s[2] = 0; return s; }
  }
  return "?";
}

static void print_header() {
  Serial.print("# firmware=");
  Serial.print(kFirmware);
  Serial.print(" board_revision=");
  Serial.print(kBoardRevision);
  Serial.print(" imu=");
  Serial.println(kImuName);
  if (!imu_ok) {
    Serial.print("ERREUR imu_begin : ");
    Serial.println(kWrongBoard);
    return;
  }
  Serial.print("# accel_odr_nominal_hz=");
  Serial.print(IMU.accelerationSampleRate());
  Serial.print(" gyro_odr_nominal_hz=");
  Serial.println(IMU.gyroscopeSampleRate());
  Serial.println("t_ms,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,fs_acc_hz,fs_gyr_hz,gravite");
}

void setup() {
  Serial.begin(115200);
  const uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 3000) {
  }
  imu_ok = IMU.begin();
  print_header();
  window_start_us = micros();
}

void loop() {
  if (Serial.available() > 0) {  // Entrée dans le moniteur : réaffiche l'en-tête
    while (Serial.available() > 0) Serial.read();
    print_header();
  }
  if (!imu_ok) {
    delay(2000);
    Serial.print("ERREUR imu_begin : ");
    Serial.println(kWrongBoard);
    return;
  }

  if (read_accel(ax, ay, az)) ++n_acc;
  if (read_gyro(gx, gy, gz)) ++n_gyr;

  const uint32_t now_us = micros();
  if (now_us - window_start_us >= kRateWindowUs) {
    const float dt = (now_us - window_start_us) * 1e-6f;
    fs_acc = n_acc / dt;
    fs_gyr = n_gyr / dt;
    n_acc = n_gyr = 0;
    window_start_us = now_us;
  }

  const uint32_t now_ms = millis();
  if (now_ms - last_print_ms >= kPrintPeriodMs) {
    last_print_ms = now_ms;
    Serial.print(now_ms);     Serial.print(',');
    Serial.print(ax, 4);      Serial.print(',');
    Serial.print(ay, 4);      Serial.print(',');
    Serial.print(az, 4);      Serial.print(',');
    Serial.print(gx, 2);      Serial.print(',');
    Serial.print(gy, 2);      Serial.print(',');
    Serial.print(gz, 2);      Serial.print(',');
    Serial.print(fs_acc, 1);  Serial.print(',');
    Serial.print(fs_gyr, 1);  Serial.print(',');
    Serial.println(gravity_axis());
  }
}
