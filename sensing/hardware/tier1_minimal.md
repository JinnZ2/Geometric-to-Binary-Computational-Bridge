# Tier 1 — minimal sensing node

> Solar-powered Pi (or old phone), four sensor classes, ~$150 BOM,
> 24–36 h battery runtime through cloudy weather. Produces a stream
> of `Primitive` records in `.obs` format. Mock-mode for every driver
> means you can develop on a laptop and deploy when you have the hardware.

## Bill of materials

| Qty | Item                                | Cost (USD, approx) |
|----:|-------------------------------------|--------------------|
| 1   | Raspberry Pi Zero W (or old phone)  | $15                |
| 4   | DS18B20 1-wire temperature sensors  | $4                 |
| 1   | Capacitive soil-moisture probe      | $8                 |
| 1   | MLX90614 IR thermometer (I²C)       | $25                |
| 1   | PIR motion sensor (HC-SR501 / AM312)| $8                 |
| 1   | USB microphone                      | $12                |
| 1   | 5 W solar panel + charge controller | $30                |
| 1   | USB battery pack (≥ 10 Ah / 37 Wh)  | $20                |
| —   | Cables, breadboard, weather enclosure| $30                |
|     | **TOTAL**                            | **~$150**          |

## Wiring

* **DS18B20 (×4)** — single 1-wire bus on GPIO4 with a 4.7 kΩ pull-up
  to 3.3 V. Each probe has a unique 64-bit ROM address; the driver
  picks the first `28-*` device under `/sys/bus/w1/devices/`. To wire
  several at once, pass `device_address="28-xxxxxxxxxxxx"` per
  driver.
* **Capacitive soil moisture** — analog out → ADC channel of choice
  (MCP3008 on SPI, or ADS1115 on I²C). Pass an `adc_read(channel)`
  callable to `CapacitiveSoilMoistureDriver`.
* **MLX90614** — I²C, default address `0x5A`. Pass an
  `i2c_read_word(register)` callable.
* **PIR** — digital out → GPIO pin. Pass a `gpio_read(pin)` callable.
* **Microphone** — USB audio. Pass a
  `capture_seconds(out_path, seconds)` callable that records to a WAV.

The framework deliberately does not pin a specific GPIO / I²C / SPI
library — different boards (Pi, BeagleBone, Pi-compatible phone
SoCs) use different stacks. Whatever you have, wrap it in the four
callables above.

## Power

Run `python sensing/hardware/solar_power_calc.py` to estimate
runtime. Defaults assume a 5 W panel, 20 Wh battery, 3 peak-sun
hours/day (worst month at 47°N), 5% duty cycle, and a 3-day design
storm — that combination produces a "COMFORTABLE" verdict for a
node that wakes once every five minutes.

## Boot sequence

1. SD card running Raspberry Pi OS Lite, headless, SSH enabled.
2. `pip install -r requirements.txt` (numpy + scipy + matplotlib
   suffice for Tier 1).
3. Enable 1-wire (`raspi-config` → Interface Options).
4. Drop `sensing_node.py` into `/opt/sensing/`.
5. systemd unit at `/etc/systemd/system/sensing-node.service`:

   ```
   [Unit]
   Description=Field sensing node
   After=network.target

   [Service]
   Type=simple
   ExecStart=/usr/bin/python3 /opt/sensing/sensing_node.py \
       --interval-seconds 300 \
       --output /opt/sensing/data/node.obs \
       --queue /opt/sensing/data/node.obs.queue
   Restart=always
   RestartSec=10
   User=pi

   [Install]
   WantedBy=multi-user.target
   ```

6. `systemctl enable --now sensing-node`.
7. `tail -f /opt/sensing/data/node.obs` to watch primitives stream in.

## Calibration

Run mock mode for the first day to verify the pipeline. Then swap
each driver's `mock=True` for the corresponding hardware callable
one at a time, comparing against a known reference (a digital
thermometer, a kitchen scale wet-vs-dry soil sample, a pointed-at-
sky vs pointed-at-skin IR check). Update the per-driver headline
`confidence_grade` if your specific setup is consistently more or
less accurate than the defaults.

See `sensing/docs/CALIBRATION.md` for the full procedure.
