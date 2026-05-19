"""
fabrication/emit/

SubstrateIR -> physical fab artifact. Each emit_* returns BYTES or
TEXT that goes to a real machine.

Currently shipped:
  stl.py             3D-print / CNC artifact (mechanical, acoustic shells)
  svg_mask.py        laser-cut / photolitho mask (optical, fluidic)
  spice_acoustic.py  pre-fab simulation via electrical-acoustic analogy

Future (stubs commented in fabrication/__init__.py docstring):
  kicad_netlist.py   electrical -> PCB fab
  gcode.py           mechanical -> direct CNC
  coil_winding.py    magnetic -> winding schedule
  loom_pattern.py    woven -> jacquard / wire routing
"""
