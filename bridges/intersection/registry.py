"""
DOMAIN_RULES — registry of per-domain IntersectionRule instances.

Built lazily: instances are created on first lookup so importing
``bridges.intersection`` does not force the entire alternative-compute
graph to load.

Extending
---------
To wire a new domain into the Mandala:

1. Write ``bridges/<domain>_alternative_compute.py`` using the
   per-bridge template in
   ``docs/alternative_computing_integration_schedule.md``.
2. Write ``bridges/intersection/<domain>_rule.py`` following the
   existing ``gravity_rule``, ``electric_rule``, etc. pattern —
   subclass :class:`bridges.intersection.base.IntersectionRule`,
   delegate to the domain's ``*_alternative_compute`` module, and
   project onto the shared three-axis basin space.
3. Add the ``"<domain>": "bridges.intersection.<domain>_rule:<Class>"``
   entry to :data:`_RULE_REGISTRY` below.

The registry key is the same domain name used everywhere else
(``"electric"``, ``"gravity"``, ``"sound"``, ``"community"``, …) so
all three registries — binary-encoder, alternative-interpreter, and
intersection-rule — share a single vocabulary.
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from bridges.intersection.base import IntersectionRule


# domain → "<module>:<class>" spec. Resolved lazily to avoid loading
# every alternative-compute module at import time.
_RULE_REGISTRY: Dict[str, str] = {
    "gravity":   "bridges.intersection.gravity_rule:GravityIntersectionRule",
    "electric":  "bridges.intersection.electric_rule:ElectricIntersectionRule",
    "sound":     "bridges.intersection.sound_rule:SoundIntersectionRule",
    "community": "bridges.intersection.community_rule:CommunityIntersectionRule",
}


# Instance cache so callers who look up the same domain repeatedly
# get the same object (useful because IntersectionRule subclasses
# stash the last diagnostic on ``self.last_diagnostic``).
_INSTANCE_CACHE: Dict[str, IntersectionRule] = {}


def _resolve(spec: str) -> type:
    module_name, _, class_name = spec.partition(":")
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)


def get_rule(domain: str) -> IntersectionRule:
    """
    Return the :class:`IntersectionRule` instance for ``domain``.

    Raises
    ------
    KeyError
        If ``domain`` has no registered intersection rule.
    """
    if domain in _INSTANCE_CACHE:
        return _INSTANCE_CACHE[domain]

    if domain not in _RULE_REGISTRY:
        raise KeyError(
            f"No intersection rule registered for {domain!r}. "
            f"Known: {sorted(_RULE_REGISTRY)}"
        )

    cls = _resolve(_RULE_REGISTRY[domain])
    instance = cls()
    _INSTANCE_CACHE[domain] = instance
    return instance


def register_rule(domain: str, rule: IntersectionRule) -> None:
    """
    Register a concrete :class:`IntersectionRule` instance.

    Mostly intended for tests and for downstream repos that want to
    plug in their own domain without editing :data:`_RULE_REGISTRY`.
    Overwrites any existing entry for ``domain``.
    """
    if not isinstance(rule, IntersectionRule):
        raise TypeError(
            f"register_rule expects an IntersectionRule instance; "
            f"got {type(rule).__name__}"
        )
    _INSTANCE_CACHE[domain] = rule


def registered_domains() -> Iterable[str]:
    """List every domain with a registered intersection rule."""
    return sorted(set(_RULE_REGISTRY) | set(_INSTANCE_CACHE))


class _DomainRulesFacade:
    """Dict-shaped facade for the live rule registry."""

    def __contains__(self, domain: str) -> bool:
        return domain in _RULE_REGISTRY or domain in _INSTANCE_CACHE

    def __iter__(self):
        return iter(registered_domains())

    def __len__(self) -> int:
        return len(list(registered_domains()))

    def __getitem__(self, domain: str) -> IntersectionRule:
        return get_rule(domain)

    def get(
        self,
        domain: str,
        default: Optional[IntersectionRule] = None,
    ) -> Optional[IntersectionRule]:
        try:
            return get_rule(domain)
        except KeyError:
            return default

    def keys(self):
        return list(registered_domains())


DOMAIN_RULES = _DomainRulesFacade()


__all__ = [
    "DOMAIN_RULES",
    "get_rule",
    "register_rule",
    "registered_domains",
]
