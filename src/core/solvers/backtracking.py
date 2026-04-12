from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base_solver import BaseSolver, SolverFactory
from ..utils.metrics import GLOBAL_METRICS_STORE

# Import your AC3 utilities
from ..heuristics.ac3 import (
    build_initial_domains,
    run_ac3,
    select_mrv_cell,
    lcv_order,
    domains_to_grid,
)


@SolverFactory.register("backtracking")
class BacktrackingSolver(BaseSolver):
    """
    Backtracking + MRV + LCV + AC-3 solver for Futoshiki.
    """

    def __init__(self, problem: Any, *, name: Optional[str] = None) -> None:
        super().__init__(problem, name=name or "backtracking")

        self.n = problem.size
        self.grid = [row[:] for row in problem.grid]
        self.h_constraints = problem.h_constraints
        self.v_constraints = problem.v_constraints

        self.solutions: List[List[List[int]]] = []

    def _is_valid_solution(self, grid):
        n = self.n

        # Row
        for row in grid:
            if sorted(row) != list(range(1, n+1)):
                return False

        # Column
        for c in range(n):
            col = [grid[r][c] for r in range(n)]
            if sorted(col) != list(range(1, n+1)):
                return False

        # Inequalities
        for r in range(n):
            for c in range(n - 1):
                con = self.h_constraints[r][c]
                if con == 1 and not (grid[r][c] < grid[r][c+1]):
                    return False
                if con == -1 and not (grid[r][c] > grid[r][c+1]):
                    return False

        for r in range(n - 1):
            for c in range(n):
                con = self.v_constraints[r][c]
                if con == 1 and not (grid[r][c] < grid[r+1][c]):
                    return False
                if con == -1 and not (grid[r][c] > grid[r+1][c]):
                    return False

        return True

    def _backtrack(self, domains, limit=2):
        if len(self.solutions) >= limit:
            return True

        # MRV selection
        cell = select_mrv_cell(domains)

        if cell is None:
            solution = domains_to_grid(domains, self.n)

            if self._is_valid_solution(solution):
                self.solutions.append(solution)

            return len(self.solutions) >= limit

        self.metrics.inc_nodes_expanded()

        # LCV ordering
        for value in lcv_order(
            cell, domains, self.n, self.h_constraints, self.v_constraints
        ):
            self.metrics.inc_nodes_generated()

            # Copy domains
            new_domains = {k: set(v) for k, v in domains.items()}

            # Assign value
            new_domains[cell] = {value}
            self.metrics.inc_assignments()

            # Run AC-3 (constraint propagation)
            pruned = run_ac3(
                new_domains,
                self.n,
                self.h_constraints,
                self.v_constraints,
            )

            # If inconsistency → skip
            if pruned is None:
                self.metrics.inc_backtracks()
                continue

            # Continue search
            if self._backtrack(pruned, limit):
                return True

            self.metrics.inc_backtracks()

        return False

    # ------------------------------------------------------------------
    # Solve entry
    # ------------------------------------------------------------------

    def solve(self) -> Dict[str, Any]:
        self.metrics.start()

        status = "none"
        solution = None

        try:
            # Build initial domains
            domains = build_initial_domains(self.n, self.grid)

            # Initial AC-3 propagation
            domains = run_ac3(
                domains,
                self.n,
                self.h_constraints,
                self.v_constraints,
            )

            if domains is None:
                self.metrics.mark_solved(False)
                return {
                    "status": "none",
                    "solution": None,
                    "metrics": self.metrics.to_dict(),
                }

            # Backtracking search
            self._backtrack(domains, limit=2)

            if len(self.solutions) == 0:
                status = "none"
                solution = None
                self.metrics.mark_solved(False)

            elif len(self.solutions) == 1:
                status = "unique"
                solution = self.solutions[0]
                self.metrics.mark_solved(True)
                self.metrics.set_solution_depth(self.n * self.n)

            else:
                status = "multiple"
                solution = self.solutions[0]
                self.metrics.mark_solved(True)

        finally:
            self.metrics.stop()
            GLOBAL_METRICS_STORE.add(self.metrics)

        return {
            "status": status,
            "solution": solution,
            "metrics": self.metrics.to_dict(),
        }