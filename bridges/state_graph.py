"""
State Graph Engine for Alternative-Computing Integration
========================================================

Dataflow graph that routes a single geometry input through multiple
interpretive manifolds (binary, ternary, stochastic, tensor-field)
without the paths interfering with each other.

This is the *branch-point architecture* described in the alternative
computing bridge spec: the geometry enters one port and fans out to
every interpreter that declares a dependency on it. Each path produces
its own representation; a merge node collects them at the end.

The graph is deliberately minimal — it is a scheduler, not a planner.
Topological resolution is done by repeated relaxation: each pass runs
every node whose inputs are already in state, until no more progress
is possible. This tolerates out-of-order ``add_node`` calls and lets
callers wire in custom interpreters without specifying an ordering.

Typical usage
-------------
>>> from bridges.state_graph import Node, StateGraph
>>> g = StateGraph()
>>> g.add_node(Node("double", lambda i, s: {"y": i["x"] * 2},
...                 inputs=["x"], outputs=["y"]))
>>> g.set_input("x", 3)
>>> g.run()["y"]
6
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


@dataclass
class Node:
    """
    One interpreter in the dataflow graph.

    Parameters
    ----------
    name
        Unique identifier used for bookkeeping and error messages.
    fn
        Callable ``fn(inputs_dict, full_state_dict) -> dict | Any``.
        If the return value is a dict it is merged into state;
        otherwise it is written to ``state[outputs[0]]``.
    inputs
        Keys that must exist in state before ``fn`` may fire.
    outputs
        Keys this node promises to produce. Used for readability and
        for the single-output fallback when ``fn`` returns a scalar.
    """

    name: str
    fn: Callable[[Dict[str, Any], Dict[str, Any]], Any]
    inputs: List[str]
    outputs: List[str]


class StateGraph:
    """
    A small, re-runnable dataflow graph.

    The graph does not build a DAG explicitly; it relies on data
    dependencies declared on each node. ``run()`` repeatedly scans
    the node set and fires every node whose inputs are currently
    available, stopping when every node has fired or when a full
    pass produces no progress (which raises ``RuntimeError``).
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.state: Dict[str, Any] = {}

    def add_node(self, node: Node) -> "StateGraph":
        if node.name in self.nodes:
            raise ValueError(f"Duplicate node name: {node.name!r}")
        self.nodes[node.name] = node
        return self

    def set_input(self, key: str, value: Any) -> "StateGraph":
        self.state[key] = value
        return self

    def reset(self) -> "StateGraph":
        """Forget all state while preserving the node topology."""
        self.state = {}
        return self

    def run(self) -> Dict[str, Any]:
        """
        Execute the graph until every node has fired.

        Returns the full state dictionary. Raises ``RuntimeError`` if
        any node's inputs are never satisfied — this usually means a
        missing ``set_input`` call or a circular dependency.
        """
        executed: set = set()

        while len(executed) < len(self.nodes):
            progress = False

            for name, node in self.nodes.items():
                if name in executed:
                    continue
                if not all(k in self.state for k in node.inputs):
                    continue

                inputs = {k: self.state[k] for k in node.inputs}
                result = node.fn(inputs, self.state)

                if isinstance(result, dict):
                    self.state.update(result)
                else:
                    if not node.outputs:
                        raise RuntimeError(
                            f"Node {name!r} returned non-dict but declares "
                            f"no outputs."
                        )
                    self.state[node.outputs[0]] = result

                executed.add(name)
                progress = True

            if not progress:
                unresolved = [n for n in self.nodes if n not in executed]
                raise RuntimeError(
                    f"Graph stalled: unresolved dependencies for nodes "
                    f"{unresolved}. Current state keys: "
                    f"{sorted(self.state.keys())}"
                )

        return self.state


# ---------------------------------------------------------------------------
# Pre-built node factories for the bridge pipeline
# ---------------------------------------------------------------------------

def geometry_to_binary_node(domain: str = "electric") -> Node:
    """
    Node that runs the existing binary encoder for a given domain.

    The node reads ``state["geometry"]`` and writes
    ``state["binary_encoding"]``.
    """

    def _fn(inputs: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        from bridges.encode_state import binary_encode

        return {"binary_encoding": binary_encode(inputs["geometry"], domain=domain)}

    return Node(
        name=f"{domain}_binary_path",
        fn=_fn,
        inputs=["geometry"],
        outputs=["binary_encoding"],
    )


def geometry_to_alternative_node(domain: str = "electric") -> Node:
    """
    Node that runs the ternary / stochastic / quantum interpreter
    for a given domain.

    Reads ``state["geometry"]`` and optional ``state["frequency_hz"]``;
    writes ``state["alt_diagnostic"]``.
    """

    def _fn(inputs: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        from bridges.encode_state import alternative_encode

        return {
            "alt_diagnostic": alternative_encode(
                inputs["geometry"],
                domain=domain,
                frequency_hz=state.get("frequency_hz"),
            )
        }

    return Node(
        name=f"{domain}_alternative_path",
        fn=_fn,
        inputs=["geometry"],
        outputs=["alt_diagnostic"],
    )


def merge_views_node() -> Node:
    """Node that bundles both paths into a single ``merged`` dict."""

    def _fn(inputs: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "merged": {
                "binary": state.get("binary_encoding"),
                "alternative": state.get("alt_diagnostic"),
            }
        }

    return Node(
        name="merge",
        fn=_fn,
        inputs=["binary_encoding", "alt_diagnostic"],
        outputs=["merged"],
    )


def build_dual_path_graph(domain: str = "electric") -> StateGraph:
    """
    Construct the canonical dual-path graph:

        geometry ──┬── binary encoder ──┐
                   │                    ├── merge
                   └── alt interpreter ─┘
    """
    graph = StateGraph()
    graph.add_node(geometry_to_binary_node(domain))
    graph.add_node(geometry_to_alternative_node(domain))
    graph.add_node(merge_views_node())
    return graph


__all__ = [
    "Node",
    "StateGraph",
    "geometry_to_binary_node",
    "geometry_to_alternative_node",
    "merge_views_node",
    "build_dual_path_graph",
]
