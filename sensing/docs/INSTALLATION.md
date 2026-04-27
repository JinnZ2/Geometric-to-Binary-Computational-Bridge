# Installation

> Deploy in three phases: dry-run on a laptop, single-sensor proof
> on a Pi, full Tier-1 install on solar.

## Phase 0 — laptop dry-run (no hardware)

```bash
git clone <repo>
cd <repo>
pip install -r requirements.txt        # numpy + scipy + matplotlib
python sensing/sensing_node.py \
    --max-ticks 10 --interval-seconds 0 --no-sleep --mock \
    --output /tmp/dry_run.obs --queue /tmp/dry_run.obs.queue
column -ts $'\t' /tmp/dry_run.obs
```

Confirms: imports work, the encoder emits valid `.obs` lines, the
queue persists, the LoRa stub logs no-op transmissions. No SD card,
no soldering, no field trip.

## Phase 1 — single sensor on a Pi (one evening)

Hardware: Pi Zero W, one DS18B20, one 4.7 kΩ resistor, 3 jumper wires.

1. Flash Raspberry Pi OS Lite, headless, SSH enabled.
2. Boot, SSH in, `sudo raspi-config` → Interface Options → 1-Wire → Yes.
3. Wire the DS18B20:
   * Red → 3.3 V, Black → GND, Yellow → GPIO4
   * 4.7 kΩ between Red and Yellow
4. Reboot. Verify the kernel sees it:
   ```bash
   ls /sys/bus/w1/devices/         # expect a "28-..." entry
   ```
5. Clone the repo, `pip install -r requirements.txt`.
6. Run:
   ```bash
   python sensing/sensing_node.py --interval-seconds 60
   ```
7. Watch `./sensor_log.obs` — surface temperature lines appear; every
   other driver runs in mock mode and emits clearly-marked synthetic
   data. The encoder caps mock-mode primitives at 60% confidence.

## Phase 2 — full Tier-1 deployment (one weekend)

See [`hardware/tier1_minimal.md`](../hardware/tier1_minimal.md) for the
complete BOM and per-sensor wiring. The three additions to Phase 1:

* Capacitive soil moisture probe → MCP3008 SPI ADC → Pi GPIO 8/9/10/11.
* MLX90614 IR thermometer → Pi I²C bus (GPIO 2/3).
* PIR sensor → Pi GPIO 17.
* Solar panel + charge controller + USB battery pack.

Run `python sensing/hardware/solar_power_calc.py` with your panel /
battery / latitude numbers before installing — it will tell you
whether your duty cycle survives the worst storm of the year.

## Phase 3 — turn it into a service

```ini
# /etc/systemd/system/sensing-node.service
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

```bash
sudo systemctl enable --now sensing-node
journalctl -u sensing-node -f
```

## What "installed" means

* `sensor_log.obs` is appending one line every interval.
* `sensor_log.obs.queue` is appending whenever the LoRa stub returns
  False (i.e. every tick if you have not wired a real radio yet).
* `python -m unittest discover -s sensing/tests` returns 42/42.
* The Pi survives a 24-hour power test without dropping below 30 %
  battery (under your typical insolation).
