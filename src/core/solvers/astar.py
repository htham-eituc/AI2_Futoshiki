"""
A* Search Solver for Futoshiki.

Inherits from BaseSolver. Registered as "astar" in SolverFactory.

Algorithm (matches the report):
  f(s) = g(s) + h(s)
    g(s) = number of assigned cells
    h(s) = |U| unassigned cells after AC-3,
           or inf if AC-3 finds an empty domain

  Variable ordering : MRV  (Minimum Remaining Values)
  Value ordering    : LCV  (Least Constraining Value)
  Pruning           : AC-3 run before inserting each successor into OPEN

Input (via AlgorithmAdapter.to_astar()):
    {
        "initial_grid"  : List[List[int]],   # N×N, 0 = empty
        "h_constraints" : List[List[int]],   # N × (N-1)
        "v_constraints" : List[List[int]],   # (N-1) × N
        "grid_size"     : int
    }

Output of solve():
    {
        "status"   : "unique" | "none",
        "solution" : List[List[int]] | None,
        "metrics"  : SolverMetrics,
    }
"""

from __future__ import annotations

import heapq
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from .base_solver import BaseSolver, SolverFactory
from ..utils.metrics import SolverMetrics
from ..heuristics.ac3 import (
    Cell,
    Domain,
    build_initial_domains,
    compute_heuristic,
    domains_to_grid,
    lcv_order,
    run_ac3,
    select_mrv_cell,
)


# ---------------------------------------------------------------------------
# Internal node
# ---------------------------------------------------------------------------

class _Node:
    """
    A* search node.

    f = g + h  where:
      g = assigned cells (depth)
      h = unassigned cells remaining (or inf if infeasible)
    """

    _counter: int = 0  # global tie-breaker so heapq never compares domains

    __slots__ = ("domains", "g", "h", "f", "grid", "_id")

    def __init__(self, domains: Domain, g: int, h: float, grid: List[List[int]]) -> None:
        self.domains = domains
        self.g = g
        self.h = h
        self.f = g + h
        self.grid = grid
        _Node._counter += 1
        self._id = _Node._counter

    def __lt__(self, other: "_Node") -> bool:
        return (self.f, self._id) < (other.f, other._id)

    def is_goal(self) -> bool:
        return all(len(v) == 1 for v in self.domains.values())


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

@SolverFactory.register("astar")
class AStarSolver(BaseSolver):
    """A* search solver for Futoshiki."""

    def __init__(self, problem: Dict[str, Any], *, name: str = "A*") -> None:
        super().__init__(problem, name=name)
        self._n: int = problem["grid_size"]
        self._initial_grid: List[List[int]] = problem["initial_grid"]
        self._h_con: List[List[int]] = problem["h_constraints"]
        self._v_con: List[List[int]] = problem["v_constraints"]

        # Set to False when running benchmarks to avoid memory overhead
        self.record_snapshots: bool = True

    # ------------------------------------------------------------------
    # Public API (matches BaseSolver contract)
    # ------------------------------------------------------------------

    def solve(self) -> Dict[str, Any]:
        self.metrics.start()

        solution = self._run()

        self.metrics.stop()

        if solution is not None:
            self.metrics.mark_solved(True)
            self.metrics.set_solution_depth(self._n * self._n)
        else:
            self.metrics.mark_solved(False)

        return {
            "status": "unique" if solution is not None else "none",
            "solution": solution,
            "metrics": self.metrics,
        }

    # ------------------------------------------------------------------
    # Core A* loop
    # ------------------------------------------------------------------

    def _run(self) -> Optional[List[List[int]]]:
        n = self._n
        m = self.metrics  # shorthand

        # Build and AC-3 the initial state
        init_domains = build_initial_domains(n, self._initial_grid)
        init_domains = run_ac3(init_domains, n, self._h_con, self._v_con)

        if init_domains is None:
            return None  # Initial puzzle already infeasible

        h0 = compute_heuristic(init_domains)
        g0 = sum(1 for v in init_domains.values() if len(v) == 1)

        root = _Node(
            domains=init_domains,
            g=g0,
            h=h0,
            grid=domains_to_grid(init_domains, n),
        )

        # OPEN: min-heap by f
        open_heap: List[_Node] = []
        heapq.heappush(open_heap, root)
        m.inc_nodes_generated()

        # CLOSED: frozenset of assigned (cell, value) pairs
        closed: set = set()

        step = 0

        while open_heap:
            m.set_frontier_size(len(open_heap))

            node = heapq.heappop(open_heap)
            m.inc_nodes_expanded()

            # Goal check
            if node.is_goal():
                return domains_to_grid(node.domains, n)

            # Duplicate detection
            sig = _signature(node.domains)
            if sig in closed:
                continue
            closed.add(sig)

            # Snapshot for GUI step-by-step replay
            if self.record_snapshots:
                m.add_extra(
                    f"snap_{step}",
                    {
                        "step": step,
                        "grid": node.grid,
                        "label": f"expand g={node.g} h={node.h:.0f} f={node.f:.0f}",
                    },
                )
            step += 1

            # MRV: choose next cell
            cell = select_mrv_cell(node.domains)
            if cell is None:
                continue  # should not reach here if goal check is correct

            r, c = cell

            # LCV: try values in least-constraining order
            for value in lcv_order(cell, node.domains, n, self._h_con, self._v_con):
                m.inc_constraint_checks()

                child_domains = deepcopy(node.domains)
                child_domains[cell] = {value}
                m.inc_assignments()

                # AC-3 on successor
                child_domains = run_ac3(child_domains, n, self._h_con, self._v_con)

                if child_domains is None:
                    # h = inf → prune
                    if self.record_snapshots:
                        m.add_extra(
                            f"snap_{step}",
                            {
                                "step": step,
                                "grid": node.grid,
                                "label": f"PRUNED ({r},{c})={value}",
                            },
                        )
                    step += 1
                    m.inc_backtracks()
                    continue

                child_sig = _signature(child_domains)
                if child_sig in closed:
                    continue

                h_child = compute_heuristic(child_domains)
                g_child = sum(1 for v in child_domains.values() if len(v) == 1)
                child_grid = domains_to_grid(child_domains, n)

                child_node = _Node(
                    domains=child_domains,
                    g=g_child,
                    h=h_child,
                    grid=child_grid,
                )

                heapq.heappush(open_heap, child_node)
                m.inc_nodes_generated()

                if self.record_snapshots:
                    m.add_extra(
                        f"snap_{step}",
                        {
                            "step": step,
                            "grid": child_grid,
                            "label": f"assign ({r},{c})={value} g={g_child} h={h_child:.0f}",
                        },
                    )
                step += 1

        return None  # OPEN exhausted


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _signature(domains: Domain) -> frozenset:
    """Hashable representation of the current partial assignment."""
    return frozenset(
        (cell, next(iter(vals)))
        for cell, vals in domains.items()
        if len(vals) == 1
    )