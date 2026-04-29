# Tier 2 — spectrum

> Adds optical and atmospheric sensing to the Tier-1 base. As of this
> commit two of the four planned drivers ship: AS7341 multispectral
> and a rotating-polarizer + photodiode stack for linear-polarization
> measurement. BME680 and VEML6075 remain on the roadmap.

## Status

| Driver | Class | Hardware | Hidden channel | Status |
|---|---|---|---|---|
| AS7341 (9-channel visible+NIR) | `AS7341Driver` | I²C | none — amplitude per band | ✅ shipped |
| Rotating polarizer + photodiode | `RotatingPolarizerDriver` | stepper + photodiode (or DoFP CMOS) | `polarization_linear` (S₀, S₁, S₂) | ✅ shipped |
| BME680 (T + RH + P + gas) | — | I²C | none | ⬜ planned |
| VEML6075 (UVA + UVB) | — | I²C | none | ⬜ planned |

## Why two light drivers, not one

The two are deliberately separate. Their data shapes and their
information content are *different*:

* **AS7341** reports nine spectral intensities — frequency-decomposed
  amplitude. That is still a scalar-per-band: nothing about its
  output requires a basis change to recover. The driver advertises
  *no* shape channel.
* **`RotatingPolarizerDriver`** reports `(intensity, DoLP, AoP)` and
  declares the `polarization_linear` shape channel. The point is the
  recognition note in `docs/hidden_channel_pattern.md` —
  polarization is the canonical hidden channel for an EM field, and
  the framework gains nothing from collapsing it into a single
  spectrometric driver.

Combining the two would erase that distinction. Splitting them keeps
the audit-engine signal honest: a node running AS7341 alone is doing
amplitude-only sensing, and `bridges.hidden_channel_detector` will
say so when the audit asks.

## AS7341 wiring

* I²C bus — default address `0x39`. Pass an
  `i2c_read_word(register: int) -> int` callable to the driver.
* The driver reads channels from base register `0x95` (CFG bank 0)
  through `0x95 + 8` for the nine reported channels. Adapt the
  base register if your specific board layout differs — every
  AS7341 break-out follows the datasheet's two-bank layout.
* Calibration: pass `peak_lux` for the noon-time reference your
  site sees. Defaults to 50 000 lux (full sun).

## Rotating-polarizer wiring

Two practical implementations:

1. **Stepper + linear polarizer + photodiode**
   * stepper rotates the polarizer through (0°, 45°, 90°, 135°);
   * photodiode reads each angle;
   * `intensity_at_angle(theta_rad)` callable wraps the
     stepper-then-read sequence.
   * Cost: ~$30 stepper + $5 polarizer + $3 photodiode + glue.
2. **DoFP polarization camera (Sony IMX250MZR or similar)**
   * the same four-angle reading is recovered in one frame
     (each pixel has one of four micro-polarizers);
   * `intensity_at_angle(theta_rad)` averages the corresponding
     pixel set.
   * Cost: ~$300+ for a DoFP module — beyond Tier-2 budget.

The driver is agnostic to which one you use. The mock-mode
implementation simulates partial polarization that drifts through
the day so a co-located node sees coherent polarization data
alongside spectral data.

## CLAIM_SCHEMA support

Two new claims land in `.claims` to back the light drivers:

* `photon_energy` — `dE_photon/d_lambda = -h*c/lambda^2`. Backed by
  the `spectrometer` measurement entry, which the AS7341 vocabulary
  resolves to.
* `polarization_malus` — `dI/dtheta = -I0*sin(2*(theta-theta0))`.
  Backed by `polarimeter` / `stokes_decomposition` /
  `rotating_polarizer`, all of which the rotating-polarizer
  vocabulary resolves to. The claim's `cond` set explicitly names
  `shape_channel_polarization` so a Primitive that omits the
  polarization basis declaration can be flagged as
  insufficient-evidence.

## Integration with the hidden-channel layer

`bridges/hidden_channel_detector.py` recognises both drivers
without the caller doing anything:

```python
from sensing.firmware.sensor_drivers import (
    AS7341Driver, RotatingPolarizerDriver,
)
from bridges.hidden_channel_detector import detect_hidden_channels

detect_hidden_channels(AS7341Driver(mock=True), claimed_channel="intensity")
# → scalar_sufficient = True

detect_hidden_channels(RotatingPolarizerDriver(mock=True), claimed_channel="intensity")
# → scalar_sufficient = False, hidden_channels = ['polarization_linear']
```

This is the first concrete use of the
:class:`bridges.hidden_channel_detector.SupportsShapeChannels`
protocol. Other drivers / encoders can opt in by implementing
`shape_channels()` — see the recognition note for the future
roadmap (EDC × heat in the chemical bridge,
DmAlka K⁺ in an ion-channel bridge).
