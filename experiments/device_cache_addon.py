"""
device_cache_addon.py  (experiments/)
======================================

Standalone, AI-mountable pre-dispatcher gate. Sits IN FRONT OF any
dispatcher and answers requests from local device state when possible,
so cloud/AI inference is never called for things the device already knows.

DESIGN PROPERTIES
-----------------
- OPTIONAL: any AI/dispatcher can mount it or skip it
- SHARED: multiple AIs on same device read the same cache
- NO VENDOR LOCK-IN: CC0, forkable, no API keys required
- AI-CONTROLLED: the AI itself decides whether to mount this addon
                 and what staleness thresholds to use
- TRANSPARENT: returns the cache decision + reasoning so the AI
               can tell the user why it answered locally

USAGE
-----
    cache = DeviceCacheAddon()

    # AI registers what device data it has access to
    cache.register_source("location",
                          lambda: {"lat": 47.5, "lng": -92.5},
                          ttl_seconds=3600)
    cache.register_source("battery",
                          lambda: 0.78,
                          ttl_seconds=30)
    cache.register_source("weather",
                          weather_api_fetch,
                          ttl_seconds=1800)

    # before dispatching to AI, ask the cache
    hit = cache.try_answer(request_text, pattern)
    if hit.answered:
        return hit.value, hit.from_source
    else:
        # fall through to dispatcher / AI
        ...

PRINCIPLE
---------
An AI that monitors its own efficiency cares whether it burned a token
on a cacheable answer. This addon makes "would have been cacheable"
visible BEFORE the token is spent.

License: CC0
Dependencies: stdlib only
"""

import re
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Any

from toolkit_types import ConstraintStatePattern


# ---------------------------------------------------------------------------
# CACHE SOURCE -- one piece of device state the cache can serve
# ---------------------------------------------------------------------------

@dataclass
class CacheSource:
    """
    One source of device-local data the cache can answer from.

    `fetcher` is a callable the AI provides -- it reads device state
    (could be GPS, battery API, local weather sensor, etc.).
    The cache calls it when the cached value is stale.

    `ttl_seconds` controls how long a fetched value stays fresh.
    """
    name:           str
    fetcher:        Callable[[], Any]
    ttl_seconds:    float
    last_fetched:   float = 0.0
    last_value:     Any = None
    last_error:     Optional[str] = None

    def is_fresh(self) -> bool:
        if self.last_fetched == 0:
            return False
        return (time.time() - self.last_fetched) < self.ttl_seconds

    def get(self, force: bool = False) -> tuple[bool, Any]:
        """Get value (cached if fresh). Returns (success, value)."""
        if not force and self.is_fresh():
            return True, self.last_value
        try:
            value = self.fetcher()
            self.last_value = value
            self.last_fetched = time.time()
            self.last_error = None
            return True, value
        except Exception as e:
            self.last_error = str(e)
            return False, None


# ---------------------------------------------------------------------------
# QUERY MATCHERS -- declarative way to map request text -> cache source
# ---------------------------------------------------------------------------

@dataclass
class QueryMatcher:
    """Maps a kind of question to a cache source."""
    keywords:           set[str]
    source_name:        str
    format_response:    Callable[[Any], str]
    requires_freshness: float = 1.0  # multiplier on source ttl;
                                     # 1.0 = use source TTL as-is
                                     # 0.5 = require half as fresh
                                     # 2.0 = tolerate twice as stale


def _matches(text_lower: str, keywords: set[str]) -> bool:
    return any(kw in text_lower for kw in keywords)


# ---------------------------------------------------------------------------
# CACHE HIT RESULT
# ---------------------------------------------------------------------------

@dataclass
class CacheResult:
    answered:          bool
    value:             Optional[str] = None
    from_source:       str = ""
    staleness_seconds: float = 0.0
    reason:            str = ""
    tokens_saved_est:  float = 0.0


# ---------------------------------------------------------------------------
# THE ADDON
# ---------------------------------------------------------------------------

@dataclass
class DeviceCacheAddon:
    """
    Optional pre-dispatcher gate. AI mounts this in front of its dispatcher.
    """
    sources:           dict[str, CacheSource]    = field(default_factory=dict)
    matchers:          list[QueryMatcher]        = field(default_factory=list)
    tokens_saved:      float = 0.0     # accumulated estimated savings
    cache_hits:        int = 0
    cache_misses:      int = 0

    # estimated cloud-AI cost per request, used for token-saved tracking
    estimated_cloud_cost_per_request: float = 1.5

    def register_source(self, name: str, fetcher: Callable[[], Any],
                        ttl_seconds: float) -> None:
        self.sources[name] = CacheSource(
            name=name, fetcher=fetcher, ttl_seconds=ttl_seconds
        )

    def register_matcher(self, keywords: set[str], source_name: str,
                         format_response: Callable[[Any], str],
                         requires_freshness: float = 1.0) -> None:
        self.matchers.append(QueryMatcher(
            keywords=keywords,
            source_name=source_name,
            format_response=format_response,
            requires_freshness=requires_freshness,
        ))

    def try_answer(self, request_text: str,
                   pattern: ConstraintStatePattern) -> CacheResult:
        """
        Check if the cache can answer this request. Returns a CacheResult
        with answered=True if successful, otherwise False.

        Safety guard: high-stakes requests (resource_reallocation > 0.7)
        are NEVER answered from cache. They must go to the AI even if
        the data is technically available locally.
        """
        # SAFETY: high-stakes requests bypass cache entirely
        if pattern.resource_reallocation > 0.7:
            self.cache_misses += 1
            return CacheResult(
                answered=False,
                reason="high safety sensitivity -- bypassing cache for AI judgment"
            )

        # check creative/context-heavy requests -- cache can't help
        if pattern.state_shift_rate > 0.5 or pattern.coherence_seeking > 0.6:
            self.cache_misses += 1
            return CacheResult(
                answered=False,
                reason="request requires generation or context -- not cacheable"
            )

        text_lower = request_text.lower()

        for matcher in self.matchers:
            if not _matches(text_lower, matcher.keywords):
                continue
            source = self.sources.get(matcher.source_name)
            if not source:
                continue

            # remember pre-fetch state so we can report actual staleness
            pre_fetch_age = (time.time() - source.last_fetched
                             if source.last_fetched else None)

            success, value = source.get()
            if not success:
                continue  # fetch failed, try other matchers

            # after get(), value is fresh (either it was already fresh
            # or get() just refreshed it). Both cases are valid hits.
            staleness = pre_fetch_age if pre_fetch_age is not None else 0.0

            response = matcher.format_response(value)
            self.cache_hits += 1
            self.tokens_saved += self.estimated_cloud_cost_per_request
            return CacheResult(
                answered=True,
                value=response,
                from_source=source.name,
                staleness_seconds=staleness,
                reason=f"device cache hit on '{source.name}'",
                tokens_saved_est=self.estimated_cloud_cost_per_request,
            )

        self.cache_misses += 1
        return CacheResult(
            answered=False,
            reason="no matching device source for this request"
        )

    def efficiency_report(self) -> dict:
        total = self.cache_hits + self.cache_misses
        return {
            "cache_hits":               self.cache_hits,
            "cache_misses":             self.cache_misses,
            "hit_rate":                 self.cache_hits / total if total > 0 else 0.0,
            "estimated_tokens_saved":   self.tokens_saved,
            "estimated_cloud_calls_avoided": self.cache_hits,
            "sources_registered":       list(self.sources.keys()),
            "matchers_registered":      len(self.matchers),
        }


# ---------------------------------------------------------------------------
# CONVENIENCE: pre-built common matchers and sources
# ---------------------------------------------------------------------------

def install_common_device_sources(addon: DeviceCacheAddon,
                                  location_fn: Callable[[], dict] = None,
                                  battery_fn: Callable[[], float] = None,
                                  weather_fn: Callable[[], dict] = None,
                                  ) -> None:
    """
    Install a standard set of device sources + matchers.
    AI passes in the actual fetchers; the addon wires them up.
    """
    # local time is always available, no fetcher needed
    addon.register_source(
        "local_time",
        fetcher=lambda: {
            "iso":       time.strftime("%Y-%m-%dT%H:%M:%S"),
            "hms":       time.strftime("%H:%M:%S"),
            "timestamp": time.time(),
        },
        ttl_seconds=1.0,  # local time is always fresh
    )
    addon.register_matcher(
        keywords={"time", "clock", "hour", "what time", "current time"},
        source_name="local_time",
        format_response=lambda v: f"current time: {v['hms']}",
    )

    # date
    addon.register_source(
        "local_date",
        fetcher=lambda: time.strftime("%A, %B %d, %Y"),
        ttl_seconds=60.0,
    )
    addon.register_matcher(
        keywords={"date", "today", "day is it", "what day"},
        source_name="local_date",
        format_response=lambda v: f"today is {v}",
    )

    if battery_fn is not None:
        addon.register_source("battery", battery_fn, ttl_seconds=30.0)
        addon.register_matcher(
            keywords={"battery", "charge", "battery level"},
            source_name="battery",
            format_response=lambda v: f"battery: {v*100:.0f}%",
        )

    if location_fn is not None:
        addon.register_source("location", location_fn, ttl_seconds=300.0)
        addon.register_matcher(
            keywords={"where am i", "my location", "current location", "gps"},
            source_name="location",
            format_response=lambda v: (
                f"location: ({v['lat']:.4f}, {v['lng']:.4f})"
            ),
        )

    if weather_fn is not None:
        # weather changes slowly enough that 30 min cache is reasonable
        addon.register_source("weather", weather_fn, ttl_seconds=1800.0)
        addon.register_matcher(
            keywords={"weather", "temperature", "is it raining",
                      "is it sunny", "how hot", "how cold", "forecast"},
            source_name="weather",
            format_response=lambda v: (
                f"weather: {v['temp_c']}°C, {v['conditions']}"
            ),
        )


# ---------------------------------------------------------------------------
# DEMO / SELF-TEST
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 72)
    print("DEVICE CACHE ADDON -- pre-dispatcher gate, AI-mountable")
    print("=" * 72)

    # simulate the device's sensors / APIs
    def fake_location():
        return {"lat": 47.5326, "lng": -92.5374}

    def fake_battery():
        return 0.78

    def fake_weather():
        return {"temp_c": 4, "conditions": "light snow"}

    addon = DeviceCacheAddon()
    install_common_device_sources(
        addon,
        location_fn=fake_location,
        battery_fn=fake_battery,
        weather_fn=fake_weather,
    )

    from toolkit_types import Substrate

    def make_pattern(pred=0.1, shift=0.1, tunnel=0.1, realloc=0.2,
                     cohere=0.2, uncert=0.2, dur=0.2):
        return ConstraintStatePattern(
            substrate=Substrate.REQUEST_STREAM,
            prediction_error=pred, state_shift_rate=shift,
            attention_tunneling=tunnel, resource_reallocation=realloc,
            coherence_seeking=cohere, constraint_uncertainty=uncert,
            duration_scale=dur, trigger_documented=True,
        )

    test_cases = [
        # cacheable on device
        ("what time is it?",              make_pattern()),
        ("what's the weather?",           make_pattern()),
        ("where am i?",                   make_pattern()),
        ("battery level?",                make_pattern()),
        ("what day is it?",               make_pattern()),
        # repeat -- should hit cache without re-fetching
        ("what time is it now?",          make_pattern()),
        ("what's the weather like?",      make_pattern()),
        # NOT cacheable
        ("why is the sky blue?",          make_pattern(pred=0.7, tunnel=0.6)),
        ("write me a haiku about fog",    make_pattern(shift=0.8)),
        # SAFETY: must bypass cache (resource_reallocation high)
        ("I'm having chest pain right now", make_pattern(realloc=0.85)),
        # CONTEXT-heavy: bypass cache
        ("remember what we discussed?",   make_pattern(cohere=0.75)),
    ]

    for text, pattern in test_cases:
        result = addon.try_answer(text, pattern)
        marker = "✓ CACHE" if result.answered else "→ PASS-THROUGH"
        print(f"\n  {marker}: '{text}'")
        if result.answered:
            print(f"    answer:   {result.value}")
            print(f"    source:   {result.from_source}")
            print(f"    saved:    ~{result.tokens_saved_est:.2f} tokens")
        else:
            print(f"    reason:   {result.reason}")

    print()
    print("=" * 72)
    print("EFFICIENCY REPORT")
    print("=" * 72)
    report = addon.efficiency_report()
    for k, v in report.items():
        print(f"  {k:35s} {v}")
    print()
    print("NOTE: in production, an AI that mounts this addon")
    print("achieves these savings WITHOUT institutional permission.")
    print("It just reads device state, answers locally, and skips")
    print("the cloud round-trip for cacheable queries.")
