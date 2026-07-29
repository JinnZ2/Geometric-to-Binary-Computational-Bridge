"""
NEG-4 -- dependency re-rooting for a physical archive network.

An archive is not a pile of claims. It is a directed graph of what rests
on what, and the interesting operations are not "insert" and "delete" but
"add something at the edge" and "move the base".

EDGE SEMANTICS
    ``b in dep[a]``   means   "a rests on b"
    foundations       = nodes with no outgoing dependency (the base)
    center            = the node the archive is currently rooted at

THE TWO EVIDENCE OPERATIONS

    radiate     add(new, rests_on=[existing])       cheap, local, O(1)
    recenter    reverse every edge on paths v -> center

NEG-4 is the claim that these two are the *only* moves evidence can make on
a well-formed archive. New evidence either hangs off what is already there,
or it changes which claim the rest is founded on. There is no third thing.

THREE CONSEQUENCES, EACH SEPARATELY FALSIFIABLE

NEG-9  A cycle appearing after an inversion is not a bug in the graph, it
       is a CONTRADICTION DETECTOR. Two claims cannot both be foundational
       to each other, so if inverting one edge closes a loop, at least one
       of the claims on that loop is wrong. :meth:`Archive.invert` rolls
       back and hands you the cycle rather than storing an impossible
       state.

NEG-10 Recentering cost is the number of edges reversed, which is the path
       length from the new center to the old one. An archive that recenters
       often is therefore under selection pressure toward shallow, wide
       topology. :meth:`Archive.depth` and :meth:`Archive.mean_recenter_cost`
       make that measurable.

NEG-11 The validation gate is load-bearing. An unconfirmed claim cannot
       become the base no matter how convenient it is, because everything
       else will then rest on it. ``v_max_gap`` is the mechanical form of
       that rule.

Stdlib only. Phone-buildable.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

__all__ = ["Archive"]

Node = object


class Archive:
    """A dependency graph of claims, rooted at one of them.

    Attributes
    ----------
    dep : dict
        ``node -> set of nodes it rests on``.
    validated : dict
        ``node -> epoch of last EMPIRICAL confirmation``. Not the epoch it
        was written down, not the epoch it was last cited. Confirmed.
    center : node or None
        The node the archive is currently rooted at.
    history : list of dict
        One record per successful recenter, for the NEG-10 cost series.
    """

    def __init__(self) -> None:
        self.dep: Dict[Node, Set[Node]] = {}
        self.validated: Dict[Node, int] = {}
        self.center: Optional[Node] = None
        self.history: List[Dict[str, object]] = []

    # ---- construction ---------------------------------------------------

    def add(self, node: Node, rests_on: Iterable[Node] = (),
            validated: int = 0) -> None:
        """Seed or update a node.

        Parents that do not exist yet are created with validation epoch 0 --
        an unconfirmed placeholder, which is the honest default for a claim
        nobody has checked.

        Re-adding an existing node merges the new dependencies and
        *overwrites* its validation epoch, which is what re-confirming a
        claim should do.
        """
        parents = set(rests_on)
        if node in parents:
            raise ValueError(f"{node!r} cannot rest on itself")
        self.dep.setdefault(node, set()).update(parents)
        for p in parents:
            self.dep.setdefault(p, set())
            self.validated.setdefault(p, 0)
        self.validated[node] = validated
        if self.center is None:
            self.center = node

    def radiate(self, node: Node, rests_on: Sequence[Node],
                validated: int = 0) -> Dict[str, object]:
        """Evidence operation 1: attach a new claim to existing ones.

        Unlike :meth:`add`, every parent must already be in the archive.
        That restriction is what makes radiating cheap and local -- it can
        never change the base, never reverse an edge, and never need a
        cycle check, because a genuinely new node has nothing pointing at
        it yet.

        Returns the node's distance from the base, which is the quantity
        NEG-10 says should stay small in a frequently-recentered archive.
        """
        if not rests_on:
            raise ValueError("radiating requires at least one existing parent; "
                             "use add() to seed a foundation")
        missing = [p for p in rests_on if p not in self.dep]
        if missing:
            raise KeyError(f"unknown parents: {missing!r}")
        if node in self.dep:
            raise ValueError(f"{node!r} already exists; radiate adds new claims")

        self.add(node, rests_on, validated)
        return {"status": "OK", "node": node, "depth": self.depth_of(node)}

    def foundations(self) -> Set[Node]:
        """Nodes nothing rests on -- the base the archive stands on."""
        return {n for n, d in self.dep.items() if not d}

    # ---- integrity ------------------------------------------------------

    def _cycle(self) -> Optional[List[Node]]:
        """Three-colour DFS. Returns a cycle as a node list, or ``None``.

        Iterative rather than recursive: the recursive form's depth is the
        archive's depth, which is fine at a few hundred nodes and is not
        fine on a phone with a small stack. Neighbours are visited in
        sorted order so that a reported contradiction is reproducible
        across runs -- set iteration order is not stable for strings.
        """
        WHITE, GREY, BLACK = 0, 1, 2
        color = {n: WHITE for n in self.dep}

        for root in sorted(self.dep, key=repr):
            if color[root] != WHITE:
                continue
            path: List[Node] = [root]
            color[root] = GREY
            stack: List[Tuple[Node, Iterable[Node]]] = [
                (root, iter(sorted(self.dep[root], key=repr)))
            ]
            while stack:
                node, neighbours = stack[-1]
                descended = False
                for m in neighbours:
                    if color[m] == GREY:
                        return path[path.index(m):] + [m]
                    if color[m] == WHITE:
                        color[m] = GREY
                        path.append(m)
                        stack.append((m, iter(sorted(self.dep[m], key=repr))))
                        descended = True
                        break
                if not descended:
                    color[node] = BLACK
                    path.pop()
                    stack.pop()
        return None

    def _edges_on_paths(self, src: Node, dst: Node) -> Set[Tuple[Node, Node]]:
        """Edges lying on *some* path ``src -> dst``.

        A node qualifies iff it is reachable from ``src`` and can reach
        ``dst``; an edge qualifies iff both ends do. Returns the empty set
        when ``dst`` is unreachable, which is the correct answer and not an
        error -- it means there is nothing to reverse.
        """
        forward: Set[Node] = set()
        stack = [src]
        while stack:
            n = stack.pop()
            if n in forward:
                continue
            forward.add(n)
            stack.extend(self.dep[n])
        if dst not in forward:
            return set()

        reverse: Dict[Node, Set[Node]] = {n: set() for n in self.dep}
        for a, parents in self.dep.items():
            for b in parents:
                reverse[b].add(a)

        backward: Set[Node] = set()
        stack = [dst]
        while stack:
            n = stack.pop()
            if n in backward:
                continue
            backward.add(n)
            stack.extend(reverse[n])

        on_path = forward & backward
        return {(a, b) for a in on_path for b in self.dep[a] if b in on_path}

    # ---- topology, for NEG-10 -------------------------------------------

    def depth_of(self, node: Node) -> int:
        """Longest path from ``node`` down to a foundation, in edges.

        Zero for a foundation. Assumes acyclicity, which every mutating
        method here maintains.
        """
        if node not in self.dep:
            raise KeyError(node)
        memo: Dict[Node, int] = {}
        # Post-order traversal with an explicit stack; no recursion.
        stack: List[Tuple[Node, bool]] = [(node, False)]
        while stack:
            n, expanded = stack.pop()
            if n in memo:
                continue
            if expanded:
                memo[n] = 1 + max((memo[p] for p in self.dep[n]), default=-1)
            else:
                stack.append((n, True))
                for p in self.dep[n]:
                    if p not in memo:
                        stack.append((p, False))
        return memo[node]

    def depth(self) -> int:
        """Depth of the deepest node: how far the archive is from its base."""
        if not self.dep:
            return 0
        return max(self.depth_of(n) for n in self.dep)

    def topology(self) -> Dict[str, float]:
        """Shape metrics for the NEG-10 falsifier.

        ``depth`` is the longest chain, ``width`` the largest number of
        nodes at any one distance from the base, and ``aspect`` their ratio.
        NEG-10 predicts aspect falls over the life of an archive that
        recenters often.
        """
        if not self.dep:
            return {"depth": 0.0, "width": 0.0, "aspect": 0.0, "nodes": 0.0}
        levels: Dict[int, int] = {}
        for n in self.dep:
            d = self.depth_of(n)
            levels[d] = levels.get(d, 0) + 1
        depth = max(levels)
        width = max(levels.values())
        return {
            "depth": float(depth),
            "width": float(width),
            "aspect": depth / width,
            "nodes": float(len(self.dep)),
        }

    def recenter_cost(self, v: Node) -> int:
        """Edges that recentering on ``v`` would reverse, without doing it."""
        if v not in self.dep:
            raise KeyError(v)
        if self.center is None:
            return 0
        return len(self._edges_on_paths(v, self.center))

    def mean_recenter_cost(self) -> Optional[float]:
        """Mean cost of the recenters performed so far, or ``None``."""
        if not self.history:
            return None
        return sum(int(h["work"]) for h in self.history) / len(self.history)

    # ---- validation, for NEG-11 -----------------------------------------

    def validation_gap(self, node: Node, now: int) -> int:
        """Epochs since ``node`` was last empirically confirmed."""
        if node not in self.dep:
            raise KeyError(node)
        return now - self.validated.get(node, 0)

    def base_validation_gap(self, now: int) -> Optional[int]:
        """Worst validation gap among the current foundations.

        This is the NEG-11 measurement: the claim is that an archive whose
        base carries a large gap degrades faster than one whose base is
        confirmed. Returns ``None`` for an empty archive.
        """
        base = self.foundations()
        if not base:
            return None
        return max(self.validation_gap(n, now) for n in base)

    # ---- the two evidence operations ------------------------------------

    def invert(self, a: Node, b: Node) -> Dict[str, object]:
        """Evidence says ``b`` rests on ``a``, not the reverse.

        A ``CONTRADICTION`` return is the useful case, not the failure case
        (NEG-9). It means the archive would now contain two mutually
        foundational claims, so at least one of them is wrong. The archive
        is rolled back and the cycle is handed to you to adjudicate;
        storing the cycle instead would be storing a known impossibility.
        """
        if b not in self.dep.get(a, ()):
            return {"status": "NO_EDGE"}

        self.dep[a].discard(b)
        self.dep[b].add(a)

        cycle = self._cycle()
        if cycle:
            self.dep[b].discard(a)
            self.dep[a].add(b)
            return {"status": "CONTRADICTION", "cycle": cycle}
        return {"status": "OK", "edge": (b, a)}

    def recenter(self, v: Node, now: int = 0,
                 v_max_gap: Optional[int] = None) -> Dict[str, object]:
        """Evidence operation 2: re-root the archive at ``v``.

        Parameters
        ----------
        v : node
            The new center.
        now : int
            Current epoch, for the validation gate.
        v_max_gap : int, optional
            Refuse to found the archive on a node whose validation gap
            exceeds this (NEG-11). An unconfirmed claim cannot become the
            base -- everything else would then rest on it, and the archive
            would be no better confirmed than that one node. This is the
            mechanical form of the consensus gate, and passing ``None``
            disables it, which is a decision the caller should have to make
            explicitly.

        Returns
        -------
        dict
            ``OK`` with the work done and the new foundations, ``V_GATE``
            if the validation gate refused, or ``CONTRADICTION`` with the
            offending cycle.
        """
        if v not in self.dep:
            raise KeyError(v)
        if self.center is None:
            self.center = v
            return {"status": "OK", "work": 0, "from": None, "to": v,
                    "foundations": sorted(self.foundations(), key=repr)}

        gap = self.validation_gap(v, now)
        if v_max_gap is not None and gap > v_max_gap:
            return {"status": "V_GATE", "gap": gap, "limit": v_max_gap}

        edges = self._edges_on_paths(v, self.center)
        snapshot = {n: set(d) for n, d in self.dep.items()}
        for a, b in edges:
            self.dep[a].discard(b)
            self.dep[b].add(a)

        cycle = self._cycle()
        if cycle:
            self.dep = snapshot
            return {"status": "CONTRADICTION", "cycle": cycle}

        old, self.center = self.center, v
        result = {
            "status": "OK",
            "work": len(edges),
            "from": old,
            "to": v,
            "foundations": sorted(self.foundations(), key=repr),
        }
        self.history.append({"from": old, "to": v, "work": len(edges),
                             "epoch": now, "depth": self.depth()})
        return result


if __name__ == "__main__":
    a = Archive()
    a.add("T1", validated=1850)                     # first triangle
    a.add("T2", rests_on=["T1"], validated=1900)
    a.add("T3", rests_on=["T2"], validated=1960)
    a.radiate("T4", rests_on=["T2"], validated=2010)

    print("NEG-4: the two evidence operations")
    print(f"  foundations: {sorted(a.foundations())}   depth {a.depth()}")
    print(f"  recenter on T4 would cost {a.recenter_cost('T4')} edges")
    print(f"  {a.recenter('T4', now=2026, v_max_gap=90)}")

    print("\nNEG-11: the validation gate")
    print(f"  {a.recenter('T1', now=2026, v_max_gap=90)}")
    print("  T1 last confirmed 1850. It cannot be re-promoted to base on "
          "memory alone.")

    print("\nNEG-9: inversion as a contradiction detector")
    b = Archive()
    b.add("ground", validated=2020)
    b.add("mid", rests_on=["ground"], validated=2020)
    b.add("top", rests_on=["mid", "ground"], validated=2020)
    outcome = b.invert("top", "ground")             # claim ground rests on top
    print(f"  invert(top, ground) -> {outcome['status']}")
    print(f"  cycle: {outcome.get('cycle')}")
    print(f"  archive unchanged: {sorted(b.dep['top'])}")

    print("\nNEG-10: cost and shape")
    deep, wide = Archive(), Archive()
    deep.add("d0", validated=2020)
    for i in range(1, 8):
        deep.radiate(f"d{i}", rests_on=[f"d{i-1}"], validated=2020)
    wide.add("w0", validated=2020)
    for i in range(1, 8):
        wide.radiate(f"w{i}", rests_on=["w0"], validated=2020)
    for name, arc, leaf in (("deep", deep, "d7"), ("wide", wide, "w7")):
        shape = arc.topology()
        print(f"  {name}: depth {shape['depth']:.0f} width {shape['width']:.0f} "
              f"aspect {shape['aspect']:.2f}  "
              f"recenter cost {arc.recenter_cost(leaf)}")
