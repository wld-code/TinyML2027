// TinyML2027 — TP01 : firmware d'acquisition de l'accéléromètre.
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

// Protocole texte, une commande par ligne (terminée par \n), à 115200 bauds :
//
//   PC -> carte : INFO                  carte -> PC : INFO firmware=... board_revision=... imu=... odr_nominal_hz=...
//   PC -> carte : START <recording_id>  carte -> PC : BEGIN recording_id=... (mêmes champs que INFO)
//                                                     seq,t_us,ax_g,ay_g,az_g
//                                                     0,0,0.01234,-0.00567,0.95812
//                                                     1,8432,...            (un échantillon par ligne)
//   PC -> carte : STOP                  carte -> PC : END recording_id=... n=<nombre d'échantillons>
//
// - seq : compteur d'échantillons, remis à 0 à chaque START, sans trou ni doublon côté carte ;
// - t_us : instant de LECTURE de l'échantillon sur la carte (micros()), relatif au
//   premier échantillon ; ce n'est pas l'heure de réception sur le PC ;
// - ax_g..az_g : accélération en g, 5 décimales.
// Une perte d'échantillon (carte bloquée parce que le PC ne lit plus assez vite) se voit
// dans t_us (intervalle anormal), pas dans seq : c'est au PC de la détecter (QC du TP01).
// Toute erreur est signalée par une ligne commençant par ERREUR.

constexpr char kFirmware[] = "imu_capture 0.1.0";
constexpr int kMaxIdLen = 40;

bool imu_ok = false;
bool recording = false;
char recording_id[kMaxIdLen + 1] = "";
uint32_t seq = 0;
uint32_t t0_us = 0;
char cmd[64];
int cmd_len = 0;

static void print_info_fields() {
  Serial.print(" firmware=");
  Serial.print(kFirmware);
  Serial.print(" board_revision=");
  Serial.print(kBoardRevision);
  Serial.print(" imu=");
  Serial.print(kImuName);
  Serial.print(" odr_nominal_hz=");
  Serial.println(imu_ok ? IMU.accelerationSampleRate() : NAN);
}

static bool valid_id(const char* s) {
  const int n = strlen(s);
  if (n == 0 || n > kMaxIdLen) return false;
  for (int i = 0; i < n; ++i) {
    const char c = s[i];
    if (!(isalnum(c) || c == '_' || c == '-')) return false;
  }
  return true;
}

static void stop_recording() {
  Serial.print("END recording_id=");
  Serial.print(recording_id);
  Serial.print(" n=");
  Serial.println(seq);
  recording = false;
}

static void handle_command(char* line) {
  if (strcmp(line, "INFO") == 0) {
    Serial.print("INFO");
    print_info_fields();
    if (!imu_ok) {
      Serial.print("ERREUR imu_begin : ");
      Serial.println(kWrongBoard);
    }
  } else if (strncmp(line, "START ", 6) == 0) {
    if (!imu_ok) {
      Serial.print("ERREUR imu_begin : ");
      Serial.println(kWrongBoard);
    } else if (recording) {
      Serial.println("ERREUR deja_en_cours");
    } else if (!valid_id(line + 6)) {
      Serial.println("ERREUR recording_id_invalide (1 a 40 caracteres A-Z a-z 0-9 _ -)");
    } else {
      strcpy(recording_id, line + 6);
      seq = 0;
      recording = true;
      Serial.print("BEGIN recording_id=");
      Serial.print(recording_id);
      print_info_fields();
      Serial.println("seq,t_us,ax_g,ay_g,az_g");
      float ax, ay, az;
      read_accel(ax, ay, az);  // vide un éventuel échantillon ancien
    }
  } else if (strcmp(line, "STOP") == 0) {
    if (recording) {
      stop_recording();
    } else {
      Serial.println("ERREUR pas_d_enregistrement");
    }
  } else if (line[0] != '\0') {
    Serial.print("ERREUR commande_inconnue ");
    Serial.println(line);
  }
}

static void poll_serial() {
  while (Serial.available() > 0) {
    const char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      cmd[cmd_len] = '\0';
      handle_command(cmd);
      cmd_len = 0;
    } else if (cmd_len < static_cast<int>(sizeof cmd) - 1) {
      cmd[cmd_len++] = c;
    }
  }
}

void setup() {
  Serial.begin(115200);
  imu_ok = IMU.begin();
}

void loop() {
  poll_serial();
  if (!recording) return;

  float ax, ay, az;
  if (!read_accel(ax, ay, az)) return;
  const uint32_t now = micros();
  if (seq == 0) t0_us = now;

  Serial.print(seq);
  Serial.print(',');
  Serial.print(now - t0_us);
  Serial.print(',');
  Serial.print(ax, 5);
  Serial.print(',');
  Serial.print(ay, 5);
  Serial.print(',');
  Serial.println(az, 5);
  ++seq;
}
