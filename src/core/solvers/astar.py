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
  Pruning           : AC-3 chỉ chạy lúc khởi đầu (init).
                      Khi expand node dùng forward checking nhẹ (≠ row/col)
                      để tạo nhiều snapshot hơn cho visualization.
"""

from __future__ import annotations

import heapq
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from .base_solver import BaseSolver, SolverFactory
from ..utils.metrics import GLOBAL_METRICS_STORE
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

    _counter: int = 0

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

        self.record_snapshots: bool = True

    # ------------------------------------------------------------------
    # Public API — format đồng nhất với BacktrackingSolver
    # ------------------------------------------------------------------

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
            self.metrics.stop()                    # stop() TRƯỚC
            GLOBAL_METRICS_STORE.add(self.metrics)

        return {                                    # return SAU finally
            "status": status,
            "solution": solution,
            "metrics": self.metrics.to_dict(),     # lúc này elapsed đã có
        }

    # ------------------------------------------------------------------
    # Core A* loop
    # ------------------------------------------------------------------

    def _run(self) -> Optional[List[List[int]]]:
        n = self._n
        m = self.metrics

        init_domains = build_initial_domains(n, self._initial_grid)

        # AC-3 chỉ chạy MỘT LẦN ở đây — không chạy lại khi expand node
        init_domains = run_ac3(init_domains, n, self._h_con, self._v_con)

        if init_domains is None:
            return None

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

            if node.is_goal():
                return domains_to_grid(node.domains, n)

            sig = _signature(node.domains)
            if sig in closed:
                continue
            closed.add(sig)

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

            cell = select_mrv_cell(node.domains)
            if cell is None:
                continue

            r, c = cell

            for value in lcv_order(cell, node.domains, n, self._h_con, self._v_con):
                m.inc_constraint_checks()

                child_domains = deepcopy(node.domains)
                child_domains[cell] = {value}
                m.inc_assignments()

                # --------------------------------------------------------
                # THAY ĐỔI: dùng forward checking nhẹ thay vì run_ac3()
                # → solver đi vào nhiều nhánh hơn → nhiều snapshot hơn
                # --------------------------------------------------------
                child_domains = _forward_check(child_domains, cell, n)

                if child_domains is None:
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

        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _forward_check(domains: Domain, assigned: Cell, n: int) -> Optional[Domain]:
    """
    Forward checking nhẹ sau khi gán một cell:
    - Xóa giá trị vừa gán khỏi domain các ô cùng hàng / cùng cột (≠ constraint).
    - KHÔNG propagate tiếp (không dùng queue như AC-3).

    Ưu điểm cho visualization: solver sẽ khám phá nhiều node hơn vì
    inequality constraint không được tự động propagate — phát hiện
    mâu thuẫn muộn hơn, tạo ra nhiều bước trung gian để hiển thị.

    Trả về None nếu có domain nào rỗng (prune nhánh).
    """
    r, c = assigned
    (val,) = domains[assigned]

    peers = (
        [(r, col) for col in range(n) if col != c] +
        [(row, c) for row in range(n) if row != r]
    )

    for peer in peers:
        if val in domains[peer]:
            domains[peer].discard(val)
            if not domains[peer]:
                return None

    return domains


def _signature(domains: Domain) -> frozenset:
    """Hashable representation of the current partial assignment."""
    return frozenset(
        (cell, next(iter(vals)))
        for cell, vals in domains.items()
        if len(vals) == 1
    )


__all__ = ["AStarSolver"]