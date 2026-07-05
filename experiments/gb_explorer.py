#!/usr/bin/env python3
# gb_explorer.py — CC0
# Geometric-to-Binary Computational Bridge — Exploration Playground
# stdlib only, no cloud dependency
#
# Tree-based exploration: multiple-choice branching, backtrack, fork,
# annotate, and automated experiment suggestion over the bridge's
# encoding/operation space.
#
# Two encoding schemes are registered:
#   blade_bits / coord_binary  — toy placeholders (as originally sketched),
#                                useful for trying the mechanics risk-free.
#   octahedral_state           — wired to the REAL bridge: GEIS's
#                                OctahedralState (GEIS/octahedral_state.py),
#                                silicon's actual 8-vertex sp3 coordination,
#                                3 bits per unit. Not a placeholder.
#
# The octahedral_invert operation is the real bridge's own
# OctahedralState.invert() (i -> 7-i). The demo below runs the same
# "detect a homomorphism" walkthrough as the design sketch, but on the
# real encoding: it checks whether geometric inversion equals bitwise
# complement, which is an exact identity for 3-bit values (7-i == i^0b111
# for every i in 0..7), not an approximation.
#
# REFUTATION_PROTOCOL: if a suggested branch's "interesting" flag turns
# out to be a coincidence of the toy encodings rather than a real
# invariant, that's a valid (and reportable) outcome of exploration —
# not a reason to quietly drop the branch.

import copy
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from GEIS.octahedral_state import OctahedralState   # noqa: E402


# ----------------------------------------------------------------------
# Core data structures
# ----------------------------------------------------------------------

@dataclass
class BranchState:
    """Holds the current configuration and data of an exploration branch."""
    encoding: str = ""               # name of current encoding scheme
    data: Any = None                 # current bits, under the active encoding
    history: List[str] = field(default_factory=list)  # human-readable history
    params: Dict[str, Any] = field(default_factory=dict)

    def clone(self) -> "BranchState":
        return BranchState(
            encoding=self.encoding,
            data=copy.deepcopy(self.data),
            history=self.history.copy(),
            params=copy.deepcopy(self.params)
        )


class TreeNode:
    """A node in the exploration tree."""
    def __init__(self, state: BranchState, choice: str = "root",
                 parent: Optional["TreeNode"] = None):
        self.id = str(uuid.uuid4())[:8]
        self.state = state
        self.choice = choice            # description of the choice that led here
        self.annotations: List[str] = []
        self.parent = parent
        self.children: List["TreeNode"] = []

    def add_child(self, child: "TreeNode"):
        child.parent = self
        self.children.append(child)

    def to_dict(self) -> dict:
        """Recursive serialisation (no circular refs)."""
        return {
            "id": self.id,
            "choice": self.choice,
            "annotations": self.annotations,
            "state": {
                "encoding": self.state.encoding,
                "data": str(self.state.data),  # simplified; extend as needed
                "history": self.state.history,
                "params": self.state.params
            },
            "children": [child.to_dict() for child in self.children]
        }

    @classmethod
    def from_dict(cls, d: dict, parent: Optional["TreeNode"] = None) -> "TreeNode":
        state = BranchState(
            encoding=d["state"]["encoding"],
            data=d["state"]["data"],  # you may need custom deserialisation
            history=d["state"]["history"],
            params=d["state"]["params"]
        )
        node = cls(state, d["choice"], parent)
        node.id = d["id"]
        node.annotations = d["annotations"]
        for child_dict in d["children"]:
            child = cls.from_dict(child_dict, parent=node)
            node.children.append(child)
        return node


# ----------------------------------------------------------------------
# Abstract encoding & operation interfaces
# ----------------------------------------------------------------------

class EncodingScheme:
    """Base class for a geometric-to-binary encoding."""
    name: str = "base"

    def encode(self, mv: Any) -> Any: raise NotImplementedError
    def decode(self, bits: Any) -> Any: raise NotImplementedError


class Operation:
    """Base class for a binary/geometric operation."""
    name: str = "base_op"

    def apply(self, a: Any, b: Any, encoding: EncodingScheme = None) -> Any:
        raise NotImplementedError


# ----------------------------------------------------------------------
# Toy examples — safe to experiment with, not tied to any real bridge.
# ----------------------------------------------------------------------

class BladeBitEncoding(EncodingScheme):
    """Direct blade bits: coefficient > 0.5 -> bit 1."""
    name = "blade_bits"

    def encode(self, mv):
        # Assume mv is a list/array of coefficients [scalar, e1, e2, e12]
        bits = 0
        for i, coeff in enumerate(mv):
            if abs(coeff) > 0.5:
                bits |= (1 << i)
        return bits

    def decode(self, bits):
        # Convert back to a coefficient list (GF(2) style, all ones)
        return [1.0 if (bits >> i) & 1 else 0.0 for i in range(4)]


class CoordinateBinaryEncoding(EncodingScheme):
    """Encode a point (x,y) as two 8-bit fixed-point coordinates packed."""
    name = "coord_binary"

    def encode(self, point):
        # point is a tuple (x, y) in [-1,1] mapped to 0..255
        x_byte = int((point[0] + 1) / 2 * 255)
        y_byte = int((point[1] + 1) / 2 * 255)
        return (x_byte << 8) | y_byte

    def decode(self, bits):
        x = ((bits >> 8) & 0xFF) / 255.0 * 2 - 1
        y = (bits & 0xFF) / 255.0 * 2 - 1
        return (x, y)


class BitwiseXOR(Operation):
    """Binary XOR, returns integer."""
    name = "XOR"

    def apply(self, a, b, encoding=None):
        return a ^ b


class GeometricProduct(Operation):
    """Placeholder for actual GA product."""
    name = "geometric_product"

    def apply(self, a, b, encoding=None):
        # Not a real geometric-algebra product — a dummy per-component sum,
        # standing in for whatever GA library backend you wire in later.
        return [a[i] + b[i] for i in range(min(len(a), len(b)))]


# ----------------------------------------------------------------------
# Real bridge — wired to GEIS/octahedral_state.py, not a placeholder.
# ----------------------------------------------------------------------

class OctahedralBladeEncoding(EncodingScheme):
    """The repo's actual bridge: silicon's 8-vertex sp3 coordination,
    3 bits per unit (GEIS.octahedral_state.OctahedralState)."""
    name = "octahedral_state"

    def encode(self, mv):
        # mv: vertex index 0..7, or an OctahedralState
        state = mv if isinstance(mv, OctahedralState) else OctahedralState(int(mv) % 8)
        return int(state.to_binary(), 2)

    def decode(self, bits):
        return OctahedralState.from_binary(format(bits & 0b111, "03b"))


class OctahedralInvert(Operation):
    """The real bridge's own inversion: OctahedralState.invert(), i -> 7-i.
    Unary — `b` is accepted for interface symmetry but ignored."""
    name = "octahedral_invert"

    def apply(self, a, b=None, encoding=None):
        state = a if isinstance(a, OctahedralState) else OctahedralState(a)
        return int(state.invert().to_binary(), 2)


# ----------------------------------------------------------------------
# Explorer engine
# ----------------------------------------------------------------------

class Explorer:
    """Manages the exploration tree with branching, backtracking, and suggestions."""

    def __init__(self):
        root_state = BranchState()
        self.root = TreeNode(root_state, "root")
        self.current = self.root
        self._encoding_registry = {
            "blade_bits": BladeBitEncoding(),
            "coord_binary": CoordinateBinaryEncoding(),
            "octahedral_state": OctahedralBladeEncoding(),
        }
        self._operation_registry = {
            "XOR": BitwiseXOR(),
            "geom_prod": GeometricProduct(),
            "octahedral_invert": OctahedralInvert(),
        }
        # A global list of all experiments ever suggested (for simplicity)
        self.all_suggestions = []

    # ---------- Tree navigation ----------
    def choices(self) -> List[str]:
        """Return a list of possible next actions based on current node state."""
        state = self.current.state
        options = []

        # Stage 1: Choose encoding if not set
        if not state.encoding:
            for name in self._encoding_registry:
                options.append(f"set_encoding:{name}")
        else:
            # Stage 2: Apply an operation on current data
            options.append("apply_operation:XOR")
            if state.encoding == "octahedral_state":
                options.append("apply_operation:octahedral_invert")
            else:
                options.append("apply_operation:geom_prod")
            # Stage 3: Decode result and compare
            options.append("decode_and_compare")
            # Stage 4: Annotate, fork, etc.
            options.append("annotate")
            options.append("fork_new_idea")
        return options

    def select(self, choice_str: str):
        """Execute a choice, create a child node, and move to it."""
        # Parse choice
        parts = choice_str.split(":", 1)
        action = parts[0]
        arg = parts[1] if len(parts) > 1 else None

        new_state = self.current.state.clone()
        new_state.history.append(choice_str)
        child = TreeNode(new_state, choice_str, parent=self.current)

        # Execute action on the new state
        if action == "set_encoding":
            new_state.encoding = arg
            enc = self._encoding_registry[arg]
            # Initialise with a default test value, ALREADY ENCODED — state.data
            # holds bits from here on, matching decode_and_compare's assumption
            # and the "bitwise ops act on bits" / "geometric ops, then encode" split.
            if arg == "blade_bits":
                new_state.data = enc.encode([1.0, 0.0, 0.0, 0.0])  # scalar 1
            elif arg == "coord_binary":
                new_state.data = enc.encode((0.0, 0.0))
            elif arg == "octahedral_state":
                new_state.data = enc.encode(5)  # vertex 5, arbitrary default
        elif action == "apply_operation":
            op_name = arg
            op = self._operation_registry[op_name]
            enc = self._encoding_registry[new_state.encoding]
            # For simplicity, we apply the operation with a hardcoded second
            # operand. In a real system you would ask for the second operand.
            if op_name == "XOR":
                second = 0b0100  # e2
                new_state.data = op.apply(new_state.data, second)
            elif op_name == "geom_prod":
                second = [0.0, 1.0, 0.0, 0.0]  # e1
                # Geometric product acts on the multivector, not raw bits —
                # decode, apply, then re-encode so state.data stays bits.
                current_mv = enc.decode(new_state.data)
                result_mv = op.apply(current_mv, second)
                new_state.data = enc.encode(result_mv)
            elif op_name == "octahedral_invert":
                new_state.data = op.apply(new_state.data)
        elif action == "decode_and_compare":
            enc = self._encoding_registry[new_state.encoding]
            decoded = enc.decode(new_state.data)
            # Store result as annotation
            child.annotations.append(f"Decoded: {decoded}")
            # Compare with something
            child.annotations.append("Comparison: (placeholder)")
        elif action == "annotate":
            child.annotations.append(arg if arg else "manual note")
        elif action == "fork_new_idea":
            # Fork creates a sibling with identical state but different label
            sibling = TreeNode(new_state, f"fork: {arg}", parent=self.current.parent)
            self.current.parent.add_child(sibling)
            # Move to the sibling
            self.current = sibling
            return

        self.current.add_child(child)
        self.current = child

    def backtrack(self, steps: int = 1):
        for _ in range(steps):
            if self.current.parent:
                self.current = self.current.parent

    def annotate(self, text: str):
        self.current.annotations.append(text)

    def fork(self, description: str = "alternative"):
        """Create a sibling of the current node (a new branch from the same parent)."""
        if self.current.parent is None:
            raise ValueError("Cannot fork root.")
        sibling = TreeNode(self.current.state.clone(), f"fork: {description}", parent=self.current.parent)
        self.current.parent.add_child(sibling)
        self.current = sibling

    def save_branch(self, filepath: str):
        tree_dict = self.root.to_dict()
        with open(filepath, 'w') as f:
            json.dump(tree_dict, f, indent=2)

    def load_branch(self, filepath: str):
        with open(filepath) as f:
            tree_dict = json.load(f)
        self.root = TreeNode.from_dict(tree_dict)
        # Reset current to root
        self.current = self.root

    def compare_with(self, other_branch_name: str):
        """Dummy comparison that just prints the annotation."""
        print(f"Comparing current branch with {other_branch_name}: (not implemented)")

    def suggest_experiments(self) -> List[str]:
        """Generate possible next experiments from the current node."""
        suggestions = []
        state = self.current.state
        if state.encoding:
            # Suggest trying all operations not yet applied
            for op_name in self._operation_registry:
                suggestions.append(f"Try operation {op_name} on current data")
            # Suggest varying bit order, threshold, etc.
            suggestions.append("Vary bit ordering (LSB vs MSB)")
            suggestions.append("Change threshold for blade bits")
            suggestions.append("Extend to 3D and test")
        else:
            suggestions.append("First set an encoding scheme")
        self.all_suggestions.extend(suggestions)
        return suggestions


# ----------------------------------------------------------------------
# Demo if run directly: toy walkthrough, then the real-bridge walkthrough.
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("Toy walkthrough (blade_bits placeholder)")
    print("=" * 60)
    ex = Explorer()
    print("Initial choices:", ex.choices())
    ex.select("set_encoding:blade_bits")
    print("After encoding choice, state:", ex.current.state)
    print("New choices:", ex.choices())
    ex.select("apply_operation:XOR")
    print("After XOR, data bits:", bin(ex.current.state.data))
    ex.select("decode_and_compare")
    print("Annotations:", ex.current.annotations)
    ex.annotate("XOR gave a mix of e2 and e12 bits — not a clean homomorphism here")
    print("Suggested experiments:", ex.suggest_experiments())

    print("\n" + "=" * 60)
    print("Real-bridge walkthrough (GEIS OctahedralState)")
    print("=" * 60)
    real = Explorer()
    real.select("set_encoding:octahedral_state")
    print(f"Vertex 5 encoded: {bin(real.current.state.data)} "
          f"({real.current.state.data})")
    real.select("apply_operation:octahedral_invert")
    inverted = real.current.state.data
    print(f"OctahedralState.invert() result: {bin(inverted)} ({inverted})")
    xor_check = 5 ^ 0b111
    print(f"Bitwise complement (5 XOR 0b111): {bin(xor_check)} ({xor_check})")
    if inverted == xor_check:
        real.annotate(
            "Homomorphism CONFIRMED: octahedral inversion (i -> 7-i) equals "
            "bitwise complement (i XOR 0b111) — exact for all 8 vertices, "
            "not a coincidence of this one input (one's-complement identity "
            "in 3-bit space: (2^3 - 1) - i == i XOR 0b111)."
        )
    else:
        real.annotate("No homomorphism found for this input — reported as-is.")
    print("Annotations:", real.current.annotations)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "exploration_tree.json")
    real.save_branch(out_path)
    print(f"\nTree saved to {out_path}")
