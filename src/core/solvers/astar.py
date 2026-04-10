"""
A* Search Solver for Futoshiki.

Inherits from BaseSolver. Registered as "astar" in SolverFactory.

Algorithm:
  f(s) = g(s) + h2(s)
    g(s)  = number of assigned cells
    h2(s) = Σ (|domain(cell)| - 1)  — tổng kích thước domain dư
            = 0   iff goal
            = inf nếu có domain rỗng (nhánh không khả thi)

  Variable ordering : MRV  (Minimum Remaining Values)
  Value ordering    : LCV  (Least Constraining Value)
  Pruning           : Forward checking (≠ row/col) sau mỗi lần gán.
                      Không dùng AC-3.

Optimisations vs. original:
  1. compute_heuristic trả về inf sớm khi domain rỗng (đúng công thức h2).
  2. g và h tính incremental từ node cha — tránh scan O(N²) mỗi child.
  3. deepcopy thay bằng shallow_copy_domains (~5–10× nhanh hơn).
"""

from __future__ import annotations

import heapq
from typing import Any, Dict, List, Optional, Tuple

from .base_solver import BaseSolver, SolverFactory
from ..utils.metrics import GLOBAL_METRICS_STORE
from ..heuristics.heuristics import (
    Cell,
    Domain,
    build_initial_domains,
    compute_heuristic,
    domains_to_grid,
    lcv_order,
    select_mrv_cell,
    shallow_copy_domains,
)


# ---------------------------------------------------------------------------
# Internal node
# ---------------------------------------------------------------------------

class _Node:
    """
    A* search node.

    f = g + h2  where:
      g  = số cell đã gán (depth)
      h2 = Σ (|domain(cell)| - 1)
    """

    _counter: int = 0

    __slots__ = ("domains", "g", "h", "f", "grid", "_id")

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

    def is_goal(self) -> bool:
        return all(len(v) == 1 for v in self.domains.values())


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

@SolverFactory.register("astar")
class AStarSolver(BaseSolver):
    """A* search solver for Futoshiki (h2, no AC-3)."""

    def __init__(self, problem: Dict[str, Any], *, name: str = "A*") -> None:
        super().__init__(problem, name=name)
        self._n:            int              = problem["grid_size"]
        self._initial_grid: List[List[int]]  = problem["initial_grid"]
        self._h_con:        List[List[int]]  = problem["h_constraints"]
        self._v_con:        List[List[int]]  = problem["v_constraints"]

        self.record_snapshots: bool = True

    # ------------------------------------------------------------------
    # Public API
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
            self.metrics.stop()
            GLOBAL_METRICS_STORE.add(self.metrics)

        return {
            "status":   status,
            "solution": solution,
            "metrics":  self.metrics.to_dict(),
        }

    # ------------------------------------------------------------------
    # Core A* loop
    # ------------------------------------------------------------------

    def _run(self) -> Optional[List[List[int]]]:
        n = self._n
        m = self.metrics

        # Khởi tạo domain từ grid ban đầu — KHÔNG chạy AC-3
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
        step   = 0

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
                        "step":  step,
                        "grid":  node.grid,
                        "label": f"expand g={node.g} h={node.h:.0f} f={node.f:.0f}",
                    },
                )
            step += 1

            cell = select_mrv_cell(node.domains)
            if cell is None:
                continue

            r, c = cell

            # Kích thước domain của cell này ở node cha
            parent_domain_size = len(node.domains[cell])

            # Đóng góp của cell vào h cha: (parent_domain_size - 1)
            # Sau khi gán (domain → singleton): đóng góp = 0
            # → h giảm đúng (parent_domain_size - 1) trước forward check
            h_after_assign = node.h - (parent_domain_size - 1)

            # g tăng 1 vì cell này chưa được gán ở node cha
            g_child = node.g + 1

            for value in lcv_order(cell, node.domains, n, self._h_con, self._v_con):
                m.inc_constraint_checks()

                # --- Dùng shallow copy thay deepcopy: ~5–10× nhanh hơn ---
                child_domains = shallow_copy_domains(node.domains)
                child_domains[cell] = {value}
                m.inc_assignments()

                # Forward checking: loại value khỏi peer cùng hàng/cột
                # Trả về (domains_đã_cập_nhật, delta_h) hoặc (None, inf)
                child_domains, delta_h = _forward_check(child_domains, cell, n)

                if child_domains is None:
                    if self.record_snapshots:
                        m.add_extra(
                            f"snap_{step}",
                            {
                                "step":  step,
                                "grid":  node.grid,
                                "label": f"PRUNED ({r},{c})={value}",
                            },
                        )
                    step += 1
                    m.inc_backtracks()
                    continue

                child_sig = _signature(child_domains)
                if child_sig in closed:
                    continue

                # h incremental: h sau gán + delta từ forward check
                h_child = h_after_assign + delta_h

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
                            "step":  step,
                            "grid":  child_grid,
                            "label": (
                                f"assign ({r},{c})={value} "
                                f"g={g_child} h={h_child:.0f}"
                            ),
                        },
                    )
                step += 1

        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _forward_check(
    domains: Domain, assigned: Cell, n: int
) -> Tuple[Optional[Domain], float]:
    """
    Loại giá trị vừa gán khỏi domain các ô cùng hàng / cùng cột.
    Không propagate thêm (không phải AC-3).

    Trả về:
      (None, inf)           nếu có domain nào rỗng sau khi loại
      (domains, delta_h)    delta_h = số lần discard thành công (âm → h giảm)
    """
    r, c = assigned
    (val,) = domains[assigned]
    delta_h = 0

    peers = (
        [(r, col) for col in range(n) if col != c] +
        [(row, c)  for row in range(n) if row != r]
    )

    for peer in peers:
        if val in domains[peer]:
            domains[peer].discard(val)
            if not domains[peer]:
                return None, float("inf")
            delta_h -= 1   # mỗi lần discard, h2 giảm 1

    return domains, delta_h


def _signature(domains: Domain) -> frozenset:
    """Hashable snapshot của partial assignment hiện tại."""
    return frozenset(
        (cell, next(iter(vals)))
        for cell, vals in domains.items()
        if len(vals) == 1
    )


__all__ = ["AStarSolver"]