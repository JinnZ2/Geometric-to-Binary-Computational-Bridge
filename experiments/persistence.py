"""
persistence.py  (experiments/)
===============================

Saves and loads the dispatcher's learning state to/from disk.

Without persistence the dispatcher forgets everything on restart, so
"learning" never actually accumulates beyond one process lifetime.
With persistence the system grows smarter over time.

STATUS: experimental. Uses JSON because it's stdlib, human-readable,
and portable. Real deployment may want SQLite or proper DB.

License: CC0
"""

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from comfort_layer_dispatcher import (
    PatternMemory, LearnedPattern, DispatcherStats,
    TierCost, RouteTier, DEFAULT_COSTS
)


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# MEMORY
# ---------------------------------------------------------------------------

def save_memory(memory: PatternMemory, path: Path) -> None:
    _ensure_dir(path)
    data = {
        "resolution": memory.resolution,
        "learned": [
            {
                "pattern_signature": list(lp.pattern_signature),
                "handler_name":      lp.handler_name,
                "times_seen":        lp.times_seen,
                "times_succeeded":   lp.times_succeeded,
                "ai_assists_used":   lp.ai_assists_used,
            }
            for lp in memory.learned
        ],
        "saved_at": time.time(),
    }
    path.write_text(json.dumps(data, indent=2))


def load_memory(path: Path) -> PatternMemory:
    if not path.exists():
        return PatternMemory()
    data = json.loads(path.read_text())
    memory = PatternMemory(resolution=data.get("resolution", 4))
    for entry in data.get("learned", []):
        memory.learned.append(LearnedPattern(
            pattern_signature=tuple(entry["pattern_signature"]),
            handler_name=entry["handler_name"],
            times_seen=entry["times_seen"],
            times_succeeded=entry["times_succeeded"],
            ai_assists_used=entry["ai_assists_used"],
        ))
    return memory


# ---------------------------------------------------------------------------
# STATS
# ---------------------------------------------------------------------------

def save_stats(stats: DispatcherStats, path: Path,
               max_log_entries: int = 1000) -> None:
    """Trim request log to most recent N entries to keep file size bounded."""
    _ensure_dir(path)
    trimmed_log = stats.request_log[-max_log_entries:]
    data = {
        "total_requests":       stats.total_requests,
        "by_tier":              stats.by_tier,
        "total_cost":           stats.total_cost,
        "cost_saved_vs_all_ai": stats.cost_saved_vs_all_ai,
        "request_log":          trimmed_log,
        "saved_at":             time.time(),
    }
    path.write_text(json.dumps(data, indent=2))


def load_stats(path: Path) -> DispatcherStats:
    if not path.exists():
        return DispatcherStats()
    data = json.loads(path.read_text())
    return DispatcherStats(
        total_requests       = data["total_requests"],
        by_tier              = data["by_tier"],
        total_cost           = data["total_cost"],
        cost_saved_vs_all_ai = data["cost_saved_vs_all_ai"],
        request_log          = data["request_log"],
    )


# ---------------------------------------------------------------------------
# COSTS
# ---------------------------------------------------------------------------

def save_costs(costs: dict, path: Path) -> None:
    _ensure_dir(path)
    data = {
        tier.value: {"base_cost": tc.base_cost,
                     "per_unit_cost": tc.per_unit_cost}
        for tier, tc in costs.items()
    }
    path.write_text(json.dumps(data, indent=2))


def load_costs(path: Path) -> dict:
    if not path.exists():
        return dict(DEFAULT_COSTS)
    raw = json.loads(path.read_text())
    out = {}
    for tier_value, costs in raw.items():
        tier = RouteTier(tier_value)
        out[tier] = TierCost(
            tier=tier,
            base_cost=costs["base_cost"],
            per_unit_cost=costs["per_unit_cost"],
        )
    return out


# ---------------------------------------------------------------------------
# CONVENIENCE: full dispatcher state
# ---------------------------------------------------------------------------

def save_dispatcher_state(dispatcher, base_dir: Path) -> dict[str, Path]:
    """Save everything the dispatcher knows. Returns paths written."""
    paths = {
        "memory": base_dir / "memory.json",
        "stats":  base_dir / "stats.json",
    }
    save_memory(dispatcher.memory, paths["memory"])
    save_stats(dispatcher.stats, paths["stats"])
    return paths


def load_dispatcher_state(dispatcher, base_dir: Path) -> dict[str, bool]:
    """Load saved state into existing dispatcher. Returns what was found."""
    found = {"memory": False, "stats": False}
    mem_path = base_dir / "memory.json"
    if mem_path.exists():
        dispatcher.memory = load_memory(mem_path)
        found["memory"] = True
    stats_path = base_dir / "stats.json"
    if stats_path.exists():
        dispatcher.stats = load_stats(stats_path)
        found["stats"] = True
    return found
