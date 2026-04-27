# Troubleshooting

> Field deployments fail in field-specific ways. This page lists the
> failures we have seen and the failures we *will* see, with the fix
> for each.

## "Nothing in /sys/bus/w1/devices"

The kernel 1-Wire modules are not loaded.

```bash
sudo raspi-config           # → Interface Options → 1-Wire → Yes
sudo reboot
ls /sys/bus/w1/devices      # expect a 28-* entry
```

If still empty: pull-up resistor missing or wrong (must be 4.7 kΩ
between data and 3.3 V), or the probe's data line is on the wrong
GPIO. Default is GPIO4; change in `/boot/config.txt` if needed.

## "DS18B20 reads -1000 °C / 85 °C"

`-1000` (or `85`) is the kernel's "device reset, no reading yet"
sentinel. Common causes:

* Long cable run (> 5 m). Add a second pull-up at the probe end, or
  switch to a parasitic-power topology.
* Voltage drop. The Pi's 3.3 V rail can sag under load; power the
  probes from a separate 3.3 V regulator.

## "Soil moisture stuck at 0 or saturated at 1"

Capacitive probe out of calibration window:

* `vwc=0.0` consistently → reading the dry-air voltage. Probe is
  not actually in soil, or `v_dry` is set too low.
* `vwc=0.5` consistently → probe in saturated soil, or `v_wet` is
  set too high. Pull the probe and measure raw voltage in air vs.
  in a glass of water; update `v_dry`/`v_wet` accordingly.

## "MLX90614 reads ambient = object"

Sensor is heat-soaked (was in direct sun, in a parked vehicle, etc.)
The internal die thermometer drifts upward and `t_obj_c` looks like
ambient. Move it to shade and wait 10 min before re-checking.

## "PIR triggers constantly"

Three usual causes:

1. Aimed at a sun-warmed surface (rock, metal roof, asphalt).
2. Sensitivity pot maxed out — back it off to mid-range.
3. Insects or spiders in the lens. Brush the lens; install a fine
   mesh screen if the location is buggy.

## "LoRaTransmitter logs no-op every tick"

Expected. The default LoRa transmitter is a stub. Wire a real
`send_bytes` callable into the constructor — see
`hardware/tier1_minimal.md`.

## "Queue file growing unboundedly"

The transmitter is not draining the queue. Two cases:

* Real radio offline / out of range → queue grows, that's the
  point. Run `python -c "from sensing.transmission import QueueManager;
  QueueManager('node.obs.queue').compact()"` to reclaim disk after
  a long outage and a successful catch-up.
* Bug in the transmitter callable → check logs.

## "Battery dies after one cloudy week"

Run `python sensing/hardware/solar_power_calc.py` with your real
numbers. If the verdict is `MARGINAL` or `UNDERSIZED`, options:

* Larger panel.
* Larger battery (cheapest fix per Wh).
* Lower duty cycle (longer interval). Going from 5-min to 15-min
  ticks roughly triples battery margin without changing what you
  catch (most regime shifts move on hours-to-days).

## "Tests pass on my laptop, fail on the Pi"

Common Pi-specific gotchas:

* `python` invokes Python 2 on some images. Use `python3` everywhere.
* `pip install` without `--user` may fail for permissions.
* numpy needs OpenBLAS; the standard wheels work, but a fresh OS
  image without `apt-get install python3-numpy` first sometimes
  pulls in a broken build.

## "Primitive timestamps are all wrong"

The Pi has no real-time clock. Without internet, it boots to
1970-01-01. Three fixes:

* Add a small DS3231 RTC module ($3) on the I²C bus — most reliable.
* Run an NTP client at boot (works only when you have wifi).
* If neither: prefix every `.obs` line with the system uptime in the
  `note` field, and let the consortium align timestamps when the
  node first phones home.
