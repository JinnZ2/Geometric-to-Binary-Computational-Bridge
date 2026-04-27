# Tier 3 — RF spectrum (planned)

> Adds wideband RF capture to the Tier-1/2 base. The point is *not*
> to decode any specific transmission — it is to characterise the RF
> environment as a whole and detect shifts (animal-tracker collars,
> weather-radio bursts, human-activity proxies). ~$25 incremental
> cost on top of an existing Pi.

## Sensors to add

| Sensor        | Notes                                                  |
|---------------|--------------------------------------------------------|
| RTL-SDR dongle (R820T2) | 24 MHz – 1.766 GHz, 2.4 MS/s. The standard cheap |
|               | software-defined radio. Runs over USB on any computer  |
|               | with the `rtl_sdr` driver suite installed.             |

## Driver scaffolding

* `sensing/firmware/sensor_drivers/rf_scanner.py`
  * Wraps `pyrtlsdr` for the captures.
  * Emits one `SensorReading` per scan window, with values:
    `band_24_88_mhz_dbm`, `band_88_174_mhz_dbm`, `band_174_400_mhz_dbm`,
    `band_400_800_mhz_dbm`, `band_800_1766_mhz_dbm`. Each is the
    median power across the band over the capture interval.
  * `confidence_grade = 0.65` — RF interpretation is one inference
    layer removed from a clean physical reading.

## Operational note

RF capture is power-hungry compared to Tier 1/2. Even at low duty
cycle (e.g. one 5-second scan every 15 minutes) it roughly doubles
the average node load. Re-run `solar_power_calc.py` with the new
load before adding it to a battery-only deployment.

## Status

**Not yet implemented.** Adding it is a multi-day commitment
(driver + calibration + a stable noise-floor baseline per band).
Defer until Tier 1+2 are deployed and you have at least a month of
baseline data without RF.
