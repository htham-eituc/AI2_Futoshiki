"""
Visualization Service - Bridge between GUI and Core solvers.

This service encapsulates all interactions with the core module,
providing a clean interface for the GUI components.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple
from dataclasses import dataclass, field
import copy

# Add src directory to path for imports
SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.problem.parser import FutoshikiData, ParserFactory, AlgorithmAdapter
from core.solvers.base_solver import SolverFactory

# Import solvers to register them
import core.solvers.backtrack
import core.solvers.astar
import core.solvers.forward_chaining
import core.solvers.backward_chaining


@dataclass
class StepState:
    """Represents the state at a single algorithm step."""
    step_number: int
    grid: List[List[int]]
    active_cell: Optional[Tuple[int, int]] = None
    changed_cell: Optional[Tuple[int, int]] = None
    conflict_cells: List[Tuple[int, int]] = field(default_factory=list)
    message: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    is_complete: bool = False
    is_solved: bool = False


@dataclass
class ComparisonResult:
    """Results from running a single algorithm on a single testcase."""
    algorithm: str
    testcase: str
    solved: bool
    elapsed_seconds: float
    nodes_generated: int
    nodes_expanded: int
    constraint_checks: int
    backtracks: int
    assignments: int
    error: Optional[str] = None


class VisualizationService:
    """Service layer for algorithm visualization."""

    # Directories to scan for testcases (relative to project root)
    TESTCASE_DIRS = [
        "src/test_generate",
        "data/inputs",
    ]
    
    # Project root (parent of src/)
    PROJECT_ROOT = SRC_DIR.parent

    @classmethod
    def get_available_algorithms(cls) -> List[str]:
        """
        Get list of all registered solver algorithms.
        
        Returns:
            List of algorithm names sorted alphabetically.
        """
        return sorted(SolverFactory.registered_solvers().keys())

    @classmethod
    def get_available_testcases(cls) -> List[Dict[str, str]]:
        """
        Scan testcase directories for puzzle files.
        
        Returns:
            List of dicts with 'name' and 'path' keys for each testcase.
        """
        testcases = []
        
        for dir_path in cls.TESTCASE_DIRS:
            full_path = cls.PROJECT_ROOT / dir_path
            if not full_path.exists():
                continue
                
            for file_path in sorted(full_path.glob("*.txt")):
                testcases.append({
                    "name": file_path.stem,
                    "path": str(file_path),
                })
        
        return testcases

    @classmethod
    def load_puzzle(cls, filepath: str) -> FutoshikiData:
        """
        Load and parse a puzzle file.
        
        Args:
            filepath: Path to the puzzle file.
            
        Returns:
            Parsed FutoshikiData object.
        """
        return ParserFactory.get_standard_data(filepath)

    @classmethod
    def run_algorithm_steps(
        cls,
        algorithm_name: str,
        puzzle_data: FutoshikiData,
    ) -> Generator[StepState, None, None]:
        """
        Run algorithm step-by-step, yielding state at each step.
        
        This is a generator that yields StepState objects representing
        the algorithm's progress through the puzzle.
        
        Args:
            algorithm_name: Name of the registered algorithm to use.
            puzzle_data: Parsed puzzle data.
            
        Yields:
            StepState objects for each algorithm step.
        """
        # Initial state
        yield StepState(
            step_number=0,
            grid=[row[:] for row in puzzle_data.grid],
            message="Initial puzzle state",
            metrics={
                "nodes_generated": 0,
                "nodes_expanded": 0,
                "constraint_checks": 0,
                "assignments": 0,
                "backtracks": 0,
            },
        )
        
        # For step visualization, we use backtracking with step capture
        # This simplified version simulates steps based on the algorithm
        solver = SolverFactory.create(algorithm_name, puzzle_data)
        
        if algorithm_name == "backtracking":
            yield from cls._run_backtracking_steps(solver, puzzle_data)
        else:
            # For non-backtracking algorithms, run and show result
            result = solver.solve()
            metrics = result.get("metrics", {})
            solution = result.get("solution")
            
            if solution:
                yield StepState(
                    step_number=1,
                    grid=solution,
                    message="Algorithm completed",
                    metrics=metrics,
                    is_complete=True,
                    is_solved=True,
                )
            else:
                yield StepState(
                    step_number=1,
                    grid=[row[:] for row in puzzle_data.grid],
                    message="No solution found",
                    metrics=metrics,
                    is_complete=True,
                    is_solved=False,
                )

    @classmethod
    def _run_backtracking_steps(
        cls,
        solver: Any,
        puzzle_data: FutoshikiData,
    ) -> Generator[StepState, None, None]:
        """
        Generate step-by-step states for backtracking algorithm.
        
        This captures each assignment and backtrack as a step.
        """
        n = puzzle_data.size
        grid = [row[:] for row in puzzle_data.grid]
        step = 1
        
        # Find empty cells
        empty_cells = []
        for r in range(n):
            for c in range(n):
                if grid[r][c] == 0:
                    empty_cells.append((r, c))
        
        if not empty_cells:
            yield StepState(
                step_number=step,
                grid=grid,
                message="Puzzle already solved",
                is_complete=True,
                is_solved=True,
            )
            return
        
        # Simulate step-by-step solving
        assignments = []
        metrics = {
            "nodes_generated": 0,
            "nodes_expanded": 0,
            "constraint_checks": 0,
            "assignments": 0,
            "backtracks": 0,
        }
        
        def is_valid(row: int, col: int, val: int) -> bool:
            metrics["constraint_checks"] += 1
            # Row check
            for c in range(n):
                if c != col and grid[row][c] == val:
                    return False
            # Column check  
            for r in range(n):
                if r != row and grid[r][col] == val:
                    return False
            # Horizontal constraints
            if col > 0:
                constraint = puzzle_data.h_constraints[row][col - 1]
                left = grid[row][col - 1]
                if left != 0 and constraint != 0:
                    if constraint == 1 and not (left < val):
                        return False
                    if constraint == -1 and not (left > val):
                        return False
            if col < n - 1:
                constraint = puzzle_data.h_constraints[row][col]
                right = grid[row][col + 1]
                if right != 0 and constraint != 0:
                    if constraint == 1 and not (val < right):
                        return False
                    if constraint == -1 and not (val > right):
                        return False
            # Vertical constraints
            if row > 0:
                constraint = puzzle_data.v_constraints[row - 1][col]
                top = grid[row - 1][col]
                if top != 0 and constraint != 0:
                    if constraint == 1 and not (top < val):
                        return False
                    if constraint == -1 and not (top > val):
                        return False
            if row < n - 1:
                constraint = puzzle_data.v_constraints[row][col]
                bottom = grid[row + 1][col]
                if bottom != 0 and constraint != 0:
                    if constraint == 1 and not (val < bottom):
                        return False
                    if constraint == -1 and not (val > bottom):
                        return False
            return True
        
        cell_idx = 0
        value_stack = [1]  # Current value to try at each level
        
        while cell_idx < len(empty_cells):
            if cell_idx < 0:
                # No solution
                yield StepState(
                    step_number=step,
                    grid=[row[:] for row in grid],
                    message="No solution found - exhausted all possibilities",
                    metrics=dict(metrics),
                    is_complete=True,
                    is_solved=False,
                )
                return
            
            row, col = empty_cells[cell_idx]
            metrics["nodes_expanded"] += 1
            
            found_valid = False
            start_val = value_stack[cell_idx] if cell_idx < len(value_stack) else 1
            
            for val in range(start_val, n + 1):
                metrics["nodes_generated"] += 1
                
                if is_valid(row, col, val):
                    grid[row][col] = val
                    metrics["assignments"] += 1
                    
                    yield StepState(
                        step_number=step,
                        grid=[r[:] for r in grid],
                        active_cell=(row, col),
                        changed_cell=(row, col),
                        message=f"Assigned {val} to cell ({row+1}, {col+1})",
                        metrics=dict(metrics),
                    )
                    step += 1
                    
                    if cell_idx < len(value_stack):
                        value_stack[cell_idx] = val + 1
                    else:
                        value_stack.append(val + 1)
                    
                    cell_idx += 1
                    if cell_idx < len(value_stack):
                        value_stack[cell_idx] = 1
                    else:
                        value_stack.append(1)
                    
                    found_valid = True
                    break
            
            if not found_valid:
                # Backtrack
                grid[row][col] = 0
                metrics["backtracks"] += 1
                
                yield StepState(
                    step_number=step,
                    grid=[r[:] for r in grid],
                    active_cell=(row, col),
                    conflict_cells=[(row, col)],
                    message=f"Backtracking from cell ({row+1}, {col+1})",
                    metrics=dict(metrics),
                )
                step += 1
                
                cell_idx -= 1
                if cell_idx >= 0:
                    r, c = empty_cells[cell_idx]
                    grid[r][c] = 0
        
        # Solution found
        yield StepState(
            step_number=step,
            grid=[r[:] for r in grid],
            message="Puzzle solved!",
            metrics=dict(metrics),
            is_complete=True,
            is_solved=True,
        )

    @classmethod
    def run_batch_comparison(
        cls,
        algorithms: List[str],
        testcases: Optional[List[Dict[str, str]]] = None,
    ) -> List[ComparisonResult]:
        """
        Run multiple algorithms on multiple testcases for comparison.
        
        Args:
            algorithms: List of algorithm names to compare.
            testcases: List of testcase dicts with 'name' and 'path'.
                      If None, uses all available testcases.
        
        Returns:
            List of ComparisonResult objects.
        """
        if testcases is None:
            testcases = cls.get_available_testcases()
        
        results = []
        
        for testcase in testcases:
            try:
                puzzle_data = cls.load_puzzle(testcase["path"])
            except Exception as e:
                # Skip testcases that fail to load
                for algo in algorithms:
                    results.append(ComparisonResult(
                        algorithm=algo,
                        testcase=testcase["name"],
                        solved=False,
                        elapsed_seconds=0,
                        nodes_generated=0,
                        nodes_expanded=0,
                        constraint_checks=0,
                        backtracks=0,
                        assignments=0,
                        error=str(e),
                    ))
                continue
            
            for algo in algorithms:
                try:
                    # Adapt puzzle data based on algorithm
                    adapter = AlgorithmAdapter(puzzle_data)
                    if algo == "astar":
                        problem = adapter.to_astar()
                    else:
                        # backtracking, forward_chaining, backward_chaining use FutoshikiData
                        problem = puzzle_data
                    
                    solver = SolverFactory.create(algo, problem)
                    result = solver.solve()
                    metrics = result.get("metrics", {})
                    
                    # Handle SolverMetrics object vs dict
                    if hasattr(metrics, 'to_dict'):
                        metrics = metrics.to_dict()
                    
                    results.append(ComparisonResult(
                        algorithm=algo,
                        testcase=testcase["name"],
                        solved=metrics.get("solved", False),
                        elapsed_seconds=metrics.get("elapsed_seconds", 0),
                        nodes_generated=metrics.get("nodes_generated", 0),
                        nodes_expanded=metrics.get("nodes_expanded", 0),
                        constraint_checks=metrics.get("constraint_checks", 0),
                        backtracks=metrics.get("backtracks", 0),
                        assignments=metrics.get("assignments", 0),
                    ))
                except Exception as e:
                    results.append(ComparisonResult(
                        algorithm=algo,
                        testcase=testcase["name"],
                        solved=False,
                        elapsed_seconds=0,
                        nodes_generated=0,
                        nodes_expanded=0,
                        constraint_checks=0,
                        backtracks=0,
                        assignments=0,
                        error=str(e),
                    ))
        
        return results


__all__ = ["VisualizationService", "StepState", "ComparisonResult"]
