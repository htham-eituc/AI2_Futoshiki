from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_solver import BaseSolver, SolverFactory
from ..utils.metrics import GLOBAL_METRICS_STORE

                           
from ..heuristics.ac3 import (
    build_initial_domains,
    run_ac3,
    select_mrv_cell,
    lcv_order,
    domains_to_grid,
)

from ..utils.step_state import StepState

@SolverFactory.register("backtracking")
class BacktrackingSolver(BaseSolver):
    """
    Backtracking + MRV + LCV + AC-3 solver for Futoshiki.
    """

    def __init__(self, problem: Any, *, name: Optional[str] = None) -> None:
        super().__init__(problem, name=name or "Backtracking")

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

                       
        cell = select_mrv_cell(domains)

        if cell is None:
            solution = domains_to_grid(domains, self.n)

            if self._is_valid_solution(solution):
                self.solutions.append(solution)

            return len(self.solutions) >= limit

        self.metrics.inc_nodes_expanded()

                      
        for value in lcv_order(
            cell, domains, self.n, self.h_constraints, self.v_constraints
        ):
            self.metrics.inc_nodes_generated()

                          
            new_domains = {k: set(v) for k, v in domains.items()}

                          
            new_domains[cell] = {value}
            self.metrics.inc_assignments()

                                               
            pruned = run_ac3(
                new_domains,
                self.n,
                self.h_constraints,
                self.v_constraints,
            )

                                     
            if pruned is None:
                self.metrics.inc_backtracks()
                continue

                             
            if self._backtrack(pruned, limit):
                return True

            self.metrics.inc_backtracks()

        return False                                                                 

    def solve(self) -> Dict[str, Any]:
        self.metrics.start()

        status = "none"
        solution = None

        try:                  
            domains = build_initial_domains(self.n, self.grid)                  
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

    def solve_steps(self):
        """Generate step-by-step states for backtracking algorithm with heuristics."""
        if StepState is None:
            raise ImportError("StepState not available for visualization")

        import time
        start_time = time.time()
        
        n = self.n
        grid = [row[:] for row in self.grid]
        step = 1

        # Initial state
        yield StepState(
            step_number=step,
            grid=[row[:] for row in grid],
            message="Initial puzzle state",
            metrics={
                "nodes_generated": 0,
                "nodes_expanded": 0,
                "constraint_checks": 0,
                "assignments": 0,
                "backtracks": 0,
                "elapsed_seconds": 0,
            },
        )
        step += 1

        # Build initial domains
        domains = build_initial_domains(n, grid)
        domains = run_ac3(domains, n, self.h_constraints, self.v_constraints)

        if domains is None:
            yield StepState(
                step_number=step,
                grid=[row[:] for row in grid],
                message="Initial AC-3 failed - no solution possible",
                metrics={
                    "nodes_generated": 0,
                    "nodes_expanded": 0,
                    "constraint_checks": 0,
                    "assignments": 0,
                    "backtracks": 0,
                    "elapsed_seconds": time.time() - start_time,
                },
                is_complete=True,
                is_solved=False,
            )
            return

        # Iterative backtracking with stack, choosing MRV cell at each step
        stack = [domains]
        metrics = {
            "nodes_generated": 0,
            "nodes_expanded": 0,
            "constraint_checks": 0,
            "assignments": 0,
            "backtracks": 0,
        }

        while stack:
            current_domains = stack[-1]

            # Find candidates: cells with domain size > 1
            candidates = [cell for cell in current_domains if len(current_domains[cell]) > 1]
            if not candidates:
                # Solution found
                solution_grid = domains_to_grid(current_domains, n)
                metrics["elapsed_seconds"] = time.time() - start_time
                yield StepState(
                    step_number=step,
                    grid=solution_grid,
                    message="Solution found!",
                    metrics=dict(metrics),
                    is_complete=True,
                    is_solved=True,
                )
                return  # Stop after finding the first solution

            # Select MRV cell
            cell = min(candidates, key=lambda c: len(current_domains[c]))
            metrics["nodes_expanded"] += 1

            # Get values in LCV order
            values = lcv_order(cell, current_domains, n, self.h_constraints, self.v_constraints)
            assigned = False

            for value in values:
                metrics["nodes_generated"] += 1

                # Try assignment
                new_domains = {k: set(v) for k, v in current_domains.items()}
                new_domains[cell] = {value}
                metrics["assignments"] += 1

                # Run AC-3
                pruned = run_ac3(new_domains, n, self.h_constraints, self.v_constraints)

                if pruned is not None:
                    # Successful assignment
                    current_grid = domains_to_grid(new_domains, n)
                    metrics["elapsed_seconds"] = time.time() - start_time
                    yield StepState(
                        step_number=step,
                        grid=current_grid,
                        active_cell=cell,
                        changed_cell=cell,
                        message=f"Assigned {value} to cell ({cell[0]}, {cell[1]})",
                        metrics=dict(metrics),
                    )
                    step += 1

                    # Push next state
                    stack.append(pruned)
                    assigned = True
                    break

            if not assigned:
                # Backtrack
                metrics["elapsed_seconds"] = time.time() - start_time
                yield StepState(
                    step_number=step,
                    grid=domains_to_grid(current_domains, n),
                    conflict_cells=[cell],
                    message=f"Backtracking from cell ({cell[0]}, {cell[1]}) - no valid values",
                    metrics=dict(metrics),
                )
                step += 1
                metrics["backtracks"] += 1
                stack.pop()

        # No solution
        metrics["elapsed_seconds"] = time.time() - start_time
        yield StepState(
            step_number=step,
            grid=[row[:] for row in grid],
            message="No solution found",
            metrics=dict(metrics),
            is_complete=True,
            is_solved=False,
        )