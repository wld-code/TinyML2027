// 01_blink — premier test de la chaîne de compilation et de téléversement.
// La LED orange (LED_BUILTIN) clignote à 1 Hz : 500 ms allumée, 500 ms éteinte.
// Chaque changement d'état est aussi écrit sur le port série USB (115200 bauds),
// ce qui permet de vérifier la communication sans regarder la carte.
unsigned long count = 0;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(115200);
}

void loop() {
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.print("blink "); Serial.print(++count); Serial.println(" LED=ON");
  delay(500);
  digitalWrite(LED_BUILTIN, LOW);
  Serial.print("blink "); Serial.print(count); Serial.println(" LED=OFF");
  delay(500);
}
