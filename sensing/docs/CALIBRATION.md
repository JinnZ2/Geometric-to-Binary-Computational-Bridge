# Calibration

> Each sensor ships with a default `confidence_grade`. The default is
> *typical for the sensor class*; it is not a calibration of *your*
> probe in *your* soil. This page is the per-site calibration
> procedure. Skip it and your data is still useful, just not
> trustworthy enough to feed a confident decision.

## DS18B20 (temperature)

**Default grade:** 0.95.

1. Place the probe in a stirred ice-water bath for 5 min.
   Reading should be 0.0 ± 0.5 °C.
2. Place in boiling water (correct for altitude:
   100 °C – 0.0034 × elevation_m).
3. If both endpoints are within 0.5 °C of nominal, keep grade 0.95.
   If either is off by 1–2 °C, drop to 0.85 and apply a linear
   correction in your ingestion script.
4. If off by more than 2 °C, the probe is damaged. Replace.

## Capacitive soil moisture

**Default grade:** 0.85.

Capacitive probes need a per-soil calibration because dielectric
constant varies with mineral content, organic matter, and salinity.

1. Take three samples from the deployment site (top 30 cm).
2. Weigh wet, oven-dry at 105 °C for 24 h, weigh dry. Compute
   gravimetric water content `θ_g = (wet - dry) / dry`.
3. Convert to volumetric: `θ_v ≈ θ_g × ρ_bulk` (ρ_bulk ≈ 1.3 g/cm³
   for a typical loam — measure if you can).
4. Pour each sample into a beaker, push the probe in, record voltage.
5. Update `v_dry` and `v_wet` in `CapacitiveSoilMoistureDriver(...)`
   so a fresh dry sample reads `vwc ≈ 0.05` and a saturated sample
   reads `vwc ≈ 0.45`.
6. Repeat the measurement on a fourth sample. If `vwc_predicted`
   matches `vwc_measured` within 0.05, keep grade 0.85. Else drop
   to 0.70.

## MLX90614 (IR thermometer)

**Default grade:** 0.90.

1. Aim the sensor at a known-temperature blackbody (a tin can of
   warm water with a paper sleeve works; use a contact thermometer
   for ground truth).
2. Aim at a clear sky on a still night — typical reading is
   25–40 °C colder than ambient air.
3. If the difference between MLX-`t_obj_c` and the contact
   thermometer is < 1 °C across 10–40 °C, keep grade 0.90.
   Otherwise drop to 0.80.

## PIR motion

**Default grade:** 0.75.

PIR sensors don't have a calibration so much as an
*aim-and-tune* procedure:

1. Set the on-board sensitivity pot to mid-range.
2. Set the time-delay pot to its minimum.
3. Walk past the sensor at known distances (1, 3, 5, 10 m). Note
   which distances trigger reliably — that's your detection envelope.
4. Aim away from sun-warmed metal and direct heat sources; thermal
   gradients trigger false positives.

There is no per-site numeric correction. The grade stays 0.75 unless
you observe consistent false positives, in which case drop to 0.55.

## Microphone

**Default grade:** 0.55 (this is for the *recording*; species ID is
done in a separate inference layer not shipped here).

1. Record a 30-second clip with a sound source at a known SPL.
2. Listen. Verify no clipping, no DC offset, no buzz.
3. The grade stays 0.55 — raw audio carries low confidence by design.

## Updating the grade in code

Each driver has a class-level `confidence_grade` attribute. To pin a
calibrated grade per node, subclass:

```python
class CalibratedDS18B20(DS18B20Driver):
    confidence_grade = 0.92  # this probe was 0.5 °C off at boiling
```

Or pass `is_calibrated=False` to `LocalLogger` recipe so the epi
classifier applies the uncalibrated penalty to every emitted
Primitive until you have run the procedure above.
