"""
solar_power_calc — runtime estimator for a Tier-1 solar deployment.

Given a panel rating, a battery, a sensor duty cycle, and a season's
typical insolation, predict how long the node runs through cloudy
stretches and how much margin it has on the worst week of the year.

No external dependencies — runs anywhere Python runs. The model is
deliberately coarse: it ignores temperature derating, wiring loss,
charge controller MPPT efficiency, and per-month solar variability
once you go beyond simple seasonal hours-of-sun. Treat the output
as a sanity check, not a final spec; for a real install, add a 50%
safety margin.

Usage::

    python sensing/hardware/solar_power_calc.py
        --panel-watts 5
        --battery-wh 20
        --sun-hours 3
        --avg-load-watts 0.4
        --duty-cycle 0.05
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


@dataclass
class PowerBudget:
    panel_watts:        float    # peak rating
    battery_wh:         float    # nominal capacity at full charge
    sun_hours_per_day:  float    # equivalent peak-sun hours
    avg_load_watts:     float    # active draw of the whole node
    duty_cycle:         float    # 0–1, fraction of time the node is awake
    sleep_load_watts:   float = 0.05   # standby (Pi Zero W idle ≈ 50 mW)
    panel_efficiency:   float = 0.70   # MPPT + battery round-trip + wiring
    battery_dod:        float = 0.50   # depth of discharge before damage
    consecutive_cloudy_days: int = 3   # design-storm run length

    # ------------------------------------------------------------------
    # Daily energy
    # ------------------------------------------------------------------

    @property
    def daily_load_wh(self) -> float:
        active = self.avg_load_watts * 24.0 * self.duty_cycle
        sleep = self.sleep_load_watts * 24.0 * (1.0 - self.duty_cycle)
        return active + sleep

    @property
    def daily_harvest_wh(self) -> float:
        return self.panel_watts * self.sun_hours_per_day * self.panel_efficiency

    @property
    def daily_balance_wh(self) -> float:
        return self.daily_harvest_wh - self.daily_load_wh

    # ------------------------------------------------------------------
    # Storm survival
    # ------------------------------------------------------------------

    @property
    def usable_battery_wh(self) -> float:
        return self.battery_wh * self.battery_dod

    @property
    def storm_runtime_hours(self) -> float:
        """Hours the node runs on battery alone, no harvest."""
        if self.daily_load_wh <= 0:
            return float("inf")
        # Daily load → hourly average draw.
        hourly = self.daily_load_wh / 24.0
        return self.usable_battery_wh / hourly

    @property
    def storm_safety_factor(self) -> float:
        """Battery runtime ÷ design-storm length. >1 = survives."""
        design_hours = self.consecutive_cloudy_days * 24.0
        if design_hours <= 0:
            return float("inf")
        return self.storm_runtime_hours / design_hours

    # ------------------------------------------------------------------
    # Verdict
    # ------------------------------------------------------------------

    def verdict(self) -> str:
        if self.daily_balance_wh < 0:
            return (
                "UNDERSIZED — average daily harvest is less than "
                "average daily load. The battery will deplete over time."
            )
        if self.storm_safety_factor < 1.0:
            return (
                "MARGINAL — daily energy balance is positive but the "
                f"battery only covers {self.storm_runtime_hours:.0f} h "
                f"of cloudy weather, less than the "
                f"{self.consecutive_cloudy_days}-day design storm."
            )
        if self.storm_safety_factor < 1.5:
            return (
                "ADEQUATE — storm safety factor "
                f"{self.storm_safety_factor:.2f}× the design storm. "
                "Add battery capacity or reduce duty cycle for headroom."
            )
        return (
            f"COMFORTABLE — "
            f"{self.storm_safety_factor:.1f}× design-storm margin, "
            f"{self.daily_balance_wh:+.2f} Wh/day surplus."
        )

    def report(self) -> str:
        lines = [
            f"  Panel              : {self.panel_watts:.1f} W peak  "
            f"× {self.sun_hours_per_day:.1f} sun-hours/day  "
            f"× {self.panel_efficiency:.0%} system eff.",
            f"  Battery            : {self.battery_wh:.1f} Wh nominal, "
            f"{self.usable_battery_wh:.1f} Wh usable "
            f"(DoD {self.battery_dod:.0%})",
            f"  Load               : {self.avg_load_watts:.2f} W active × "
            f"{self.duty_cycle:.1%} duty + "
            f"{self.sleep_load_watts:.3f} W sleep",
            "",
            f"  Daily harvest      : {self.daily_harvest_wh:.2f} Wh",
            f"  Daily load         : {self.daily_load_wh:.2f} Wh",
            f"  Daily balance      : {self.daily_balance_wh:+.2f} Wh "
            "(positive = recharging)",
            "",
            f"  Storm runtime      : {self.storm_runtime_hours:.1f} h "
            f"on battery alone",
            f"  Design storm       : "
            f"{self.consecutive_cloudy_days} days = "
            f"{self.consecutive_cloudy_days * 24} h",
            f"  Safety factor      : {self.storm_safety_factor:.2f}×",
            "",
            "  Verdict            : " + self.verdict(),
        ]
        return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Tier-1 solar runtime calculator.")
    p.add_argument("--panel-watts",       type=float, default=5.0)
    p.add_argument("--battery-wh",        type=float, default=20.0)
    p.add_argument("--sun-hours",         type=float, default=3.0,
                   help="equivalent peak-sun hours per day (worst month)")
    p.add_argument("--avg-load-watts",    type=float, default=0.4,
                   help="active power draw of the awake node")
    p.add_argument("--duty-cycle",        type=float, default=0.05,
                   help="fraction of time the node is awake")
    p.add_argument("--sleep-load-watts",  type=float, default=0.05)
    p.add_argument("--cloudy-days",       type=int,   default=3)
    args = p.parse_args(argv)

    budget = PowerBudget(
        panel_watts=args.panel_watts,
        battery_wh=args.battery_wh,
        sun_hours_per_day=args.sun_hours,
        avg_load_watts=args.avg_load_watts,
        duty_cycle=args.duty_cycle,
        sleep_load_watts=args.sleep_load_watts,
        consecutive_cloudy_days=args.cloudy_days,
    )
    print("Tier-1 solar power budget")
    print("=========================")
    print(budget.report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
