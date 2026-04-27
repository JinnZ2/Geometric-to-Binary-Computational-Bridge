"""
sensing_node.py — bare-minimum field node.

Runs on any Pi / phone / laptop. Wires up the four Tier-1 drivers,
the local logger, the persistent queue, and a no-op LoRa transmitter
(swap in a real one once you have a radio). Drivers default to mock
mode if the underlying hardware is not present, so this script
produces real .obs output even on a development laptop.

Usage::

    python sensing/sensing_node.py
        --interval-seconds 300
        --node-id KV_soil_primary
        --location Superior_MN
        --date-range 2026_ongoing
        --depth 0-50cm
        --output ./sensor_log.obs

    # one-shot dry run (5 ticks, no real sleep):
    python sensing/sensing_node.py --max-ticks 5 --interval-seconds 0 --no-sleep
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Make the repo root importable when this file is invoked directly.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sensing.firmware.local_logger import LocalLogger, PrimitiveRecipe
from sensing.firmware.sensor_drivers import (
    CapacitiveSoilMoistureDriver,
    DS18B20Driver,
    MLX90614Driver,
    PIRMotionDriver,
)
from sensing.firmware.sleep_wake_scheduler import Scheduler
from sensing.transmission import LoRaTransmitter, QueueManager


def build_node(
    node_id: str,
    bounds: tuple,
    obs_path: Path,
    queue_path: Path,
    mock: bool,
) -> tuple[LocalLogger, QueueManager]:
    drivers = [
        DS18B20Driver(channel="surface", mock=mock),
        DS18B20Driver(channel="10cm",    mock=mock, seed=2),
        DS18B20Driver(channel="30cm",    mock=mock, seed=3),
        CapacitiveSoilMoistureDriver(channel="primary", mock=mock),
        MLX90614Driver(channel="canopy",                 mock=mock),
        PIRMotionDriver(channel="primary",               mock=mock),
    ]
    queue = QueueManager(queue_path=queue_path)
    transmitter = LoRaTransmitter(send_bytes=None)  # no-op stub

    def transmit_or_queue(primitive) -> bool:
        ok = transmitter(primitive)
        if not ok:
            queue.push(primitive)
        return ok

    recipe = PrimitiveRecipe(
        concept_id=node_id,
        domain="measured_kinesthetic",
        role="direct_observation",
        couplings=("temperature", "moisture", "thermal_ir", "motion"),
        bounds=bounds,
        # The most direct CLAIM_SCHEMA law a Tier-1 node bears on:
        # the Fourier heat-flow claim. Multi-channel temperature data
        # at depth is what supports or falsifies it on this site.
        claim_ref="fourier_heat",
    )
    logger = LocalLogger(
        drivers=drivers, recipe=recipe, obs_path=obs_path,
        transmit=transmit_or_queue,
    )
    return logger, queue


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("--node-id",      default="KV_soil_primary")
    p.add_argument("--location",     default="Superior_MN")
    p.add_argument("--date-range",   default="2026_ongoing")
    p.add_argument("--depth",        default="0-50cm")
    p.add_argument("--interval-seconds", type=float, default=300.0)
    p.add_argument("--max-ticks",    type=int,   default=None,
                   help="exit after N ticks (default: run forever)")
    p.add_argument("--output",       default="./sensor_log.obs")
    p.add_argument("--queue",        default="./sensor_log.obs.queue")
    p.add_argument("--no-sleep",     action="store_true",
                   help="dry run — skip the inter-tick sleep")
    p.add_argument("--mock",         action="store_true",
                   help="force mock mode regardless of detected hardware")
    p.add_argument("--verbose",      action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
    )

    bounds = (args.location, args.date_range, args.depth)
    logger, queue = build_node(
        node_id=args.node_id,
        bounds=bounds,
        obs_path=Path(args.output),
        queue_path=Path(args.queue),
        mock=args.mock,
    )

    sched = Scheduler(interval_seconds=args.interval_seconds)
    sleep_fn = (lambda _s: None) if args.no_sleep else None
    try:
        completed = sched.run_forever(
            logger.tick,
            max_ticks=args.max_ticks,
            sleep_fn=sleep_fn or __import__("time").sleep,
        )
    except KeyboardInterrupt:
        completed = sched.ticks
    finally:
        logger.close()

    stats = logger.stats()
    print(
        f"sensing_node done — ticks={completed}, "
        f"primitives={stats['primitives_emitted']}, "
        f"anomalies={stats['anomalies_flagged']}, "
        f"queued={stats['transmissions_queued']}, "
        f"queue_pending={queue.pending_count()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
