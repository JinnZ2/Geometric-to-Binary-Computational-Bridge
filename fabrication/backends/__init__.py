"""
fabrication/backends/

Concrete substrate physics. One file per domain. Each backend
exposes pure functions that map geometry dicts to bond-graph
parameters; lowering.py composes them into a SubstrateIR.

Currently shipped:
  acoustic.py   pressure / volume-flow (Helmholtz, horn, viscous loss)
  fluidic.py    laminar incompressible (Hagen-Poiseuille)

Add a backend = add one file + one row in lowering.LOWER.
"""
