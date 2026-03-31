"""
Branch and Bound Backtracking Solver for Futoshiki Puzzles

This solver uses advanced backtracking with Branch and Bound optimizations:
- MRV (Minimum Remaining Values): Select cell with fewest legal values
- LCV (Least Constraining Value): Order values by how many options they leave
- Forward Checking: Prune domains when assignments are made
- Arc Consistency: Propagate constraints to detect failures early
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from .base_solver import BaseSolver, SolverFactory
from ..utils.metrics import GLOBAL_METRICS_STORE


@SolverFactory.register("backtracking")
class BacktrackingSolver(BaseSolver):
    """
    Branch and Bound backtracking solver for Futoshiki puzzles.
    
    Uses MRV heuristic for variable selection, LCV for value ordering,
    and forward checking with arc consistency for constraint propagation.
    """
    
    def __init__(self, problem: Any, *, name: Optional[str] = None) -> None:
        super().__init__(problem, name=name or "Backtracking")
        
        # Extract problem data
        self.n: int = problem.size
        self.grid: List[List[int]] = [row[:] for row in problem.grid]
        self.h_constraints: List[List[int]] = problem.h_constraints
        self.v_constraints: List[List[int]] = problem.v_constraints
        
        # Initialize domains for each cell
        self.domains: List[List[Set[int]]] = self._init_domains()
        
        # Track solutions
        self.solutions: List[List[List[int]]] = []
    
    def _init_domains(self) -> List[List[Set[int]]]:
        """
        Initialize domains for each cell.
        
        For filled cells, domain is the single assigned value.
        For empty cells, domain starts as {1, 2, ..., N} and is pruned
        based on initial constraints.
        """
        domains = [[set(range(1, self.n + 1)) for _ in range(self.n)] 
                   for _ in range(self.n)]
        
        # Set domains for pre-filled cells
        for row in range(self.n):
            for col in range(self.n):
                if self.grid[row][col] != 0:
                    domains[row][col] = {self.grid[row][col]}
        
        # Initial constraint propagation
        self._propagate_all_constraints(domains)
        
        return domains
    
    def _propagate_all_constraints(self, domains: List[List[Set[int]]]) -> bool:
        """
        Propagate all constraints to prune domains.
        
        Returns:
            True if domains are consistent, False if any domain becomes empty.
        """
        changed = True
        while changed:
            changed = False
            
            # Row uniqueness
            for row in range(self.n):
                for col in range(self.n):
                    if self.grid[row][col] != 0:
                        val = self.grid[row][col]
                        for c in range(self.n):
                            if c != col and val in domains[row][c]:
                                domains[row][c].discard(val)
                                changed = True
                                if not domains[row][c]:
                                    return False
            
            # Column uniqueness
            for col in range(self.n):
                for row in range(self.n):
                    if self.grid[row][col] != 0:
                        val = self.grid[row][col]
                        for r in range(self.n):
                            if r != row and val in domains[r][col]:
                                domains[r][col].discard(val)
                                changed = True
                                if not domains[r][col]:
                                    return False
            
            # Inequality constraints
            if not self._propagate_inequality_constraints(domains):
                return False
        
        return True
    
    def _propagate_inequality_constraints(self, domains: List[List[Set[int]]]) -> bool:
        """
        Propagate inequality constraints to prune domains.
        
        For constraint A < B:
        - Remove values from A that are >= max(B's domain)
        - Remove values from B that are <= min(A's domain)
        """
        # Horizontal constraints
        for row in range(self.n):
            for col in range(self.n - 1):
                constraint = self.h_constraints[row][col]
                if constraint == 0:
                    continue
                
                left_domain = domains[row][col]
                right_domain = domains[row][col + 1]
                
                if constraint == 1:  # left < right
                    if not self._prune_less_than(left_domain, right_domain):
                        return False
                else:  # left > right (constraint == -1)
                    if not self._prune_less_than(right_domain, left_domain):
                        return False
        
        # Vertical constraints
        for row in range(self.n - 1):
            for col in range(self.n):
                constraint = self.v_constraints[row][col]
                if constraint == 0:
                    continue
                
                top_domain = domains[row][col]
                bottom_domain = domains[row + 1][col]
                
                if constraint == 1:  # top < bottom
                    if not self._prune_less_than(top_domain, bottom_domain):
                        return False
                else:  # top > bottom (constraint == -1)
                    if not self._prune_less_than(bottom_domain, top_domain):
                        return False
        
        return True
    
    def _prune_less_than(self, smaller: Set[int], larger: Set[int]) -> bool:
        """
        Prune domains for constraint: smaller < larger
        
        Returns:
            True if both domains still have values, False if either becomes empty.
        """
        if not smaller or not larger:
            return False
        
        max_larger = max(larger)
        min_smaller = min(smaller)
        
        # Remove values from smaller that are >= max(larger)
        to_remove = {v for v in smaller if v >= max_larger}
        smaller -= to_remove
        
        # Remove values from larger that are <= min(smaller)
        to_remove = {v for v in larger if v <= min_smaller}
        larger -= to_remove
        
        return bool(smaller) and bool(larger)
    
    def _select_unassigned_variable_mrv(self) -> Optional[Tuple[int, int]]:
        """
        Select the unassigned variable with Minimum Remaining Values (MRV).
        
        Also known as "most constrained variable" or "fail-first" heuristic.
        Ties are broken by degree heuristic (most constraints on remaining vars).
        
        Returns:
            Tuple (row, col) of the best cell to assign, or None if all assigned.
        """
        best_cell = None
        best_domain_size = self.n + 1
        best_degree = -1
        
        for row in range(self.n):
            for col in range(self.n):
                if self.grid[row][col] == 0:  # Unassigned
                    domain_size = len(self.domains[row][col])
                    
                    if domain_size == 0:
                        # Empty domain - immediate failure
                        return (row, col)
                    
                    if domain_size < best_domain_size:
                        best_cell = (row, col)
                        best_domain_size = domain_size
                        best_degree = self._count_constraints(row, col)
                    elif domain_size == best_domain_size:
                        # Tie-break with degree heuristic
                        degree = self._count_constraints(row, col)
                        if degree > best_degree:
                            best_cell = (row, col)
                            best_degree = degree
        
        return best_cell
    
    def _count_constraints(self, row: int, col: int) -> int:
        """
        Count the number of constraints involving this cell with unassigned neighbors.
        Used as tie-breaker for MRV (degree heuristic).
        """
        count = 0
        
        # Count unassigned cells in same row
        for c in range(self.n):
            if c != col and self.grid[row][c] == 0:
                count += 1
        
        # Count unassigned cells in same column
        for r in range(self.n):
            if r != row and self.grid[r][col] == 0:
                count += 1
        
        # Count inequality constraints with unassigned neighbors
        # Horizontal left
        if col > 0 and self.h_constraints[row][col - 1] != 0:
            if self.grid[row][col - 1] == 0:
                count += 1
        # Horizontal right
        if col < self.n - 1 and self.h_constraints[row][col] != 0:
            if self.grid[row][col + 1] == 0:
                count += 1
        # Vertical top
        if row > 0 and self.v_constraints[row - 1][col] != 0:
            if self.grid[row - 1][col] == 0:
                count += 1
        # Vertical bottom
        if row < self.n - 1 and self.v_constraints[row][col] != 0:
            if self.grid[row + 1][col] == 0:
                count += 1
        
        return count
    
    def _order_domain_values_lcv(self, row: int, col: int) -> List[int]:
        """
        Order domain values using Least Constraining Value (LCV) heuristic.
        
        Prefers values that rule out the fewest choices for neighboring variables.
        This maximizes flexibility for future assignments.
        
        Returns:
            List of values from domain, ordered by LCV (least constraining first).
        """
        domain = list(self.domains[row][col])
        
        if len(domain) <= 1:
            return domain
        
        def count_conflicts(value: int) -> int:
            """Count how many values this choice eliminates from neighbors."""
            conflicts = 0
            
            # Row neighbors
            for c in range(self.n):
                if c != col and self.grid[row][c] == 0:
                    if value in self.domains[row][c]:
                        conflicts += 1
            
            # Column neighbors
            for r in range(self.n):
                if r != row and self.grid[r][col] == 0:
                    if value in self.domains[r][col]:
                        conflicts += 1
            
            # Inequality constraint neighbors
            # Horizontal left: if constraint exists and left < this cell
            if col > 0 and self.grid[row][col - 1] == 0:
                constraint = self.h_constraints[row][col - 1]
                if constraint == 1:  # left < this
                    # Values in left domain >= value become invalid
                    conflicts += sum(1 for v in self.domains[row][col - 1] if v >= value)
                elif constraint == -1:  # left > this
                    conflicts += sum(1 for v in self.domains[row][col - 1] if v <= value)
            
            # Horizontal right
            if col < self.n - 1 and self.grid[row][col + 1] == 0:
                constraint = self.h_constraints[row][col]
                if constraint == 1:  # this < right
                    conflicts += sum(1 for v in self.domains[row][col + 1] if v <= value)
                elif constraint == -1:  # this > right
                    conflicts += sum(1 for v in self.domains[row][col + 1] if v >= value)
            
            # Vertical top
            if row > 0 and self.grid[row - 1][col] == 0:
                constraint = self.v_constraints[row - 1][col]
                if constraint == 1:  # top < this
                    conflicts += sum(1 for v in self.domains[row - 1][col] if v >= value)
                elif constraint == -1:  # top > this
                    conflicts += sum(1 for v in self.domains[row - 1][col] if v <= value)
            
            # Vertical bottom
            if row < self.n - 1 and self.grid[row + 1][col] == 0:
                constraint = self.v_constraints[row][col]
                if constraint == 1:  # this < bottom
                    conflicts += sum(1 for v in self.domains[row + 1][col] if v <= value)
                elif constraint == -1:  # this > bottom
                    conflicts += sum(1 for v in self.domains[row + 1][col] if v >= value)
            
            return conflicts
        
        # Sort by conflicts (ascending - least constraining first)
        domain.sort(key=count_conflicts)
        return domain
    
    def _forward_check(self, row: int, col: int, value: int, 
                       domains: List[List[Set[int]]]) -> bool:
        """
        Forward checking: prune domains of neighbors after assignment.
        
        Returns:
            True if all neighbor domains still have values, False if any becomes empty.
        """
        self.metrics.inc_constraint_checks()
        
        # Remove value from row neighbors
        for c in range(self.n):
            if c != col and self.grid[row][c] == 0:
                domains[row][c].discard(value)
                if not domains[row][c]:
                    return False
        
        # Remove value from column neighbors
        for r in range(self.n):
            if r != row and self.grid[r][col] == 0:
                domains[r][col].discard(value)
                if not domains[r][col]:
                    return False
        
        # Propagate inequality constraints
        # Horizontal left
        if col > 0 and self.grid[row][col - 1] == 0:
            constraint = self.h_constraints[row][col - 1]
            if constraint == 1:  # left < value
                domains[row][col - 1] = {v for v in domains[row][col - 1] if v < value}
            elif constraint == -1:  # left > value
                domains[row][col - 1] = {v for v in domains[row][col - 1] if v > value}
            if not domains[row][col - 1]:
                return False
        
        # Horizontal right
        if col < self.n - 1 and self.grid[row][col + 1] == 0:
            constraint = self.h_constraints[row][col]
            if constraint == 1:  # value < right
                domains[row][col + 1] = {v for v in domains[row][col + 1] if v > value}
            elif constraint == -1:  # value > right
                domains[row][col + 1] = {v for v in domains[row][col + 1] if v < value}
            if not domains[row][col + 1]:
                return False
        
        # Vertical top
        if row > 0 and self.grid[row - 1][col] == 0:
            constraint = self.v_constraints[row - 1][col]
            if constraint == 1:  # top < value
                domains[row - 1][col] = {v for v in domains[row - 1][col] if v < value}
            elif constraint == -1:  # top > value
                domains[row - 1][col] = {v for v in domains[row - 1][col] if v > value}
            if not domains[row - 1][col]:
                return False
        
        # Vertical bottom
        if row < self.n - 1 and self.grid[row + 1][col] == 0:
            constraint = self.v_constraints[row][col]
            if constraint == 1:  # value < bottom
                domains[row + 1][col] = {v for v in domains[row + 1][col] if v > value}
            elif constraint == -1:  # value > bottom
                domains[row + 1][col] = {v for v in domains[row + 1][col] if v < value}
            if not domains[row + 1][col]:
                return False
        
        return True
    
    def _copy_domains(self) -> List[List[Set[int]]]:
        """Create a deep copy of current domains."""
        return [[cell.copy() for cell in row] for row in self.domains]
    
    def _backtrack(self, limit: int = 2) -> bool:
        """
        Branch and Bound backtracking with MRV, LCV, and forward checking.
        
        Args:
            limit: Maximum number of solutions to find (default 2 for uniqueness check)
        
        Returns:
            True if should stop early (limit reached), False otherwise.
        """
        if len(self.solutions) >= limit:
            return True
        
        # Select variable using MRV heuristic
        cell = self._select_unassigned_variable_mrv()
        
        if cell is None:
            # All cells assigned - solution found
            self.solutions.append([row[:] for row in self.grid])
            return len(self.solutions) >= limit
        
        row, col = cell
        self.metrics.inc_nodes_expanded()
        
        # Check for empty domain (failure)
        if not self.domains[row][col]:
            return False
        
        # Order values using LCV heuristic
        ordered_values = self._order_domain_values_lcv(row, col)
        
        for value in ordered_values:
            self.metrics.inc_nodes_generated()
            
            # Save state for backtracking
            saved_domains = self._copy_domains()
            
            # Make assignment
            self.grid[row][col] = value
            self.domains[row][col] = {value}
            self.metrics.inc_assignments()
            
            # Forward check - prune neighbor domains
            if self._forward_check(row, col, value, self.domains):
                # Recurse
                if self._backtrack(limit):
                    return True
            
            # Backtrack - restore state
            self.grid[row][col] = 0
            self.domains = saved_domains
            self.metrics.inc_backtracks()
        
        return False
    
    def solve(self) -> Dict[str, Any]:
        """
        Solve the Futoshiki puzzle using Branch and Bound backtracking.
        
        Returns:
            Dict with keys:
                - status: "unique", "multiple", or "none"
                - solution: solved grid or None
                - metrics: solver metrics dict
        """
        self.metrics.start()
        
        try:
            # Check for initial inconsistency
            for row in range(self.n):
                for col in range(self.n):
                    if self.grid[row][col] == 0 and not self.domains[row][col]:
                        self.metrics.mark_solved(False)
                        return {
                            "status": "none",
                            "solution": None,
                            "metrics": self.metrics.to_dict()
                        }
            
            # Run Branch and Bound backtracking
            self._backtrack(limit=2)
            
            # Determine result
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
            
            return {
                "status": status,
                "solution": solution,
                "metrics": self.metrics.to_dict()
            }
            
        finally:
            self.metrics.stop()
            GLOBAL_METRICS_STORE.add(self.metrics)


__all__ = ["BacktrackingSolver"]
