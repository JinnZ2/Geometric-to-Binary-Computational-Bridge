"""
causality.py  (fabrication/passes/)

Sequential Causality Assignment Procedure (SCAP) for bond graphs.

Reference: Karnopp, Margolis, Rosenberg, "System Dynamics: A Unified
Approach" -- junction strong rules for causality:

  0-junction (shared effort)  -> exactly ONE bond brings effort IN;
                                 all other bonds carry effort OUT.
  1-junction (shared flow)    -> exactly ONE bond brings flow IN;
                                 all other bonds carry flow OUT.

Element causality preferences:

  I-element (store_flow)   wants effort_in   (integrates effort -> p)
  C-element (store_effort) wants flow_in     (integrates flow  -> q)
  R-element (dissipate)    accepts either
  source_e                 forces effort_out at its junction
  source_f                 forces flow_out at its junction
  TF / GY                  causality propagated from counterpart

Pass is a no-op when an IR has no junctions/bonds (legacy IRs).

License: CC0. Stdlib only.
"""


ELEMENT_PREFERENCE = {
    "store_flow":     "integral",
    "store_effort":   "integral",
    "dissipate":      "either",
    "dissipate_dynamic": "either",
    "transform":      "propagate",
    "transformer":    "propagate",
    "gyrate":         "propagate",
    "source_effort":  "fixed_se",
    "source_flow":    "fixed_sf",
}


def assign_causality(ir):
    """Annotate every bond in `ir` with causality direction.

    Raises RuntimeError if an algebraic loop is detected after
    propagation. Returns the IR for chaining.

    Legacy IRs (no junctions/bonds) pass through unchanged.
    """
    if not ir.bonds:
        return ir

    # Step 1: forced causality from sources
    for idx, el in enumerate(ir.elements):
        pref = ELEMENT_PREFERENCE.get(el.kind, "either")
        if pref == "fixed_se":
            _force_bond(ir, idx, "effort_out_at_junction")
        elif pref == "fixed_sf":
            _force_bond(ir, idx, "flow_out_at_junction")

    # Step 2: integral causality preferred by I and C elements
    for idx, el in enumerate(ir.elements):
        if ELEMENT_PREFERENCE.get(el.kind) == "integral":
            _try_integral(ir, idx, el.kind)

    # Step 3: propagate constraints through junctions until stable
    changed = True
    while changed:
        changed = _propagate_junction_constraints(ir)

    # Step 4: leftover unassigned bonds = algebraic loop
    loops = _detect_algebraic_loops(ir)
    if loops:
        raise RuntimeError(
            f"algebraic loop detected at: {loops}. "
            "insert resistance or accept derivative causality"
        )
    return ir


def _force_bond(ir, element_idx, direction):
    """Apply forced causality from a source element."""
    # sources REQUIRE the junction-side bond to receive their output:
    # source_effort -> its junction sees effort_in (the source delivers
    # the effort); source_flow -> its junction sees flow_in. So for the
    # bond traveling FROM source TO junction, causality from the
    # junction's perspective:
    target = "effort_in" if "effort" in direction else "flow_in"
    for b in ir.bonds:
        if b.element_idx == element_idx:
            b.causality = target


def _try_integral(ir, element_idx, kind):
    target = "effort_in" if kind == "store_flow" else "flow_in"
    for b in ir.bonds:
        if b.element_idx == element_idx and b.causality is None:
            if _can_assign(ir, b, target):
                b.causality = target


def _can_assign(ir, bond, candidate):
    """Junction strong rule: exactly one effort_in on a 0-junction;
    exactly one flow_in on a 1-junction."""
    junction = next(j for j in ir.junctions if j.id == bond.junction_id)
    rule = "effort_in" if junction.kind == "0" else "flow_in"
    if candidate != rule:
        return True
    already = [b for b in ir.bonds
               if b.junction_id == bond.junction_id
               and b.causality == rule and b is not bond]
    return not already


def _propagate_junction_constraints(ir):
    """Once one bond at a junction carries the strong-rule direction,
    every other bond is forced to the opposite direction."""
    changed = False
    for j in ir.junctions:
        bonds_here = [b for b in ir.bonds if b.junction_id == j.id]
        unassigned = [b for b in bonds_here if b.causality is None]
        if not unassigned:
            continue
        rule = "effort_in" if j.kind == "0" else "flow_in"
        opposite = "flow_in" if rule == "effort_in" else "effort_in"
        assigned_rule = [b for b in bonds_here if b.causality == rule]
        if len(assigned_rule) == 1:
            for b in unassigned:
                b.causality = opposite
                changed = True
        elif len(assigned_rule) == 0 and len(unassigned) == 1:
            # only one unassigned: assign it the rule direction
            unassigned[0].causality = rule
            changed = True
    return changed


def _detect_algebraic_loops(ir):
    """Bonds still unassigned after propagation indicate a loop."""
    return [(b.element_idx, b.junction_id)
            for b in ir.bonds if b.causality is None]
