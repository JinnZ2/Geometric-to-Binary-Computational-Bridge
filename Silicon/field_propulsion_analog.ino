/* ============================================================
   FIELD PROPULSION ANALOG CONTROLLER  v0.9
   Compatible with Teensy 4.x / ESP32
   Drives 12 phase-shifted outputs per JSON spec
   ============================================================ */

#include <Arduino.h>
#include <Wire.h>

// ====== CONFIG (match JSON) ======
const uint8_t N = 12;          // number of nodes
const float f0_hz = 40000.0;   // base frequency
const float delta_phi_rad = 4.712f; // 270° per node
const float log_alpha = 0.0f;  // 0 = equal freq
const float amplitude = 0.8f;  // 0–1
const uint16_t burst_ms = 250;
const uint16_t burst_period_ms = 750;

elapsedMillis tBurst;
bool burstOn = true;

float phase[N];
float freq[N];
float twoPiFdt[N];
uint32_t lastMicros = 0;
float sample_dt = 1e-6f;       // will compute later

// ====== pin mapping ======
const uint8_t pins[N] = {2,3,4,5,6,7,8,9,10,11,12,13};

// ====== setup ======
void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("Field Propulsion Analog Controller v0.9");

  for (int i=0;i<N;i++) pinMode(pins[i], OUTPUT);

  // Pre-compute frequencies and phase offsets
  for (int i=0;i<N;i++) {
    phase[i] = i * delta_phi_rad;
    freq[i] = f0_hz * (1.0f + log_alpha * log(i+1));
  }
  sample_dt = 1.0f / (f0_hz * 100.0f); // oversample ×100
  lastMicros = micros();
}

// ====== loop ======
void loop() {
  uint32_t now = micros();
  float dt = (now - lastMicros) * 1e-6f;
  lastMicros = now;

  // Burst gating
  if (tBurst > (burstOn ? burst_ms : burst_period_ms)) {
    burstOn = !burstOn;
    tBurst = 0;
  }

  if (!burstOn) {
    // outputs OFF
    for (int i=0;i<N;i++) digitalWrite(pins[i], LOW);
    delayMicroseconds(200);
    return;
  }

  static float t = 0.0f;
  t += dt;

  for (int i=0;i<N;i++) {
    float s = amplitude * sinf(2.0f * PI * freq[i] * t + phase[i]);
    uint8_t pwm = (uint8_t)((s * 0.5f + 0.5f) * 255);
    analogWrite(pins[i], pwm);
  }

  // simple serial telemetry (every 100 ms)
  static elapsedMillis logTimer;
  if (logTimer > 100) {
    logTimer = 0;
    Serial.print("t(ms)="); Serial.print(millis());
    Serial.print(", Δφ="); Serial.print(delta_phi_rad,3);
    Serial.print(", burst="); Serial.println(burstOn ? "ON":"OFF");
  }
}
