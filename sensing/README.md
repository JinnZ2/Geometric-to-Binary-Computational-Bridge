# sensing — direct observation → primitive → CLAIM_SCHEMA bridge

> Field-side counterpart to the in-silico bridges. Build with
> whatever you have today — even a single soil-moisture probe and a
> phone battery generate ground truth that models can't dismiss.
> Every driver mocks cleanly so you can develop on a laptop and
> deploy when the hardware shows up.

## What this produces

A stream of `Primitive` records — timestamped, location-stamped,
co-located observations with explicit epistemic confidence.
Primitives are **measurements**, not laws; they support or falsify
the differential `Claims` in the repo-root `.claims` file.

| Artifact         | Format                       | Purpose                                  |
|------------------|------------------------------|------------------------------------------|
| `.obs` file      | one Primitive/line, tab-sep  | local rolling log on the node            |
| `.obs.queue`     | same shape + cursor sidecar  | persistent FIFO for offline transmission |
| spoken CB script | NATO-phonetic-style string   | voice relay over CB / HAM voice          |
| KISS frame       | `0xC0 0x00 <payload> 0xC0`   | TNC packet-radio for HAM operators       |
| LoRa packet      | UTF-8 bytes (chunked if >MTU)| direct mesh transmission                 |

## Layout

```
sensing/
├── README.md
├── sensing_node.py                # bare-minimum runnable node
├── firmware/
│   ├── sleep_wake_scheduler.py    # tick loop with crash recovery
│   ├── local_logger.py            # bind drivers + recipe + transport
│   └── sensor_drivers/
│       ├── base.py                # SensorDriver + SensorReading
│       ├── ds18b20.py             # 1-wire temperature (real + mock)
│       ├── soil_moisture.py       # capacitive probe (real + mock)
│       ├── ir_sensor.py           # MLX90614 IR thermometer (real + mock)
│       └── motion_acoustic.py     # PIR + USB mic (real + mock)
├── processing/
│   ├── epi_classifier.py          # confidence + provenance grading
│   ├── primitives_encoder.py      # build/serialise Primitives + .obs codec
│   └── anomaly_detector.py        # rolling baseline + threshold
├── transmission/
│   ├── queue_manager.py           # persistent FIFO with cursor
│   ├── lora_transmit.py           # LoRa wrapper (stub by default)
│   ├── ham_kiss_wrapper.py        # KISS framing for TNC packet radio
│   └── cb_relay_format.py         # CB voice script renderer
├── hardware/
│   ├── tier1_minimal.md           # build guide + BOM (~$150)
│   ├── tier2_spectrum.md          # planned (~$300)
│   ├── tier3_rf_sensing.md        # planned RTL-SDR addition
│   └── solar_power_calc.py        # runtime + storm-margin estimator
├── docs/
│   ├── INSTALLATION.md
│   ├── CALIBRATION.md
│   ├── INTERPRETATION.md
│   └── TROUBLESHOOTING.md
├── examples/
│   ├── soil_regime_shift.obs
│   ├── bear_activity_log.obs
│   └── phenophase_anomaly.obs
└── tests/                         # 42 hardware-less unit tests
    ├── test_sensor_drivers.py
    ├── test_processing.py
    ├── test_transmission.py
    └── test_local_logger.py
```

## Two-minute start (no hardware needed)

```bash
# Five mock ticks, no real sleep, output to /tmp.
python sensing/sensing_node.py \
    --max-ticks 5 --interval-seconds 0 --no-sleep --mock \
    --output /tmp/node.obs --queue /tmp/node.obs.queue

# Watch what was written:
column -ts $'\t' /tmp/node.obs

# Run the test suite:
PYTHONPATH=. python -m unittest discover -s sensing/tests
```

## Five-minute deploy (Pi Zero with one DS18B20)

1. Wire one DS18B20 to GPIO4 + 4.7 kΩ pull-up.
2. `raspi-config` → enable 1-wire.
3. `pip install -r requirements.txt` (numpy + scipy + matplotlib).
4. `python sensing/sensing_node.py --interval-seconds 300`.
5. Tail `./sensor_log.obs` — each line is a Primitive.

The DS18B20 driver auto-detects the kernel device file and runs
real-hardware mode; every other driver falls back to mock until you
wire its hardware. You get useful data from day one.

## Integration with the repo

* `claim_ref` — every Primitive may name a CLAIM_SCHEMA claim id
  (e.g. `"fourier_heat"`). Use
  `sensing.processing.primitives_encoder.primitives_to_claim_evidence`
  to summarise field support for a specific claim.
* `bounds` — same `(spatial, temporal, scale)` shape as the
  repo-root `CLAIM_TABLE.json`. A Primitive's bounds are directly
  comparable to a Claim's.
* `epi` — explicit provenance label
  (`measured` / `inferred` / `derived` / `asserted`). Mock-mode
  readings always degrade to `inferred` so synthetic data never
  feeds a confident decision.

## License

CC0. Build it, fork it, deploy it. No attribution required.
