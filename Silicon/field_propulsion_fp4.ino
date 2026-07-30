/*
 * field_propulsion_fp4.ino -- instrument firmware for the FP-4 measurement.
 *
 * Drives an N = 8 ring of ultrasonic transducers with a per-node phase
 * gradient, sweeps drive amplitude, and streams force / radiated-power /
 * electrical-power triples to the host. Silicon/fp4_autopilot.py parses the
 * DATA lines and fits F = k*(P_rad/v) + c*P_elec + b.
 *
 * Target: RP2040 (Pico), Teensy 4.x, or any Cortex-M at >= 48 MHz.
 * NOT an AVR -- see the timing budget below; this is enforced at compile time.
 *
 * ---------------------------------------------------------------------------
 * WHAT THIS FIRMWARE WILL AND WILL NOT DO
 * ---------------------------------------------------------------------------
 * It will not emit a DATA line until three things have happened:
 *
 *   1. the balance has been tared (`Z`),
 *   2. the radiated-power survey factor has been entered (`S <factor>`),
 *   3. the operator has declared the physical radiation state (`T <state>`).
 *
 * Until then it emits NEED lines. This is deliberate. A single reference
 * microphone cannot measure total radiated power -- that requires integrating
 * intensity over a closed surface -- so the firmware refuses to pretend its
 * one ADC channel is a power meter. The survey factor is the operator's
 * measured ratio (total radiated watts) / (reference mic watts-equivalent),
 * obtained once from a directivity survey at a known amplitude. If the array
 * geometry, mic position, or drive frequency changes, that factor is void.
 *
 * The muted and detuned states are PHYSICAL configurations -- an absorber cap
 * or clamped cones, and an off-resonance carrier respectively. The firmware
 * can set `detuned` itself (it owns the carrier). It cannot mute the array,
 * so `T muted` is an operator assertion, and the host checks it: fp4_autopilot
 * verifies that muted trials draw the same electrical power as open trials at
 * the same amplitude and that radiated power actually collapsed. A mislabelled
 * state shows up there rather than silently biasing the fit.
 *
 * ---------------------------------------------------------------------------
 * WHY AMPLITUDE AND STATE ARE BOTH SWEPT
 * ---------------------------------------------------------------------------
 * P_rad and P_elec are proportional at fixed radiation efficiency, so an
 * amplitude-only sweep leaves the anomaly term and the thermal term collinear
 * (measured VIF 96) and the fit cannot separate them. The radiation state is
 * what breaks the collinearity. See the fp4_autopilot module docstring; that
 * failure was found by the analysis code's own self-test, not by argument.
 *
 * Phase is NOT swept for FP-4. The thrust claim does not depend on it. Phase
 * is swept only for the §9.1 Bridge communication test, which is separate.
 *
 * ---------------------------------------------------------------------------
 * TIMING BUDGET
 * ---------------------------------------------------------------------------
 * Square-wave drive at F_CARRIER with N phase steps needs an ISR at
 * F_CARRIER * N:
 *
 *     40 kHz * 8  =  320 kHz  ->  3.125 us per step  =  45 deg resolution
 *
 *     AVR    16 MHz :   50 cycles/ISR   -- not feasible, prologue alone is ~30
 *     RP2040 133 MHz:  416 cycles/ISR   -- comfortable
 *     Teensy 600 MHz: 1875 cycles/ISR   -- ample
 *
 * The ISR is one table index and one port write precisely so that this budget
 * is not in question. All eight node levels live in one byte of PHASE_TABLE.
 *
 * ---------------------------------------------------------------------------
 * ARRAY GEOMETRY -- a constraint worth knowing before building
 * ---------------------------------------------------------------------------
 * lambda at 40 kHz in air is 8.58 mm, so grating-lobe-free spacing is
 * <= 4.29 mm. Eight 10 mm transducers on a ring give a 13.1 mm radius and
 * 10.0 mm spacing = 1.17 lambda; 16 mm units give 1.87 lambda. Any buildable
 * 40 kHz ring of commodity transducers is therefore spatially aliased, with
 * real grating lobes.
 *
 * This does not affect FP-2 -- traveling-wave mode indexing depends on the
 * node count, not the spacing -- and it does not affect FP-4's validity, since
 * the momentum bound holds for any radiation pattern whatsoever. It does mean
 * the radiated power survey must be a genuine closed-surface integral: the
 * lobes put a substantial fraction of the power off-axis, and an on-axis
 * measurement scaled by a solid angle will undercount P_rad, which biases k
 * upward -- toward a false anomaly. This is the single most likely way to get
 * a spurious positive out of this apparatus.
 *
 * ---------------------------------------------------------------------------
 * SERIAL COMMANDS
 * ---------------------------------------------------------------------------
 *   Z              tare the balance (array off, 64 averaged samples)
 *   S <factor>     radiated-power survey factor, watts per mic-watt-equivalent
 *   T <state>      declare radiation state: open | detuned | muted
 *   M <m>          traveling-wave mode index; reduced mod N and echoed
 *   A <0..1>       drive amplitude
 *   R              run one block: sweep amplitudes at current state, emit DATA
 *   B <m> <bits>   Bridge test: transmit <bits> at mode <m>, emit BER line
 *   ?              status
 *   X              all drive off
 *
 * Output lines are prefixed. The host ignores everything except DATA.
 *   DATA,<state>,<amplitude>,<dphi_rad>,<force_N>,<p_rad_W>,<p_elec_W>
 *
 * SPDX-License-Identifier: CC-BY-4.0
 */

#include <Arduino.h>
#include <math.h>
#include <stdio.h>      /* sscanf        */
#include <stdlib.h>     /* atof, atol    */
#include <string.h>     /* strcmp, strncpy -- not all cores pull these in */

/* ------------------------------------------------------------------ config */

#define N_NODES        8
#define F_CARRIER   40000UL             /* Hz, transducer resonance          */
#define F_DETUNED   32000UL             /* Hz, off-resonance for `detuned`   */
#define PHASE_STEPS  N_NODES            /* 45 deg per step                   */

#if defined(__AVR__)
#error "AVR cannot service a 320 kHz ISR (50 cycles). Use RP2040/Teensy/M4."
#endif

/* Node drive pins. Kept on one contiguous run so the ISR is a single write
 * on ports that allow it; portable digitalWrite fallback is used otherwise. */
static const uint8_t NODE_PIN[N_NODES] = {2, 3, 4, 5, 6, 7, 8, 9};

static const uint8_t PIN_AMPLITUDE = 10;   /* PWM -> driver rail setpoint    */
static const uint8_t PIN_HX711_DT  = 11;   /* load cell data                 */
static const uint8_t PIN_HX711_SCK = 12;   /* load cell clock                */
static const uint8_t PIN_MIC       = A0;   /* reference microphone, rectified*/
static const uint8_t PIN_ISENSE    = A1;   /* rail current sense             */
static const uint8_t PIN_VSENSE    = A2;   /* rail voltage sense             */

/* Calibration -- every one of these is a measurement, not a guess. Replace
 * with values from your own bench and record them alongside the data. */
static const float HX711_COUNTS_PER_N = 21500.0f;  /* load cell scale        */
static const float ISENSE_A_PER_V     = 1.0f;      /* current sense gain     */
static const float VSENSE_V_PER_V     = 11.0f;     /* divider ratio          */
static const float ADC_VREF           = 3.3f;
static const uint16_t ADC_FULL_SCALE  = 4095;      /* 12-bit; 1023 on 10-bit */
static const float MIC_W_PER_V2       = 1.0f;      /* mic watt-equivalent    */

static const uint16_t SETTLE_MS       = 4000;      /* thermal settle per point*/
static const uint16_t AVERAGE_SAMPLES = 32;

static const float SWEEP_AMPLITUDES[] = {0.35f, 0.50f, 0.65f, 0.80f, 1.00f};
static const uint8_t N_AMPLITUDES =
    sizeof(SWEEP_AMPLITUDES) / sizeof(SWEEP_AMPLITUDES[0]);
static const uint8_t REPEATS_PER_POINT = 3;

/* ------------------------------------------------------------------- state */

static volatile uint8_t  phaseTable[PHASE_STEPS];  /* node levels per step   */
static volatile uint8_t  phaseIndex   = 0;
static volatile bool     driveEnabled = false;
static volatile bool     tableLock    = false;     /* see buildPhaseTable    */

static int8_t   modeIndex   = 0;        /* reduced to (-N/2, N/2]            */
static float    amplitude   = 0.0f;
static float    surveyFactor = NAN;     /* set by `S`; NAN blocks DATA       */
static long     tareCounts  = 0;
static bool     tared       = false;
static char     radState[12] = "";      /* set by `T`; empty blocks DATA     */

/* --------------------------------------------------------- phase machinery */

/* Reduce a mode index to the signed range (-N/2, N/2]. Δφ = 2πm/N, and m and
 * m+N are the same physical wave -- this is FP-2. An operator who types 6 on
 * an 8-node ring is shown -2, because those are not two modes. */
static int8_t reduceMode(long m) {
  long r = ((m % N_NODES) + N_NODES) % N_NODES;
  if (r > N_NODES / 2) r -= N_NODES;
  return (int8_t)r;
}

static float dphiRadians(int8_t m) {
  return 2.0f * (float)M_PI * (float)m / (float)N_NODES;
}

/* Build the step table: node i is high for the half-cycle following its own
 * phase offset, giving a discrete traveling wave around the ring.
 *
 * Note the sign. The convention everywhere else in this project is
 * phi_i = +2*pi*m*i/N, so node i must LEAD node 0. A drive table advances a
 * node by shifting its waveform EARLIER, so the step delay is (-i*m) mod N,
 * not (+i*m) mod N. The first version of this function used +i*m and produced
 * a wave running the opposite way around the ring while reporting the
 * positive dphi in the DATA line. FP-4 is sign-blind so the thrust number
 * would have survived, but FP-2 and the sign-reversal prediction are exactly
 * about which direction the wave goes, and they would have been read against
 * a mislabelled drive. Verified against propulsion_bounds.aliased_modes() by
 * recovering each node's phase from the emitted table's fundamental Fourier
 * bin -- see tests/test_fp4_autopilot.py::TestFirmwarePhaseTable, which ports
 * this function and checks the recovered gradient. */
static void buildPhaseTable(int8_t m) {
  /* Build into a local buffer, then publish under a lock the ISR honours.
   * The ISR reads this table 320,000 times a second, and runBridgeTest
   * rebuilds it once per transmitted bit -- writing in place would let the
   * ISR read a table that is half old mode and half new. The lock holds the
   * output pins at their current level for the few microseconds of the copy,
   * which costs a fraction of one carrier cycle out of the ~16 per bit and is
   * a bounded, stated artifact rather than an unbounded one. */
  uint8_t next[PHASE_STEPS];
  for (uint8_t s = 0; s < PHASE_STEPS; s++) {
    uint8_t word = 0;
    for (uint8_t i = 0; i < N_NODES; i++) {
      int16_t off = (int16_t)(-(int16_t)i * (int16_t)m) % (int16_t)N_NODES;
      if (off < 0) off += N_NODES;
      uint8_t rel = (uint8_t)(((int16_t)s - off + PHASE_STEPS) % PHASE_STEPS);
      if (rel < PHASE_STEPS / 2) word |= (uint8_t)(1u << i);
    }
    next[s] = word;
  }
  tableLock = true;
  for (uint8_t s = 0; s < PHASE_STEPS; s++) phaseTable[s] = next[s];
  tableLock = false;
}

static void writeNodes(uint8_t word) {
  for (uint8_t i = 0; i < N_NODES; i++) {
    digitalWrite(NODE_PIN[i], (word >> i) & 1u ? HIGH : LOW);
  }
}

/* The whole ISR. One index, one table read, one write. */
static void carrierISR() {
  if (!driveEnabled) { writeNodes(0); return; }
  if (tableLock) return;            /* mid-republish: hold, do not tear */
  phaseIndex = (uint8_t)((phaseIndex + 1) % PHASE_STEPS);
  writeNodes(phaseTable[phaseIndex]);
}

/* Timer setup is board specific. Implemented for RP2040 (repeating alarm via
 * the Arduino-Pico core) and Teensy 4 (IntervalTimer). Add your platform here
 * rather than lowering F_CARRIER -- the phase resolution is the instrument. */
#if defined(ARDUINO_ARCH_RP2040)
  #include "pico/time.h"
  static repeating_timer_t carrierTimer;
  static bool carrierCB(repeating_timer_t *) { carrierISR(); return true; }
  static bool startCarrier(uint32_t fCarrier) {
    int64_t us = -(int64_t)(1000000.0 / (double)(fCarrier * PHASE_STEPS));
    cancel_repeating_timer(&carrierTimer);
    return add_repeating_timer_us((int32_t)us, carrierCB, NULL, &carrierTimer);
  }
#elif defined(__IMXRT1062__)
  static IntervalTimer carrierTimer;
  static bool startCarrier(uint32_t fCarrier) {
    carrierTimer.end();
    float us = 1000000.0f / (float)(fCarrier * PHASE_STEPS);
    return carrierTimer.begin(carrierISR, us);
  }
#else
  #warning "No timer backend for this board -- implement startCarrier()."
  static bool startCarrier(uint32_t) { return false; }
#endif

/* ------------------------------------------------------------- measurement */

static float readADCVolts(uint8_t pin) {
  uint32_t acc = 0;
  for (uint16_t i = 0; i < AVERAGE_SAMPLES; i++) acc += analogRead(pin);
  return ((float)acc / AVERAGE_SAMPLES) * ADC_VREF / (float)ADC_FULL_SCALE;
}

static long readHX711Raw() {
  while (digitalRead(PIN_HX711_DT)) { /* wait for ready */ }
  long value = 0;
  for (uint8_t i = 0; i < 24; i++) {
    digitalWrite(PIN_HX711_SCK, HIGH);
    delayMicroseconds(1);
    value = (value << 1) | (long)digitalRead(PIN_HX711_DT);
    digitalWrite(PIN_HX711_SCK, LOW);
    delayMicroseconds(1);
  }
  digitalWrite(PIN_HX711_SCK, HIGH);   /* gain = 128, channel A */
  delayMicroseconds(1);
  digitalWrite(PIN_HX711_SCK, LOW);
  if (value & 0x800000L) value |= ~0xFFFFFFL;   /* sign extend 24 -> 32 */
  return value;
}

static long readHX711Averaged(uint16_t n) {
  long long acc = 0;
  for (uint16_t i = 0; i < n; i++) acc += readHX711Raw();
  return (long)(acc / (long long)n);
}

static float readForceNewtons() {
  return (float)(readHX711Averaged(AVERAGE_SAMPLES) - tareCounts)
         / HX711_COUNTS_PER_N;
}

static float readElectricalWatts() {
  float v = readADCVolts(PIN_VSENSE) * VSENSE_V_PER_V;
  float a = readADCVolts(PIN_ISENSE) * ISENSE_A_PER_V;
  return v * a;
}

/* Reference mic -> total radiated watts, via the operator's survey factor.
 * Returns NAN when the factor has not been entered, and callers refuse to
 * emit DATA on NAN rather than substituting a default. */
static float readRadiatedWatts() {
  if (isnan(surveyFactor)) return NAN;
  float vm = readADCVolts(PIN_MIC);
  return vm * vm * MIC_W_PER_V2 * surveyFactor;
}

/* ----------------------------------------------------------------- control */

static void setAmplitude(float a) {
  amplitude = constrain(a, 0.0f, 1.0f);
  analogWrite(PIN_AMPLITUDE, (int)(amplitude * 255.0f));
}

static void driveOff() {
  driveEnabled = false;
  setAmplitude(0.0f);
  writeNodes(0);
}

static bool readyToEmit(bool announce) {
  bool ok = true;
  if (!tared)               { if (announce) Serial.println(F("NEED,tare -- send Z")); ok = false; }
  if (isnan(surveyFactor))  { if (announce) Serial.println(F("NEED,survey -- send S <factor> from a closed-surface directivity survey")); ok = false; }
  if (radState[0] == '\0')  { if (announce) Serial.println(F("NEED,state -- send T open|detuned|muted")); ok = false; }
  return ok;
}

static void emitPoint(float amp) {
  float dphi  = dphiRadians(modeIndex);
  float force = readForceNewtons();
  float prad  = readRadiatedWatts();
  float pelec = readElectricalWatts();
  if (isnan(prad)) { Serial.println(F("NEED,survey")); return; }
  Serial.print(F("DATA,"));   Serial.print(radState);
  Serial.print(',');          Serial.print(amp, 4);
  Serial.print(',');          Serial.print(dphi, 6);
  Serial.print(',');          Serial.print(force, 9);
  Serial.print(',');          Serial.print(prad, 9);
  Serial.print(',');          Serial.println(pelec, 6);
}

/* One block: the amplitude sweep at the currently declared radiation state.
 * The host needs at least two states to fit; this emits one, and prints the
 * reminder because a single-state campaign is the design that failed. */
static void runBlock() {
  if (!readyToEmit(true)) return;
  uint32_t f = (strcmp(radState, "detuned") == 0) ? F_DETUNED : F_CARRIER;
  if (!startCarrier(f)) { Serial.println(F("ERR,timer backend missing")); return; }
  Serial.print(F("BLOCK,start,state=")); Serial.print(radState);
  Serial.print(F(",mode=")); Serial.print(modeIndex);
  Serial.print(F(",f=")); Serial.println((unsigned long)f);

  for (uint8_t i = 0; i < N_AMPLITUDES; i++) {
    setAmplitude(SWEEP_AMPLITUDES[i]);
    driveEnabled = true;
    delay(SETTLE_MS);                     /* thermal, not electrical */
    for (uint8_t r = 0; r < REPEATS_PER_POINT; r++) emitPoint(SWEEP_AMPLITUDES[i]);
  }
  driveOff();
  Serial.println(F("BLOCK,end"));
  Serial.println(F("NOTE,run open, detuned AND muted before fitting -- one "
                   "state alone leaves k and c collinear (VIF 96)"));
}

/* Bridge test (§9.1). Independent of the thrust claim: BPSK on the array
 * phase pattern, loopback through a receiving transducer on PIN_MIC. Reports
 * raw error count; the host divides. No synthetic fallback -- if the receiver
 * is not connected this reports the error rate of nothing, which is 0.5, and
 * that is a visible failure rather than a hidden one. */
static void runBridgeTest(int8_t m, uint16_t bits) {
  uint32_t f = F_CARRIER;
  if (!startCarrier(f)) { Serial.println(F("ERR,timer backend missing")); return; }
  buildPhaseTable(m);
  setAmplitude(amplitude > 0.0f ? amplitude : 0.8f);
  driveEnabled = true;
  delay(200);

  float quiet = readADCVolts(PIN_MIC);
  uint16_t errors = 0;
  for (uint16_t i = 0; i < bits; i++) {
    uint8_t tx = (uint8_t)(random(2));
    buildPhaseTable(tx ? m : reduceMode(-(long)m));   /* antipodal signalling */
    delayMicroseconds(400);
    float v = readADCVolts(PIN_MIC);
    uint8_t rx = (v > quiet) ? 1 : 0;
    if (rx != tx) errors++;
  }
  driveOff();
  buildPhaseTable(modeIndex);
  Serial.print(F("BER,")); Serial.print(dphiRadians(m), 6);
  Serial.print(','); Serial.print(bits);
  Serial.print(','); Serial.println(errors);
}

/* ------------------------------------------------------------------ command */

static void printStatus() {
  Serial.println(F("STATUS"));
  Serial.print(F("  nodes      = ")); Serial.println(N_NODES);
  Serial.print(F("  mode m     = ")); Serial.print(modeIndex);
  Serial.print(F("  (dphi = ")); Serial.print(dphiRadians(modeIndex), 4);
  Serial.println(F(" rad)"));
  Serial.print(F("  amplitude  = ")); Serial.println(amplitude, 3);
  Serial.print(F("  state      = "));
  Serial.println(radState[0] ? radState : "UNDECLARED");
  Serial.print(F("  tared      = ")); Serial.println(tared ? F("yes") : F("no"));
  Serial.print(F("  survey     = "));
  if (isnan(surveyFactor)) Serial.println(F("UNSET -- DATA blocked"));
  else Serial.println(surveyFactor, 6);
  Serial.print(F("  emit ready = ")); Serial.println(readyToEmit(false) ? F("yes") : F("no"));
}

static void handleCommand(char *line) {
  char cmd = line[0];
  char *arg = line + 1;
  while (*arg == ' ') arg++;

  switch (cmd) {
    case 'Z':
      driveOff();
      delay(500);
      tareCounts = readHX711Averaged(64);
      tared = true;
      Serial.print(F("TARE,")); Serial.println(tareCounts);
      break;

    case 'S': {
      float f = atof(arg);
      if (!(f > 0.0f)) { Serial.println(F("ERR,survey factor must be > 0")); break; }
      surveyFactor = f;
      Serial.print(F("SURVEY,")); Serial.println(surveyFactor, 6);
      break;
    }

    case 'T':
      if (strcmp(arg, "open") && strcmp(arg, "detuned") && strcmp(arg, "muted")) {
        Serial.println(F("ERR,state must be open|detuned|muted"));
        break;
      }
      strncpy(radState, arg, sizeof(radState) - 1);
      radState[sizeof(radState) - 1] = '\0';
      Serial.print(F("STATE,")); Serial.println(radState);
      if (strcmp(radState, "muted") == 0) {
        Serial.println(F("NOTE,muted is a PHYSICAL change -- cap or clamp the "
                         "cones now. The host verifies P_elec is unchanged."));
      }
      break;

    case 'M': {
      int8_t m = reduceMode(atol(arg));
      modeIndex = m;
      buildPhaseTable(modeIndex);
      Serial.print(F("MODE,")); Serial.print(modeIndex);
      Serial.print(F(",dphi=")); Serial.println(dphiRadians(modeIndex), 6);
      if (atol(arg) != (long)m) {
        Serial.print(F("NOTE,")); Serial.print(atol(arg));
        Serial.print(F(" aliases to ")); Serial.print(m);
        Serial.println(F(" on this ring -- same physical wave (FP-2)"));
      }
      break;
    }

    case 'A':
      setAmplitude(atof(arg));
      Serial.print(F("AMP,")); Serial.println(amplitude, 3);
      break;

    case 'R': runBlock(); break;

    case 'B': {
      long m = 0; long bits = 0;
      if (sscanf(arg, "%ld %ld", &m, &bits) != 2 || bits <= 0) {
        Serial.println(F("ERR,usage B <m> <bits>"));
        break;
      }
      runBridgeTest(reduceMode(m), (uint16_t)min(bits, 20000L));
      break;
    }

    case 'X': driveOff(); Serial.println(F("OFF")); break;
    case '?': printStatus(); break;
    default:  Serial.println(F("ERR,unknown -- Z S T M A R B X ?")); break;
  }
}

/* --------------------------------------------------------------- lifecycle */

void setup() {
  Serial.begin(115200);
  for (uint8_t i = 0; i < N_NODES; i++) {
    pinMode(NODE_PIN[i], OUTPUT);
    digitalWrite(NODE_PIN[i], LOW);
  }
  pinMode(PIN_AMPLITUDE, OUTPUT);
  pinMode(PIN_HX711_SCK, OUTPUT);
  pinMode(PIN_HX711_DT, INPUT);
  digitalWrite(PIN_HX711_SCK, LOW);
#if defined(ARDUINO_ARCH_RP2040) || defined(__IMXRT1062__)
  analogReadResolution(12);
#endif
  driveOff();
  buildPhaseTable(modeIndex);

  Serial.println(F("FP-4 instrument ready."));
  Serial.println(F("This firmware measures the momentum ratio F/(P_rad/v)."));
  Serial.println(F("It will not emit DATA until tared (Z), survey factor set"));
  Serial.println(F("(S), and radiation state declared (T). Sweep amplitude in"));
  Serial.println(F("all three states -- open, detuned, muted -- or the fit"));
  Serial.println(F("cannot separate thrust from driver heating."));
  printStatus();
}

void loop() {
  static char buf[64];
  static uint8_t n = 0;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      buf[n] = '\0';
      if (n) handleCommand(buf);
      n = 0;
    } else if (n < sizeof(buf) - 1) {
      buf[n++] = c;
    }
  }
}
