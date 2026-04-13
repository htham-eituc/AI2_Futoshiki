"""
Visualization Service - Bridge between GUI and Core solvers.

This service encapsulates all interactions with the core module,
providing a clean interface for the GUI components.
"""

from __future__ import annotations

import sys
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Generator, List, Optional, Tuple
from dataclasses import dataclass, field

# Add src directory to path for imports
SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.problem.parser import FutoshikiData, ParserFactory, AlgorithmAdapter
from core.solvers.base_solver import SolverFactory

# Import solvers to register them
import core.solvers.bruteforce
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


class ExperimentVisualizationError(Exception):
    """Raised when experiment visualization generation fails."""


@dataclass
class ExperimentVisualizationProgress:
    """Represents one generated chart step during streaming visualization."""
    step: int
    total: int
    chart_name: str
    chart_path: Path
    status: str = "generated"


def _metrics_to_dict(metrics: Any) -> Dict[str, Any]:
    """Normalize metrics to dict regardless of whether it's a dict or SolverMetrics object."""
    if metrics is None:
        return {}
    if isinstance(metrics, dict):
        return metrics
    if hasattr(metrics, "to_dict"):
        return metrics.to_dict()
    return {}


class VisualizationService:
    """Service layer for algorithm visualization."""

    # Directories to scan for testcases (relative to project root)
    TESTCASE_DIRS = [
        "src/test_generate",
        "data/inputs",
    ]

    # Project root (parent of src/)
    PROJECT_ROOT = SRC_DIR.parent
    EXPERIMENT_CHART_FILENAMES = [
        "summary_dashboard.png",
        "time_comparison.png",
        "nodes_comparison.png",
        "difficulty_analysis.png",
        "size_analysis.png",
        "detailed_metrics.png",
    ]
    EXPERIMENT_CHART_STEPS = [
        ("summary_dashboard", "summary_dashboard.png", "plot_summary_dashboard"),
        ("time_comparison", "time_comparison.png", "plot_time_comparison"),
        ("nodes_comparison", "nodes_comparison.png", "plot_nodes_comparison"),
        ("difficulty_analysis", "difficulty_analysis.png", "plot_difficulty_analysis"),
        ("size_analysis", "size_analysis.png", "plot_size_analysis"),
        ("detailed_metrics", "detailed_metrics.png", "plot_detailed_metrics"),
    ]

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

        Args:
            algorithm_name: Name of the registered algorithm to use.
            puzzle_data: Parsed puzzle data.

        Yields:
            StepState objects for each algorithm step.
        """
        # Initial state (step 0) — always shown first
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

        if algorithm_name == "bruteforce":
            # Backtracking: inline step-by-step simulation
            solver = SolverFactory.create(algorithm_name, puzzle_data)
            yield from cls._run_backtracking_steps(solver, puzzle_data)

        elif algorithm_name == "astar":
            # A*: adapt problem, run with snapshots enabled, replay snapshots
            adapter = AlgorithmAdapter(puzzle_data)
            problem = adapter.to_astar()
            solver = SolverFactory.create(algorithm_name, problem)
            solver.record_snapshots = True
            result = solver.solve()
            yield from cls._replay_astar_steps(result, puzzle_data)
            
        elif algorithm_name == "forward_chaining":
            solver = SolverFactory.create(algorithm_name, puzzle_data)
            yield from solver.solve_steps(puzzle_data)

        elif algorithm_name == "backward_chaining":
            solver = SolverFactory.create(algorithm_name, puzzle_data)
            yield from solver.solve_steps(puzzle_data)

        elif algorithm_name == "backtracking":
            solver = SolverFactory.create(algorithm_name, puzzle_data)
            yield from solver.solve_steps()

        else:
            # forward_chaining / backward_chaining / any future solver:
            # Run and show a single result step (no internal snapshots yet)
            solver = SolverFactory.create(algorithm_name, puzzle_data)
            result = solver.solve()
            metrics = _metrics_to_dict(result.get("metrics", {}))
            solution = result.get("solution")

            if solution:
                yield StepState(
                    step_number=1,
                    grid=solution,
                    message="Algorithm completed — solution found",
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

    # ------------------------------------------------------------------
    # A* snapshot replay
    # ------------------------------------------------------------------

    @classmethod
    def _replay_astar_steps(
        cls,
        result: Dict[str, Any],
        puzzle_data: FutoshikiData,
    ) -> Generator[StepState, None, None]:
        """
        Convert A* snapshots stored in metrics.extra into StepState objects.

        A* stores each expand/assign/prune event as:
            metrics["extra"]["snap_N"] = {
                "step": N,
                "grid": List[List[int]],
                "label": str,
            }
        """
        metrics_raw = result.get("metrics", {})
        metrics = _metrics_to_dict(metrics_raw)
        solution = result.get("solution")
        extra = metrics.get("extra", {})

        # Collect and sort snapshots by step index
        snaps = []
        for key, value in extra.items():
            if key.startswith("snap_") and isinstance(value, dict):
                snaps.append(value)
        snaps.sort(key=lambda s: s.get("step", 0))

        if not snaps:
            # No snapshots — fall back to single-step display
            if solution:
                yield StepState(
                    step_number=1,
                    grid=solution,
                    message="A* completed — solution found",
                    metrics=metrics,
                    is_complete=True,
                    is_solved=True,
                )
            else:
                yield StepState(
                    step_number=1,
                    grid=[row[:] for row in puzzle_data.grid],
                    message="A* found no solution",
                    metrics=metrics,
                    is_complete=True,
                    is_solved=False,
                )
            return

        # Running metrics counters — accumulate from final metrics
        # We show final metrics on last step; intermediate steps show partial counts
        total_expanded = metrics.get("nodes_expanded", 0)
        total_generated = metrics.get("nodes_generated", 0)
        total_checks = metrics.get("constraint_checks", 0)
        total_assignments = metrics.get("assignments", 0)
        total_backtracks = metrics.get("backtracks", 0)
        n_snaps = len(snaps)

        for i, snap in enumerate(snaps):
            grid = snap.get("grid", [row[:] for row in puzzle_data.grid])
            label: str = snap.get("label", "")
            step_num = i + 1

            # Detect what kind of step this is from the label
            is_pruned = "PRUNED" in label
            is_assign = label.startswith("assign")

            # Determine highlighted cell from label if possible
            # Labels look like: "assign (r,c)=v ..." or "PRUNED (r,c)=v"
            active_cell = _parse_cell_from_label(label)
            changed_cell = active_cell if is_assign else None
            conflict_cells = [active_cell] if is_pruned and active_cell else []

            # Partial metrics: scale linearly by progress through snaps
            frac = (i + 1) / n_snaps
            partial_metrics = {
                "nodes_generated": int(total_generated * frac),
                "nodes_expanded": int(total_expanded * frac),
                "constraint_checks": int(total_checks * frac),
                "assignments": int(total_assignments * frac),
                "backtracks": int(total_backtracks * frac),
                "elapsed_seconds": 0,
            }

            yield StepState(
                step_number=step_num,
                grid=grid,
                active_cell=active_cell,
                changed_cell=changed_cell,
                conflict_cells=conflict_cells,
                message=_format_astar_label(label),
                metrics=partial_metrics,
                is_complete=False,
                is_solved=False,
            )

        # Final step — show solution (or failure)
        final_step = n_snaps + 1
        final_metrics = {
            "nodes_generated": total_generated,
            "nodes_expanded": total_expanded,
            "constraint_checks": total_checks,
            "assignments": total_assignments,
            "backtracks": total_backtracks,
            "elapsed_seconds": metrics.get("elapsed_seconds", 0),
        }

        if solution:
            yield StepState(
                step_number=final_step,
                grid=solution,
                message="A* found the solution!",
                metrics=final_metrics,
                is_complete=True,
                is_solved=True,
            )
        else:
            yield StepState(
                step_number=final_step,
                grid=[row[:] for row in puzzle_data.grid],
                message="A* found no solution",
                metrics=final_metrics,
                is_complete=True,
                is_solved=False,
            )

    # ------------------------------------------------------------------
    # Backtracking inline step-by-step
    # ------------------------------------------------------------------

    @classmethod
    def _run_backtracking_steps(
        cls,
        solver: Any,
        puzzle_data: FutoshikiData,
    ) -> Generator[StepState, None, None]:
        """
        Generate step-by-step states for backtracking algorithm.
        Inline simulation — does not call solver.solve().
        """
        n = puzzle_data.size
        grid = [row[:] for row in puzzle_data.grid]
        step = 1

        empty_cells = [
            (r, c)
            for r in range(n)
            for c in range(n)
            if grid[r][c] == 0
        ]

        if not empty_cells:
            yield StepState(
                step_number=step,
                grid=grid,
                message="Puzzle already solved",
                is_complete=True,
                is_solved=True,
            )
            return

        metrics = {
            "nodes_generated": 0,
            "nodes_expanded": 0,
            "constraint_checks": 0,
            "assignments": 0,
            "backtracks": 0,
        }

        def is_valid(row: int, col: int, val: int) -> bool:
            metrics["constraint_checks"] += 1
            for c in range(n):
                if c != col and grid[row][c] == val:
                    return False
            for r in range(n):
                if r != row and grid[r][col] == val:
                    return False
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
        value_stack = [1]

        while cell_idx < len(empty_cells):
            if cell_idx < 0:
                yield StepState(
                    step_number=step,
                    grid=[row[:] for row in grid],
                    message="No solution found — exhausted all possibilities",
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
                        message=f"Assigned {val} to cell ({row + 1}, {col + 1})",
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
                grid[row][col] = 0
                metrics["backtracks"] += 1

                yield StepState(
                    step_number=step,
                    grid=[r[:] for r in grid],
                    active_cell=(row, col),
                    conflict_cells=[(row, col)],
                    message=f"Backtracking from cell ({row + 1}, {col + 1})",
                    metrics=dict(metrics),
                )
                step += 1

                cell_idx -= 1
                if cell_idx >= 0:
                    r2, c2 = empty_cells[cell_idx]
                    grid[r2][c2] = 0

        yield StepState(
            step_number=step,
            grid=[r[:] for r in grid],
            message="Puzzle solved!",
            metrics=dict(metrics),
            is_complete=True,
            is_solved=True,
        )

    # ------------------------------------------------------------------
    # Batch comparison
    # ------------------------------------------------------------------

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
                    adapter = AlgorithmAdapter(puzzle_data)
                    if algo == "astar":
                        problem = adapter.to_astar()
                        solver = SolverFactory.create(algo, problem)
                        solver.record_snapshots = False  # Save memory in batch mode
                    else:
                        problem = puzzle_data
                        solver = SolverFactory.create(algo, problem)

                    result = solver.solve()
                    metrics = _metrics_to_dict(result.get("metrics", {}))

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

    @classmethod
    def _load_experiment_visualizer_module(cls) -> ModuleType:
        """Load visualize_experiments.py as a module from project root."""
        script_path = cls.PROJECT_ROOT / "visualize_experiments.py"
        if not script_path.exists():
            raise ExperimentVisualizationError(
                f"Visualization script not found: {script_path}"
            )

        spec = importlib.util.spec_from_file_location("visualize_experiments", script_path)
        if spec is None or spec.loader is None:
            raise ExperimentVisualizationError(
                f"Could not load visualization script: {script_path}"
            )

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @classmethod
    def _load_experiment_data(
        cls,
        module: ModuleType,
        input_path: Path,
        require_solved: bool = True,
    ) -> Tuple[Any, Any]:
        """Load and validate experiment CSV data."""
        try:
            df, df_solved = module.load_data(input_path)
        except Exception as exc:
            raise ExperimentVisualizationError(
                f"Failed to load experiment data: {exc}"
            ) from exc

        if len(df.index) == 0:
            raise ExperimentVisualizationError("experiment.csv is empty.")
        if require_solved and len(df_solved.index) == 0:
            raise ExperimentVisualizationError(
                "experiment.csv has no solved rows to visualize."
            )

        return df, df_solved

    @classmethod
    def get_experiment_algorithms(
        cls,
        csv_path: Optional[Path] = None,
    ) -> List[str]:
        """
        Return sorted unique algorithm labels from experiment.csv.

        Args:
            csv_path: CSV input path. Defaults to <project_root>/experiment.csv.
        """
        input_path = csv_path or (cls.PROJECT_ROOT / "experiment.csv")
        if not input_path.exists():
            raise ExperimentVisualizationError(f"Input CSV not found: {input_path}")

        module = cls._load_experiment_visualizer_module()
        df, _ = cls._load_experiment_data(
            module=module,
            input_path=input_path,
            require_solved=False,
        )

        if "algorithm" not in df.columns:
            raise ExperimentVisualizationError("experiment.csv is missing 'algorithm' column.")

        algorithms = sorted(
            {
                str(value).strip()
                for value in df["algorithm"].dropna()
                if str(value).strip()
            }
        )
        if not algorithms:
            raise ExperimentVisualizationError("No algorithm values found in experiment.csv.")
        return algorithms

    @classmethod
    def _filter_solved_rows_by_algorithms(
        cls,
        df: Any,
        df_solved: Any,
        selected_algorithms: Optional[List[str]],
    ) -> Any:
        """Filter experiment data to selected algorithms and solved rows."""
        if "algorithm" not in df.columns:
            raise ExperimentVisualizationError("experiment.csv is missing 'algorithm' column.")
        if selected_algorithms is None:
            if len(df_solved.index) == 0:
                raise ExperimentVisualizationError(
                    "experiment.csv has no solved rows to visualize."
                )
            return df_solved

        cleaned_selection = [algo.strip() for algo in selected_algorithms if algo and algo.strip()]
        if not cleaned_selection:
            raise ExperimentVisualizationError(
                "Please select at least one algorithm to visualize."
            )

        available = {
            str(value).strip()
            for value in df["algorithm"].dropna()
            if str(value).strip()
        }
        missing = [algo for algo in cleaned_selection if algo not in available]
        if missing:
            raise ExperimentVisualizationError(
                "Selected algorithm(s) not found in CSV: " + ", ".join(sorted(missing))
            )

        df_by_algo = df[
            df["algorithm"].astype(str).str.strip().isin(cleaned_selection)
        ]
        if len(df_by_algo.index) == 0:
            raise ExperimentVisualizationError(
                "No CSV rows found for selected algorithm(s)."
            )
        if "solution_found" not in df_by_algo.columns:
            raise ExperimentVisualizationError(
                "experiment.csv is missing 'solution_found' column."
            )

        solved_mask = (
            df_by_algo["solution_found"].eq(True)
            | df_by_algo["solution_found"].astype(str).str.lower().eq("true")
        )
        filtered_solved = df_by_algo[solved_mask].copy()
        if len(filtered_solved.index) == 0:
            raise ExperimentVisualizationError(
                "Selected algorithm(s) have no solved rows to visualize."
            )

        return filtered_solved

    @classmethod
    def stream_experiment_visualizations(
        cls,
        csv_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        selected_algorithms: Optional[List[str]] = None,
    ) -> Generator[ExperimentVisualizationProgress, None, None]:
        """
        Generate experiment charts one-by-one and emit progress events.

        Args:
            csv_path: CSV input path. Defaults to <project_root>/experiment.csv.
            output_dir: Output directory. Defaults to <project_root>/charts.
            selected_algorithms: Optional algorithm labels to include.

        Yields:
            ExperimentVisualizationProgress for each generated chart.
        """
        input_path = csv_path or (cls.PROJECT_ROOT / "experiment.csv")
        charts_dir = output_dir or (cls.PROJECT_ROOT / "charts")

        if not input_path.exists():
            raise ExperimentVisualizationError(f"Input CSV not found: {input_path}")

        charts_dir.mkdir(parents=True, exist_ok=True)
        module = cls._load_experiment_visualizer_module()
        df, df_solved = cls._load_experiment_data(
            module=module,
            input_path=input_path,
            require_solved=False,
        )
        filtered_solved = cls._filter_solved_rows_by_algorithms(
            df=df,
            df_solved=df_solved,
            selected_algorithms=selected_algorithms,
        )

        total_steps = len(cls.EXPERIMENT_CHART_STEPS)
        for step_index, (chart_name, filename, plot_fn_name) in enumerate(
            cls.EXPERIMENT_CHART_STEPS,
            start=1,
        ):
            plot_fn = getattr(module, plot_fn_name, None)
            if plot_fn is None:
                raise ExperimentVisualizationError(
                    f"Visualization function not found: {plot_fn_name}"
                )

            try:
                plot_fn(filtered_solved, charts_dir)
            except Exception as exc:
                raise ExperimentVisualizationError(
                    f"Failed to generate chart step {step_index}/{total_steps} "
                    f"'{chart_name}': {exc}"
                ) from exc

            chart_path = charts_dir / filename
            if not chart_path.exists():
                raise ExperimentVisualizationError(
                    f"Chart step {step_index}/{total_steps} '{chart_name}' did not "
                    f"produce expected file: {chart_path}"
                )

            yield ExperimentVisualizationProgress(
                step=step_index,
                total=total_steps,
                chart_name=chart_name,
                chart_path=chart_path,
            )

    @classmethod
    def generate_experiment_visualizations(
        cls,
        csv_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        selected_algorithms: Optional[List[str]] = None,
    ) -> List[Path]:
        """
        Generate experiment chart images from experiment.csv.

        Args:
            csv_path: CSV input path. Defaults to <project_root>/experiment.csv.
            output_dir: Output directory. Defaults to <project_root>/charts.
            selected_algorithms: Optional algorithm labels to include.

        Returns:
            Ordered list of generated chart paths.
        """
        chart_paths = [
            progress.chart_path
            for progress in cls.stream_experiment_visualizations(
                csv_path=csv_path,
                output_dir=output_dir,
                selected_algorithms=selected_algorithms,
            )
        ]

        if not chart_paths:
            raise ExperimentVisualizationError(
                "No chart files were generated during experiment visualization"
            )

        return chart_paths


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_astar_label(label: str) -> str:
    """
    Convert raw A* snapshot label into a human-friendly message.

    Input examples:
        "assign (0,7)=9 g=32 h=49"       → "Assigned 9 to cell (row 1, col 8)  |  f=81  [g=32, h=49]"
        "PRUNED (0,7)=9"                  → "Pruned value 9 at cell (row 1, col 8) — no valid domain"
        "expand g=32 h=49 f=81"           → "Expanding node  |  f=81  [g=32, h=49]"
    """
    import re

    # --- assign (r,c)=v g=G h=H ---
    m = re.match(r"assign\s+\((\d+),\s*(\d+)\)=(\d+)", label)
    if m:
        r, c, v = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"Assigned {v} to cell (row {r+1}, col {c+1})"

    # --- PRUNED (r,c)=v ---
    m = re.match(r"PRUNED\s+\((\d+),\s*(\d+)\)=(\d+)", label)
    if m:
        r, c, v = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"Pruned value {v} at cell (row {r+1}, col {c+1}) — domain became empty"

    # --- expand g=G h=H f=F ---
    m = re.match(r"expand\s+", label)
    if m:
        return "Expanding node"

    # fallback — return as-is but capitalised
    return label.capitalize()


def _parse_cell_from_label(label: str) -> Optional[Tuple[int, int]]:
    """
    Try to extract (row, col) from A* snapshot labels.

    Label formats:
        "assign (r,c)=v g=... h=..."
        "PRUNED (r,c)=v"
        "expand g=... h=... f=..."  ← no cell
    """
    import re
    match = re.search(r"\((\d+),\s*(\d+)\)", label)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


__all__ = [
    "VisualizationService",
    "StepState",
    "ComparisonResult",
    "ExperimentVisualizationProgress",
    "ExperimentVisualizationError",
]
