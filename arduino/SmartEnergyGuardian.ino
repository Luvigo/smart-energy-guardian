/*
 * SMART ENERGY HOME — Arduino Uno
 * Protocolo serial 9600 baud, líneas terminadas en \n (ver dashboard Python).
 *
 * Servos (D5 puerta, D6 ventana):
 *   - SERVOS_ENABLED debe permanecer en false hasta confirmar alimentación externa
 *     de 5 V adecuada para los servos y GND común con el Arduino.
 *   - NO alimentar los servos desde el USB del Arduino.
 *   - Conexión futura: señal → D5 / D6; +5 V externo → servo V+; GND externo → GND Arduino.
 */

#include <Wire.h>
#include <Servo.h>
#include <LiquidCrystal_I2C.h>

#define ENABLE_INA219 false

#if ENABLE_INA219
#include <Adafruit_INA219.h>
#endif

// ---------------------------------------------------------------------------
// Configuración de hardware (cambiar solo cuando el cableado esté listo)
// ---------------------------------------------------------------------------

// Cambiar a true SOLO tras alimentación externa 5 V + GND común verificados.
const bool SERVOS_ENABLED = false;

// Dirección I2C típica del LCD 16x2 (0x27 o 0x3F según módulo).
const uint8_t LCD_I2C_ADDR = 0x27;

// ---------------------------------------------------------------------------
// Pines
// ---------------------------------------------------------------------------
const int PIN_LED_ENTRY = 2;
const int PIN_LED_LIVING = 3;
const int PIN_LED_BEDROOM = 4;
const int PIN_SERVO_DOOR = 5;
const int PIN_SERVO_WINDOW = 6;
const int PIN_BUZZER = 7;
const int PIN_ULTRASONIC_TRIG = 9;
const int PIN_ULTRASONIC_ECHO = 10;

const int SERVO_ANGLE_OPEN = 90;
const int SERVO_ANGLE_CLOSED = 0;

const float PROXIMITY_THRESHOLD_CM = 30.0f;
const unsigned long DISTANCE_PUBLISH_MS = 500UL;
const unsigned long ENERGY_PUBLISH_MS = 1000UL;
const unsigned long LCD_ALT_TOGGLE_MS = 3000UL;
const unsigned long ALARM_BEEP_INTERVAL_MS = 500UL;
const unsigned long SHORT_BEEP_MS = 80UL;
const unsigned long US_ECHO_TIMEOUT_US = 30000UL;

LiquidCrystal_I2C lcd(LCD_I2C_ADDR, 16, 2);
Servo servoDoor;
Servo servoWindow;

#if ENABLE_INA219
Adafruit_INA219 ina219;
bool ina219Ready = false;
#endif

bool lightEntry = false;
bool lightLiving = false;
bool lightBedroom = false;
bool proximityNear = false;
bool alarmActive = false;
bool doorOpen = false;
bool windowOpen = false;

bool servosAttached = false;

float lastDistanceCm = -1.0f;
bool hasValidDistance = false;

String serialBuffer;

// Ultrasónico sin delay() bloqueante
enum UltrasonicState { US_IDLE, US_WAIT_RISE, US_WAIT_FALL };
UltrasonicState usState = US_IDLE;
unsigned long usLastCycleMs = 0;
unsigned long usTriggerUs = 0;
unsigned long usEchoRiseUs = 0;

unsigned long lastEnergyPublishMs = 0;
unsigned long lcdAltToggleMs = 0;
bool lcdEnergyScreenActive = false;

bool shortBeepActive = false;
unsigned long shortBeepEndMs = 0;

unsigned long alarmToggleMs = 0;
bool alarmToneHigh = false;

// ---------------------------------------------------------------------------
// LCD
// ---------------------------------------------------------------------------
void lcdShowBoot() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(F("SMART ENERGY"));
  lcd.setCursor(0, 1);
  lcd.print(F("Iniciando..."));
}

void lcdShowMain() {
  lcd.clear();
  if (proximityNear) {
    lcd.setCursor(0, 0);
    lcd.print(F("Objeto cercano"));
  } else {
    lcd.setCursor(0, 0);
    lcd.print(F("Area libre"));
  }
  lcd.setCursor(0, 1);
  if (hasValidDistance) {
    lcd.print(lastDistanceCm, 1);
    lcd.print(F(" cm"));
  } else {
    lcd.print(F("-- cm"));
  }
}

#if ENABLE_INA219
void lcdDisplayEnergy(float volts, float amps, float watts) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(F("Energia INA219"));
  lcd.setCursor(0, 1);
  lcd.print(volts, 1);
  lcd.print(F("V "));
  lcd.print(watts, 1);
  lcd.print(F("W"));
}
#endif

void refreshLcdIfNeeded() {
#if ENABLE_INA219
  if (ina219Ready && lcdEnergyScreenActive) {
    return;  // Pantalla de energía se actualiza al publicar ENERGY
  }
#endif
  lcdShowMain();
}

void updateLcdAlternate() {
#if ENABLE_INA219
  if (!ina219Ready) {
    lcdEnergyScreenActive = false;
    return;
  }
  unsigned long now = millis();
  if (now - lcdAltToggleMs >= LCD_ALT_TOGGLE_MS) {
    lcdAltToggleMs = now;
    lcdEnergyScreenActive = !lcdEnergyScreenActive;
    if (!lcdEnergyScreenActive) {
      lcdShowMain();
    }
  }
#else
  lcdEnergyScreenActive = false;
#endif
}

// ---------------------------------------------------------------------------
// LEDs y buzzer
// ---------------------------------------------------------------------------
void setLightEntry(bool on) {
  if (lightEntry == on) {
    return;
  }
  lightEntry = on;
  digitalWrite(PIN_LED_ENTRY, on ? HIGH : LOW);
  Serial.println(on ? F("LIGHT:ENTRY:ON") : F("LIGHT:ENTRY:OFF"));
}

void setLightLiving(bool on) {
  if (lightLiving == on) {
    return;
  }
  lightLiving = on;
  digitalWrite(PIN_LED_LIVING, on ? HIGH : LOW);
  Serial.println(on ? F("LIGHT:LIVING:ON") : F("LIGHT:LIVING:OFF"));
}

void setLightBedroom(bool on) {
  if (lightBedroom == on) {
    return;
  }
  lightBedroom = on;
  digitalWrite(PIN_LED_BEDROOM, on ? HIGH : LOW);
  Serial.println(on ? F("LIGHT:BEDROOM:ON") : F("LIGHT:BEDROOM:OFF"));
}

void startShortBeep() {
  if (alarmActive) {
    return;
  }
  tone(PIN_BUZZER, 2200);
  shortBeepActive = true;
  shortBeepEndMs = millis() + SHORT_BEEP_MS;
}

void setAlarm(bool on) {
  if (alarmActive == on) {
    return;
  }
  alarmActive = on;
  if (alarmActive) {
    alarmToggleMs = millis();
    alarmToneHigh = false;
    Serial.println(F("BUZZER:ON"));
  } else {
    noTone(PIN_BUZZER);
    shortBeepActive = false;
    Serial.println(F("BUZZER:OFF"));
  }
}

void updateBuzzer() {
  if (alarmActive) {
    unsigned long now = millis();
    if (now - alarmToggleMs >= ALARM_BEEP_INTERVAL_MS) {
      alarmToggleMs = now;
      alarmToneHigh = !alarmToneHigh;
      if (alarmToneHigh) {
        tone(PIN_BUZZER, 1500);
      } else {
        noTone(PIN_BUZZER);
      }
    }
    return;
  }
  if (shortBeepActive && millis() >= shortBeepEndMs) {
    noTone(PIN_BUZZER);
    shortBeepActive = false;
  }
}

// ---------------------------------------------------------------------------
// Servos (solo si SERVOS_ENABLED)
// ---------------------------------------------------------------------------
void attachServosIfEnabled() {
  if (!SERVOS_ENABLED || servosAttached) {
    return;
  }
  servoDoor.attach(PIN_SERVO_DOOR);
  servoWindow.attach(PIN_SERVO_WINDOW);
  servoDoor.write(SERVO_ANGLE_CLOSED);
  servoWindow.write(SERVO_ANGLE_CLOSED);
  doorOpen = false;
  windowOpen = false;
  servosAttached = true;
}

void reportServoPowerRequired() {
  Serial.println(F("SERVO:POWER_REQUIRED"));
  Serial.println(F("Servos deshabilitados: use 5V externo y GND comun; luego SERVOS_ENABLED=true"));
}

void setDoorOpen(bool open) {
  if (!SERVOS_ENABLED) {
    reportServoPowerRequired();
    return;
  }
  attachServosIfEnabled();
  if (doorOpen == open) {
    return;
  }
  doorOpen = open;
  servoDoor.write(open ? SERVO_ANGLE_OPEN : SERVO_ANGLE_CLOSED);
  Serial.println(open ? F("DOOR:OPEN") : F("DOOR:CLOSED"));
}

void setWindowOpen(bool open) {
  if (!SERVOS_ENABLED) {
    reportServoPowerRequired();
    return;
  }
  attachServosIfEnabled();
  if (windowOpen == open) {
    return;
  }
  windowOpen = open;
  servoWindow.write(open ? SERVO_ANGLE_OPEN : SERVO_ANGLE_CLOSED);
  Serial.println(open ? F("WINDOW:OPEN") : F("WINDOW:CLOSED"));
}

// ---------------------------------------------------------------------------
// Proximidad y distancia
// ---------------------------------------------------------------------------
void publishDistance(float cm) {
  Serial.print(F("DISTANCE:"));
  Serial.println(cm, 1);
}

void onProximityChanged(bool near) {
  proximityNear = near;
  if (near) {
    Serial.println(F("PROXIMITY:NEAR"));
    setLightEntry(true);
    startShortBeep();
  } else {
    Serial.println(F("PROXIMITY:FAR"));
    setLightEntry(false);
  }
  lcdShowMain();
}

void evaluateProximity(float cm) {
  bool near = (cm < PROXIMITY_THRESHOLD_CM);
  if (near != proximityNear) {
    onProximityChanged(near);
  }
}

void updateUltrasonic() {
  unsigned long nowMs = millis();

  switch (usState) {
    case US_IDLE:
      if (nowMs - usLastCycleMs < DISTANCE_PUBLISH_MS) {
        return;
      }
      digitalWrite(PIN_ULTRASONIC_TRIG, LOW);
      delayMicroseconds(2);
      digitalWrite(PIN_ULTRASONIC_TRIG, HIGH);
      delayMicroseconds(10);
      digitalWrite(PIN_ULTRASONIC_TRIG, LOW);
      usTriggerUs = micros();
      usState = US_WAIT_RISE;
      break;

    case US_WAIT_RISE:
      if (digitalRead(PIN_ULTRASONIC_ECHO) == HIGH) {
        usEchoRiseUs = micros();
        usState = US_WAIT_FALL;
      } else if (micros() - usTriggerUs > US_ECHO_TIMEOUT_US) {
        usLastCycleMs = nowMs;
        usState = US_IDLE;
      }
      break;

    case US_WAIT_FALL:
      if (digitalRead(PIN_ULTRASONIC_ECHO) == LOW) {
        unsigned long durationUs = micros() - usEchoRiseUs;
        float cm = (durationUs * 0.034f) / 2.0f;
        if (cm > 1.0f && cm < 400.0f) {
          lastDistanceCm = cm;
          hasValidDistance = true;
          publishDistance(cm);
          evaluateProximity(cm);
          if (!lcdEnergyScreenActive) {
            lcd.setCursor(0, 1);
            lcd.print(F("                "));
            lcd.setCursor(0, 1);
            lcd.print(lastDistanceCm, 1);
            lcd.print(F(" cm"));
          }
        }
        usLastCycleMs = nowMs;
        usState = US_IDLE;
      } else if (micros() - usEchoRiseUs > US_ECHO_TIMEOUT_US) {
        usLastCycleMs = nowMs;
        usState = US_IDLE;
      }
      break;
  }
}

#if ENABLE_INA219
void updateEnergy() {
  if (!ina219Ready) {
    return;
  }
  unsigned long now = millis();
  if (now - lastEnergyPublishMs < ENERGY_PUBLISH_MS) {
    return;
  }
  lastEnergyPublishMs = now;

  float volts = ina219.getBusVoltage_V();
  float amps = ina219.getCurrent_mA() / 1000.0f;
  float watts = ina219.getPower_mW() / 1000.0f;

  Serial.print(F("ENERGY:V="));
  Serial.print(volts, 2);
  Serial.print(F(",I="));
  Serial.print(amps, 2);
  Serial.print(F(",P="));
  Serial.println(watts, 2);

  if (lcdEnergyScreenActive) {
    lcdDisplayEnergy(volts, amps, watts);
  }
}
#endif

// ---------------------------------------------------------------------------
// Comandos serial
// ---------------------------------------------------------------------------
void sendStatus() {
  Serial.println(lightEntry ? F("LIGHT:ENTRY:ON") : F("LIGHT:ENTRY:OFF"));
  Serial.println(lightLiving ? F("LIGHT:LIVING:ON") : F("LIGHT:LIVING:OFF"));
  Serial.println(lightBedroom ? F("LIGHT:BEDROOM:ON") : F("LIGHT:BEDROOM:OFF"));

  if (proximityNear) {
    Serial.println(F("PROXIMITY:NEAR"));
  } else {
    Serial.println(F("PROXIMITY:FAR"));
  }

  if (SERVOS_ENABLED) {
    Serial.println(doorOpen ? F("DOOR:OPEN") : F("DOOR:CLOSED"));
    Serial.println(windowOpen ? F("WINDOW:OPEN") : F("WINDOW:CLOSED"));
  }

  Serial.println(alarmActive ? F("BUZZER:ON") : F("BUZZER:OFF"));

  if (hasValidDistance) {
    publishDistance(lastDistanceCm);
  }

#if ENABLE_INA219
  if (ina219Ready) {
    float volts = ina219.getBusVoltage_V();
    float amps = ina219.getCurrent_mA() / 1000.0f;
    float watts = ina219.getPower_mW() / 1000.0f;
    Serial.print(F("ENERGY:V="));
    Serial.print(volts, 2);
    Serial.print(F(",I="));
    Serial.print(amps, 2);
    Serial.print(F(",P="));
    Serial.println(watts, 2);
  }
#endif
}

void processCommand(const String &cmd) {
  if (cmd.equals("ENTRY_ON")) {
    setLightEntry(true);
    return;
  }
  if (cmd.equals("ENTRY_OFF")) {
    setLightEntry(false);
    return;
  }
  if (cmd.equals("LIVING_ON")) {
    setLightLiving(true);
    return;
  }
  if (cmd.equals("LIVING_OFF")) {
    setLightLiving(false);
    return;
  }
  if (cmd.equals("BEDROOM_ON")) {
    setLightBedroom(true);
    return;
  }
  if (cmd.equals("BEDROOM_OFF")) {
    setLightBedroom(false);
    return;
  }
  if (cmd.equals("DOOR_OPEN")) {
    setDoorOpen(true);
    return;
  }
  if (cmd.equals("DOOR_CLOSE")) {
    setDoorOpen(false);
    return;
  }
  if (cmd.equals("WINDOW_OPEN")) {
    setWindowOpen(true);
    return;
  }
  if (cmd.equals("WINDOW_CLOSE")) {
    setWindowOpen(false);
    return;
  }
  if (cmd.equals("ALARM_ON")) {
    setAlarm(true);
    return;
  }
  if (cmd.equals("ALARM_OFF")) {
    setAlarm(false);
    return;
  }
  if (cmd.equals("STATUS")) {
    sendStatus();
    return;
  }

  Serial.println(F("ERROR:UNKNOWN_COMMAND"));
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char c = static_cast<char>(Serial.read());
    if (c == '\n' || c == '\r') {
      if (serialBuffer.length() > 0) {
        serialBuffer.trim();
        processCommand(serialBuffer);
        serialBuffer = "";
      }
    } else if (serialBuffer.length() < 48) {
      serialBuffer += c;
    }
  }
}

// ---------------------------------------------------------------------------
// Arduino
// ---------------------------------------------------------------------------
void setup() {
  pinMode(PIN_LED_ENTRY, OUTPUT);
  pinMode(PIN_LED_LIVING, OUTPUT);
  pinMode(PIN_LED_BEDROOM, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_ULTRASONIC_TRIG, OUTPUT);
  pinMode(PIN_ULTRASONIC_ECHO, INPUT);

  digitalWrite(PIN_LED_ENTRY, LOW);
  digitalWrite(PIN_LED_LIVING, LOW);
  digitalWrite(PIN_LED_BEDROOM, LOW);
  digitalWrite(PIN_BUZZER, LOW);
  digitalWrite(PIN_ULTRASONIC_TRIG, LOW);

  lightEntry = false;
  lightLiving = false;
  lightBedroom = false;
  proximityNear = false;

  Wire.begin();

  lcd.init();
  lcd.backlight();
  lcdShowBoot();

  Serial.begin(9600);
  Serial.println(F("READY"));

#if ENABLE_INA219
  ina219Ready = ina219.begin();
  if (!ina219Ready) {
    Serial.println(F("INA219:INIT_FAILED"));
  }
#else
  // Sin INA219: no se envían valores de energía inventados.
#endif

  if (SERVOS_ENABLED) {
    attachServosIfEnabled();
  }

  delay(20);  // Breve pausa para estabilizar LCD tras READY (<= 20 ms permitido).
  lcdShowMain();
  lcdAltToggleMs = millis();
}

void loop() {
  readSerialCommands();
  updateUltrasonic();
  updateBuzzer();
  updateLcdAlternate();
#if ENABLE_INA219
  updateEnergy();
#endif
}
