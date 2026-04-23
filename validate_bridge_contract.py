from __future__ import annotations

import json
from pathlib import Path

from solver_registry import Registry
from Silicon.core.bridges import BRIDGE_ENCODERS, BRIDGE_CATALOG, DOMAIN_BRIDGES
from cross_repo_bridge_contract import load_bridge_contract, list_bridge_domains, list_hardware_modules


root = Path(__file__).resolve().parent
manifest = load_bridge_contract()
registry = Registry()
registry_names = sorted(
    name.removeprefix('encode_')
    for name, solver in registry._solvers.items()
    if solver.category == 'bridge' and name.startswith('encode_')
)
manifest_names = [entry['name'] for entry in manifest['bridge_domains']]
adapter_names = sorted(BRIDGE_ENCODERS.keys())
catalog_names = sorted(BRIDGE_CATALOG.keys())
domain_catalog_names = sorted(record.name for record in DOMAIN_BRIDGES)

print('MANIFEST_NAMES', manifest_names)
print('REGISTRY_NAMES', registry_names)
print('ADAPTER_ENCODERS', adapter_names)
print('ADAPTER_CATALOG', catalog_names)
print('DOMAIN_CATALOG', domain_catalog_names)
print('HELPER_BRIDGES', list_bridge_domains())
print('HELPER_HARDWARE', list_hardware_modules())

missing_from_registry = sorted(set(manifest_names) - set(registry_names))
missing_from_adapters = sorted(set(manifest_names) - set(adapter_names))
missing_from_catalog = sorted(set(manifest_names) - set(catalog_names))
missing_from_domain_catalog = sorted(set(manifest_names) - set(domain_catalog_names))

extra_in_registry = sorted(set(registry_names) - set(manifest_names))
extra_in_adapters = sorted(set(adapter_names) - set(manifest_names))
extra_in_catalog = sorted(set(catalog_names) - set(manifest_names))
extra_in_domain_catalog = sorted(set(domain_catalog_names) - set(manifest_names))

print('MISSING_FROM_REGISTRY', missing_from_registry)
print('MISSING_FROM_ADAPTERS', missing_from_adapters)
print('MISSING_FROM_CATALOG', missing_from_catalog)
print('MISSING_FROM_DOMAIN_CATALOG', missing_from_domain_catalog)
print('EXTRA_IN_REGISTRY', extra_in_registry)
print('EXTRA_IN_ADAPTERS', extra_in_adapters)
print('EXTRA_IN_CATALOG', extra_in_catalog)
print('EXTRA_IN_DOMAIN_CATALOG', extra_in_domain_catalog)

if any([
    missing_from_registry,
    missing_from_adapters,
    missing_from_catalog,
    missing_from_domain_catalog,
    extra_in_registry,
    extra_in_adapters,
    extra_in_catalog,
    extra_in_domain_catalog,
]):
    raise SystemExit(1)

print('BRIDGE_CONTRACT_VALIDATION_OK')
