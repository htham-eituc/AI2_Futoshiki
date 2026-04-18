from __future__ import annotations

import heapq
from typing import Any, Dict, List, Optional, Tuple

from .base_solver import BaseSolver, SolverFactory
from ..problem.parser import FutoshikiData, AlgorithmAdapter
from ..utils.metrics import GLOBAL_METRICS_STORE
from ..heuristics.heuristics import (
    Cell,
    Domain,
    build_initial_domains,
    build_ineq_map,
    build_peers_map,
    compute_heuristic,
    domains_to_grid,
    forward_check_ineq,
    lcv_order_ineq,
    select_mrv_cell_ineq,
    shallow_copy_domains,
)                                                                              

class _Node:
    __slots__ = ("domains", "g", "h", "f", "grid", "_id")
    _counter: int = 0

    def __init__(self, domains: Domain, g: int, h: float, grid: List[List[int]]) -> None:
        self.domains = domains
        self.g       = g
        self.h       = h
        self.f       = g + h
        self.grid    = grid

        _Node._counter += 1
        self._id = _Node._counter

    def __lt__(self, other: "_Node") -> bool:
        return (self.f, self._id) < (other.f, other._id)

    def is_goal(self, n: int, ineq_map: Dict) -> bool:
        if not all(len(v) == 1 for v in self.domains.values()):
            return False

        grid = self.grid

        for i in range(n):
            row = [grid[i][c] for c in range(n)]
            col = [grid[r][i] for r in range(n)]
            if len(set(row)) != n or len(set(col)) != n:
                return False

        for cell, constraints in ineq_map.items():
            r, c     = cell
            cell_val = grid[r][c]
            for (nr, nc), sign in constraints:
                nb_val = grid[nr][nc]
                if sign == 1 and cell_val >= nb_val:
                    return False
                if sign == -1 and cell_val <= nb_val:
                    return False

        return True

@SolverFactory.register("astar")
class AStarSolver(BaseSolver):
    """A* search solver for Futoshiki."""

    def __init__(self, problem: Dict[str, Any], *, name: str = "A*") -> None:
        super().__init__(problem, name=name)

        if isinstance(problem, FutoshikiData):
            adapted = AlgorithmAdapter(problem).to_astar()

            self._n            = adapted["grid_size"]
            self._initial_grid = adapted["initial_grid"]
            self._h_con        = adapted["h_constraints"]
            self._v_con        = adapted["v_constraints"]

        elif isinstance(problem, dict):
            self._n            = problem["grid_size"]
            self._initial_grid = problem["initial_grid"]
            self._h_con        = problem["h_constraints"]
            self._v_con        = problem["v_constraints"]

        else:
            raise TypeError(
                f"AStarSolver expects FutoshikiData or dict, got {type(problem)}"
            )

        self._ineq_map  = build_ineq_map(self._n, self._h_con, self._v_con)
        self._peers_map = build_peers_map(self._n)

        self.record_snapshots: bool = True                                                             

    def solve(self) -> Dict[str, Any]:
        self.metrics.start()
        try:
            solution = self._run()
            if solution is not None:
                self.metrics.mark_solved(True)
                self.metrics.set_solution_depth(self._n * self._n)
                status = "unique"
            else:
                self.metrics.mark_solved(False)
                status = "none"
        finally:
            self.metrics.stop()
            GLOBAL_METRICS_STORE.add(self.metrics)

        return {
            "status":   status,
            "solution": solution,
            "metrics":  self.metrics.to_dict(),
        }

    def _run(self) -> Optional[List[List[int]]]:
        n          = self._n
        m          = self.metrics
        ineq_map   = self._ineq_map
        peers_map  = self._peers_map

        init_domains = build_initial_domains(n, self._initial_grid)
        h0 = compute_heuristic(init_domains)
        g0 = sum(1 for v in init_domains.values() if len(v) == 1)

        root = _Node(
            domains=init_domains,
            g=g0,
            h=h0,
            grid=domains_to_grid(init_domains, n),
        )

        open_heap: List[_Node] = []
        heapq.heappush(open_heap, root)
        m.inc_nodes_generated()

        closed: set = set()
        step = 0

        while open_heap:
            m.set_frontier_size(len(open_heap))

            node = heapq.heappop(open_heap)
            m.inc_nodes_expanded()

            if node.is_goal(n, ineq_map):
                return node.grid

            sig = _signature(node.domains)
            if sig in closed:
                continue
            closed.add(sig)

            if self.record_snapshots:
                m.add_extra(f"snap_{step}", {
                    "step":  step,
                    "grid":  node.grid,
                    "label": f"expand g={node.g} h={node.h:.0f} f={node.f:.0f}",
                })
            step += 1

            cell = select_mrv_cell_ineq(node.domains, ineq_map)
            if cell is None:
                continue

            r, c    = cell
            g_child = node.g + 1

                                                                            
            parent_domain_size = len(node.domains[cell])
            h_after_assign     = node.h - (parent_domain_size - 1)

            for value in lcv_order_ineq(cell, node.domains, n, ineq_map, peers_map):
                m.inc_constraint_checks()

                child_domains = shallow_copy_domains(node.domains)
                child_domains[cell] = {value}
                m.inc_assignments()

                child_domains, delta_h = forward_check_ineq(
                    child_domains, cell, n, ineq_map, peers_map
                )

                if child_domains is None:
                    if self.record_snapshots:
                        m.add_extra(f"snap_{step}", {
                            "step":  step,
                            "grid":  node.grid,
                            "label": f"PRUNED ({r},{c})={value}",
                        })
                    step += 1
                    m.inc_backtracks()
                    continue

                child_sig = _signature(child_domains)
                if child_sig in closed:
                    continue

                                                                  
                h_child    = h_after_assign + delta_h
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
                    m.add_extra(f"snap_{step}", {
                        "step":  step,
                        "grid":  child_grid,
                        "label": f"assign ({r},{c})={value} g={g_child} h={h_child:.0f}",
                    })
                step += 1

        return None                                                                  

def _signature(domains: Domain) -> frozenset:
    return frozenset(
        (cell, next(iter(vals)))
        for cell, vals in domains.items()
        if len(vals) == 1
    )


__all__ = ["AStarSolver"]