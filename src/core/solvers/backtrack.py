"""
Simple Backtracking Solver for Futoshiki Puzzles.

This solver uses a basic backtracking approach:
- Sequential variable selection (row-by-row, left-to-right)
- Natural value ordering (1..N)
- Post-assignment constraint validation
- Array-based state saving for backtracking
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .base_solver import BaseSolver, SolverFactory
from ..utils.metrics import GLOBAL_METRICS_STORE


@SolverFactory.register("backtracking")
class BacktrackingSolver(BaseSolver):
    """
    Basic backtracking solver for Futoshiki puzzles.

    Uses sequential variable selection, natural value ordering, and
    validates constraints after each assignment.
    """

    def __init__(self, problem: Any, *, name: Optional[str] = None) -> None:
        super().__init__(problem, name=name or "Backtracking")

        self.n: int = problem.size
        self.grid: List[List[int]] = [row[:] for row in problem.grid]
        self.h_constraints: List[List[int]] = problem.h_constraints
        self.v_constraints: List[List[int]] = problem.v_constraints
        self.solutions: List[List[List[int]]] = []

    def _find_next_empty_cell(self) -> Optional[Tuple[int, int]]:
        for row in range(self.n):
            for col in range(self.n):
                if self.grid[row][col] == 0:
                    return (row, col)
        return None

    def _is_valid_assignment(
        self,
        row: int,
        col: int,
        value: int,
        *,
        count_checks: bool = True,
    ) -> bool:
        # Row uniqueness
        for c in range(self.n):
            if c == col:
                continue
            if count_checks:
                self.metrics.inc_constraint_checks()
            if self.grid[row][c] == value:
                return False

        # Column uniqueness
        for r in range(self.n):
            if r == row:
                continue
            if count_checks:
                self.metrics.inc_constraint_checks()
            if self.grid[r][col] == value:
                return False

        # Horizontal constraints (left neighbor)
        if col > 0:
            constraint = self.h_constraints[row][col - 1]
            left_value = self.grid[row][col - 1]
            if constraint != 0 and left_value != 0:
                if count_checks:
                    self.metrics.inc_constraint_checks()
                if constraint == 1 and not (left_value < value):
                    return False
                if constraint == -1 and not (left_value > value):
                    return False

        # Horizontal constraints (right neighbor)
        if col < self.n - 1:
            constraint = self.h_constraints[row][col]
            right_value = self.grid[row][col + 1]
            if constraint != 0 and right_value != 0:
                if count_checks:
                    self.metrics.inc_constraint_checks()
                if constraint == 1 and not (value < right_value):
                    return False
                if constraint == -1 and not (value > right_value):
                    return False

        # Vertical constraints (top neighbor)
        if row > 0:
            constraint = self.v_constraints[row - 1][col]
            top_value = self.grid[row - 1][col]
            if constraint != 0 and top_value != 0:
                if count_checks:
                    self.metrics.inc_constraint_checks()
                if constraint == 1 and not (top_value < value):
                    return False
                if constraint == -1 and not (top_value > value):
                    return False

        # Vertical constraints (bottom neighbor)
        if row < self.n - 1:
            constraint = self.v_constraints[row][col]
            bottom_value = self.grid[row + 1][col]
            if constraint != 0 and bottom_value != 0:
                if count_checks:
                    self.metrics.inc_constraint_checks()
                if constraint == 1 and not (value < bottom_value):
                    return False
                if constraint == -1 and not (value > bottom_value):
                    return False

        return True

    def _backtrack(self, limit: int = 2) -> bool:
        if len(self.solutions) >= limit:
            return True

        cell = self._find_next_empty_cell()
        if cell is None:
            self.solutions.append([row[:] for row in self.grid])
            return len(self.solutions) >= limit

        row, col = cell
        self.metrics.inc_nodes_expanded()

        for value in range(1, self.n + 1):
            self.metrics.inc_nodes_generated()
            if not self._is_valid_assignment(row, col, value):
                continue

            saved_grid = [r[:] for r in self.grid]
            self.grid[row][col] = value
            self.metrics.inc_assignments()

            if self._backtrack(limit):
                return True

            self.metrics.inc_backtracks()
            self.grid = saved_grid

        return False

    def solve(self) -> Dict[str, Any]:
        """
        Solve the Futoshiki puzzle using basic backtracking.

        Returns:
            Dict with keys:
                - status: "unique", "multiple", or "none"
                - solution: solved grid or None
                - metrics: solver metrics dict
        """
        self.metrics.start()
        status = "none"
        solution = None

        try:
            # Validate pre-filled cells
            for row in range(self.n):
                for col in range(self.n):
                    value = self.grid[row][col]
                    if value == 0:
                        continue
                    if value < 1 or value > self.n:
                        self.metrics.mark_solved(False)
                        status = "none"
                        solution = None
                        return  # jump to finally
                    self.grid[row][col] = 0
                    if not self._is_valid_assignment(row, col, value, count_checks=False):
                        self.grid[row][col] = value
                        self.metrics.mark_solved(False)
                        status = "none"
                        solution = None
                        return  # jump to finally
                    self.grid[row][col] = value

            self._backtrack(limit=2)

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
            # stop() ALWAYS runs before to_dict() so elapsed_seconds is correct
            self.metrics.stop()
            GLOBAL_METRICS_STORE.add(self.metrics)

        return {
            "status": status,
            "solution": solution,
            "metrics": self.metrics.to_dict(),
        }


__all__ = ["BacktrackingSolver"]