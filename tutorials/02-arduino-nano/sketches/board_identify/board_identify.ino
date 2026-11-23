// board_identify — identifie la révision d'une Arduino Nano 33 BLE Sense
// par lecture des registres d'identité des capteurs internes (bus I2C interne Wire1).
//
// Lecture seule : aucun registre n'est écrit dans les capteurs.
// Sortie série 115200 bauds, lignes "clé=valeur" faciles à lire et à analyser.
// Le rapport est envoyé au démarrage puis à chaque caractère reçu (ex. touche Entrée
// dans le moniteur série), car l'ordinateur peut ouvrir le port après le démarrage.
//
// Adresses et identifiants attendus (fiches techniques) :
//   LSM9DS1  acc/gyro 0x6B, WHO_AM_I (0x0F) = 0x68  -> Sense originale
//   LSM9DS1  magnéto  0x1E, WHO_AM_I_M (0x0F) = 0x3D -> Sense originale
//   BMI270            0x68, CHIP_ID (0x00)   = 0x24 -> Sense Rev2
//   BMM150            0x10, CHIP_ID (0x40)   = 0x32 -> Sense Rev2 (lisible seulement après mise sous tension, peut répondre 0x00)
//   HTS221 0x5F (originale), HS3003 0x44 (Rev2), LPS22HB 0x5C, APDS9960 0x39 (les deux)

#include <Wire.h>

static bool probe(uint8_t addr) {
  Wire1.beginTransmission(addr);
  return Wire1.endTransmission() == 0;
}

static int readReg(uint8_t addr, uint8_t reg) {
  Wire1.beginTransmission(addr);
  Wire1.write(reg);
  if (Wire1.endTransmission(false) != 0) return -1;
  if (Wire1.requestFrom(addr, (uint8_t)1) != 1) return -1;
  return Wire1.read();
}

static void printHex(int v) {
  if (v < 0) { Serial.print("none"); return; }
  Serial.print("0x");
  if (v < 16) Serial.print('0');
  Serial.print(v, HEX);
}

void report();

void setup() {
  Serial.begin(115200);
  unsigned long t0 = millis();
  while (!Serial && millis() - t0 < 5000) { }  // n'attend pas indéfiniment

  Wire1.begin();
  delay(50);
  report();
}

void loop() {
  if (Serial.available() > 0) {
    while (Serial.available() > 0) Serial.read();
    report();
  }
}

void report() {
  Serial.println("BEGIN board_identify v1");
  Serial.print("i2c_devices=");
  bool first = true;
  for (uint8_t a = 1; a < 127; a++) {
    if (probe(a)) {
      if (!first) Serial.print(',');
      printHex(a);
      first = false;
    }
  }
  Serial.println();

  int lsm_ag = readReg(0x6B, 0x0F);
  int lsm_m  = readReg(0x1E, 0x0F);
  int bmi    = readReg(0x68, 0x00);
  int bmm    = readReg(0x10, 0x40);
  Serial.print("lsm9ds1_whoami=");  printHex(lsm_ag); Serial.println();
  Serial.print("lsm9ds1m_whoami="); printHex(lsm_m);  Serial.println();
  Serial.print("bmi270_chipid=");   printHex(bmi);    Serial.println();
  Serial.print("bmm150_chipid=");   printHex(bmm);    Serial.println();

  const char* verdict = "unknown";
  if (lsm_ag == 0x68 && bmi != 0x24) verdict = "nano33ble_sense_original";
  else if (bmi == 0x24 && lsm_ag != 0x68) verdict = "nano33ble_sense_rev2";
  else if (lsm_ag < 0 && bmi < 0) verdict = "no_known_imu";
  Serial.print("verdict="); Serial.println(verdict);
  Serial.println("END");
}
