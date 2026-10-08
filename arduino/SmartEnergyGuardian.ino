/*
 * Smart Energy Guardian — Arduino Uno
 * Control de carga (4 LED + 2 relés) y sensor PIR HC-SR501.
 * Comandos serial: ON, OFF, STATUS (9600 baud, línea terminada en \n).
 */

// Cambiar a false si el módulo de relés se activa con HIGH.
const bool RELAY_ACTIVE_LOW = true;

const int PIN_PIR = 2;
const int PIN_LED_ROJO = 3;
const int PIN_LED_AMARILLO = 4;
const int PIN_LED_VERDE = 5;
const int PIN_LED_AZUL = 6;
const int PIN_RELE_1 = 7;
const int PIN_RELE_2 = 8;

const int LED_PINS[] = {PIN_LED_ROJO, PIN_LED_AMARILLO, PIN_LED_VERDE, PIN_LED_AZUL};
const int RELAY_PINS[] = {PIN_RELE_1, PIN_RELE_2};
const size_t NUM_LEDS = 4;
const size_t NUM_RELAYS = 2;

const unsigned long TIEMPO_SIN_MOVIMIENTO_MS = 10000UL;

bool cargaActiva = false;
bool activadaPorPir = false;  // Solo la carga encendida por PIR se apaga tras el tiempo de inactividad.
bool ultimoEstadoPir = false;
unsigned long ultimoMovimientoMs = 0;

String bufferSerial = "";

void escribirRele(int pin, bool encendido) {
  if (RELAY_ACTIVE_LOW) {
    digitalWrite(pin, encendido ? LOW : HIGH);
  } else {
    digitalWrite(pin, encendido ? HIGH : LOW);
  }
}

void encenderCarga() {
  for (size_t i = 0; i < NUM_LEDS; i++) {
    digitalWrite(LED_PINS[i], HIGH);
  }
  for (size_t i = 0; i < NUM_RELAYS; i++) {
    escribirRele(RELAY_PINS[i], true);
  }
  if (!cargaActiva) {
    cargaActiva = true;
    Serial.println(F("CARGA:ACTIVA"));
  }
}

void apagarCarga() {
  for (size_t i = 0; i < NUM_LEDS; i++) {
    digitalWrite(LED_PINS[i], LOW);
  }
  for (size_t i = 0; i < NUM_RELAYS; i++) {
    escribirRele(RELAY_PINS[i], false);
  }
  if (cargaActiva) {
    cargaActiva = false;
    Serial.println(F("CARGA:APAGADA"));
  }
  activadaPorPir = false;
}

void enviarEstadoPir(bool presencia) {
  if (presencia) {
    Serial.println(F("PIR:PRESENCIA"));
  } else {
    Serial.println(F("PIR:AUSENCIA"));
  }
}

void enviarEstadoActual() {
  enviarEstadoPir(ultimoEstadoPir);
  if (cargaActiva) {
    Serial.println(F("CARGA:ACTIVA"));
  } else {
    Serial.println(F("CARGA:APAGADA"));
  }
}

void procesarComando(const String &comando) {
  if (comando == "ON") {
    activadaPorPir = false;
    encenderCarga();
    return;
  }
  if (comando == "OFF") {
    apagarCarga();
    return;
  }
  if (comando == "STATUS") {
    enviarEstadoActual();
    return;
  }
}

void leerComandosSerial() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (bufferSerial.length() > 0) {
        bufferSerial.trim();
        procesarComando(bufferSerial);
        bufferSerial = "";
      }
    } else {
      bufferSerial += c;
    }
  }
}

void actualizarPir() {
  bool presencia = digitalRead(PIN_PIR) == HIGH;

  if (presencia != ultimoEstadoPir) {
    ultimoEstadoPir = presencia;
    enviarEstadoPir(presencia);
  }

  unsigned long ahora = millis();

  if (presencia) {
    ultimoMovimientoMs = ahora;
    activadaPorPir = true;
    encenderCarga();
    return;
  }

  if (cargaActiva && activadaPorPir &&
      (ahora - ultimoMovimientoMs >= TIEMPO_SIN_MOVIMIENTO_MS)) {
    apagarCarga();
  }
}

void setup() {
  pinMode(PIN_PIR, INPUT);

  for (size_t i = 0; i < NUM_LEDS; i++) {
    pinMode(LED_PINS[i], OUTPUT);
    digitalWrite(LED_PINS[i], LOW);
  }
  for (size_t i = 0; i < NUM_RELAYS; i++) {
    pinMode(RELAY_PINS[i], OUTPUT);
    escribirRele(RELAY_PINS[i], false);
  }

  cargaActiva = false;
  activadaPorPir = false;
  ultimoEstadoPir = (digitalRead(PIN_PIR) == HIGH);
  ultimoMovimientoMs = millis();

  Serial.begin(9600);
  Serial.println(F("READY"));
}

void loop() {
  leerComandosSerial();
  actualizarPir();
}
