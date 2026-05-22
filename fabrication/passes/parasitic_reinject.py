"""
parasitic_reinject.py  (fabrication/passes/)

Fixed-point loop:

  1. emit artifacts from the current IR
  2. ask each emitter (via its parasitic injector) what physics it
     just materialized that wasn't in the IR
  3. fold those additions back into the IR
  4. re-predict
  5. stop when the parameter set stops moving (delta below
     `tolerance`) or `max_iterations` is hit

The loop is OPTIONAL -- callers that don't want emit-side feedback
just skip this pass. Smokes that do want it can run it after
emit_all() to close the build-back-to-spec loop.

License: CC0. Stdlib only.
"""
import hashlib
import json

from ..emit._common import PARASITIC_INJECTORS


def _hash_params(ir):
    """Stable hash of the IR's element parameter set."""
    blob = []
    for el in ir.elements:
        p = el.parameter
        if isinstance(p, dict):
            blob.append(json.dumps(p, sort_keys=True, default=str))
        else:
            blob.append(repr(p))
    return hashlib.sha256("|".join(blob).encode()).hexdigest()


def _add_to_ir(ir, addition):
    """Append a parasitic element to the IR. `addition` is the dict
    the injector returned: {kind, domain, param, provenance}."""
    # Use a minimal Element-shaped record so this pass works on both
    # the real SubstrateIR and the lightweight test classes that smokes
    # use; both have an `.elements` list that accepts duck-typed items.
    from ..substrate_ir import Element, BondPort
    port = BondPort(domain=addition.get("domain", ir.domain),
                    flow_name="*", effort_name="*")
    el = Element(
        kind=addition["kind"],
        geometry={"provenance": addition.get("provenance", "")},
        parameter=addition["param"],
        port_a=port,
    )
    ir.elements.append(el)


def reinject_cycle(ir, emitted, max_iterations=5, tolerance=1e-9):
    """Fold parasitic physics from emitted artifacts back into `ir`.

    `emitted` is a dict {format_label: emitted_geometry_record}; the
    record shape is whatever the emitter exports for its parasitic
    injector to consume.

    Returns dict {iterations: int, converged: bool, additions: int}.
    """
    prev_hash = _hash_params(ir)
    total_additions = 0
    for it in range(1, max_iterations + 1):
        n_added = 0
        for (domain, fmt), injector in PARASITIC_INJECTORS.items():
            if fmt not in emitted:
                continue
            try:
                additions = injector(emitted[fmt])
            except Exception:
                continue
            for add in additions or []:
                _add_to_ir(ir, add)
                n_added += 1
        total_additions += n_added
        new_hash = _hash_params(ir)
        if new_hash == prev_hash:
            return {"iterations": it, "converged": True,
                    "additions":  total_additions}
        prev_hash = new_hash
    return {"iterations": max_iterations, "converged": False,
            "additions":  total_additions}
