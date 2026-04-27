# Tier 2 — spectrum (planned)

> Adds optical and atmospheric spectrum to the Tier-1 base. Useful
> when the question shifts from "is something happening?" to "what
> kind of thing is it?". Doubles BOM cost (~$300 total).

## Sensors to add

| Sensor    | Notes                                                          |
|-----------|----------------------------------------------------------------|
| AS7341    | 9-channel visible + NIR (415–680 nm + clear + NIR). Tracks       |
|           | photoperiod / chlorophyll fluorescence as a plant-stress proxy. |
| BME680    | T + RH + pressure + gas resistance. Gas-R is a coarse CO₂/VOC   |
|           | proxy; pressure trend is the cheapest weather-shift detector.   |
| VEML6075  | UVA + UVB. Animal-stress correlate; complements the IR passive  |
|           | sensors for daytime activity windows.                           |

## Driver scaffolding

Each Tier-2 driver follows the same `SensorDriver` contract as
Tier 1. Implement them as new modules under
`sensing/firmware/sensor_drivers/`:

* `sensing/firmware/sensor_drivers/spectrum_visible.py` — AS7341
* `sensing/firmware/sensor_drivers/atmosphere.py`        — BME680
* `sensing/firmware/sensor_drivers/uv_sensor.py`         — VEML6075

Each must expose a `confidence_grade` class attribute (use the
values listed in the framework spec: 0.80, 0.88, 0.70 respectively)
and pass the existing test suite once added.

## Status

**Not yet implemented.** Tracked here as a road map; build only
when the field needs require it. The Tier-1 stack already produces
useful Primitives — Tier 2 is for richer phenophase / weather /
biology questions.
