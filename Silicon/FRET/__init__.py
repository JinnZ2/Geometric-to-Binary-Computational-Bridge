"""Silicon/FRET — FRET engineering stack.

This subpackage contains CLI tooling and simulation modules that are
intentionally run from inside the ``Silicon/FRET`` directory (see
``AI_CONTEXT.md``) — the imports inside ``cli.py`` are flat, not
package-qualified. This ``__init__`` exists only so package-style
imports from outside still resolve; it does not re-export any
submodules.
"""
