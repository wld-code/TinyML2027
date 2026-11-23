// Diagnostic Lot 0 : cadence réelle de l'accéléromètre (Sense originale, LSM9DS1).
#include <Arduino_LSM9DS1.h>
uint32_t seq = 0;
void setup() {
  Serial.begin(115200);
  while (!Serial) { }
  if (!IMU.begin()) { Serial.println("ERROR imu_begin"); while (true) { } }
  Serial.print("# accel_odr_hz="); Serial.println(IMU.accelerationSampleRate());
  Serial.print("# gyro_odr_hz=");  Serial.println(IMU.gyroscopeSampleRate());
  Serial.println("seq,t_us,ax_g,ay_g,az_g");
}
void loop() {
  if (IMU.accelerationAvailable()) {
    float ax, ay, az;
    uint32_t t = micros();
    IMU.readAcceleration(ax, ay, az);
    Serial.print(seq++); Serial.print(','); Serial.print(t); Serial.print(',');
    Serial.print(ax, 5); Serial.print(','); Serial.print(ay, 5); Serial.print(','); Serial.println(az, 5);
  }
}
