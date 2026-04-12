
#!/usr/bin/env python3
"""
Experiment Runner for Futoshiki AI Solvers

This script runs all available solvers on a collection of puzzles
and generates experiment.csv with detailed metrics for analysis.

Usage:
    python run_experiments.py
    python run_experiments.py --puzzles-dir ../../test_generate
    python run_experiments.py --timeout 300 --output ../../experiment.csv
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import csv
import psutil
import os

# Add parent directories to path for imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))

from core.problem.parser import ParserFactory, FutoshikiData, AlgorithmAdapter
from core.solvers.base_solver import SolverFactory, BaseSolver
from core.utils.metrics import SolverMetrics, MetricsStore

# Import all solvers to register them
from core.solvers import backtrack, astar, forward_chaining, backward_chaining


def get_puzzle_files(puzzle_dir: Path) -> List[Path]:
    """Get all .txt puzzle files from directory, sorted by name."""
    if not puzzle_dir.exists():
        raise FileNotFoundError(f"Puzzle directory not found: {puzzle_dir}")
    
    puzzle_files = sorted(puzzle_dir.glob("futoshiki_*.txt"))
    # Exclude no_solve puzzles for benchmarking
    puzzle_files = [p for p in puzzle_files if "no_solve" not in p.name]
    
    return puzzle_files


def parse_puzzle_metadata(puzzle_path: Path) -> Dict[str, str]:
    """Extract metadata from puzzle filename.
    
    Example: futoshiki_5x5_medium.txt -> {size: '5x5', difficulty: 'medium'}
    """
    name = puzzle_path.stem  # futoshiki_5x5_medium
    parts = name.split("_")
    
    metadata = {
        "puzzle_id": puzzle_path.stem,
        "size": "unknown",
        "difficulty": "unknown"
    }
    
    if len(parts) >= 2:
        metadata["size"] = parts[1]  # 5x5
    if len(parts) >= 3:
        metadata["difficulty"] = parts[2]  # medium
    
    return metadata


def run_solver_with_timeout(
    solver_name: str,
    puzzle_data: FutoshikiData,
    puzzle_metadata: Dict[str, str],
    timeout: float = 300.0
) -> Optional[SolverMetrics]:
    """Run a single solver on a puzzle and collect metrics.
    
    Args:
        solver_name: Name of the solver (e.g., 'backtracking', 'astar')
        puzzle_data: Parsed puzzle data
        puzzle_metadata: Metadata extracted from filename
        timeout: Maximum time in seconds
        
    Returns:
        SolverMetrics object or None if solver failed
    """
    print(f"  Running {solver_name}...", end=" ", flush=True)
    
    try:
        # Convert puzzle data to appropriate format for each solver
        adapter = AlgorithmAdapter(puzzle_data)
        if solver_name.lower() == 'astar':
            problem_data = adapter.to_astar()
        else:
            # Other solvers expect FutoshikiData directly
            problem_data = puzzle_data
        
        # Create solver instance
        solver = SolverFactory.create(solver_name, problem_data)
        solver.metrics.puzzle_id = puzzle_metadata["puzzle_id"]
        
        # Add metadata to metrics
        solver.metrics.add_extra("grid_size", puzzle_metadata["size"])
        solver.metrics.add_extra("difficulty", puzzle_metadata["difficulty"])
        
        # Get process for memory tracking
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024  # KB
        
        # Start timing
        solver.metrics.start()
        start_time = time.time()
        
        # Run solver
        result = solver.solve()
        
        # Stop timing
        elapsed = time.time() - start_time
        solver.metrics.stop()
        
        # Check timeout
        if elapsed > timeout:
            solver.metrics.mark_timeout()
            print(f"TIMEOUT ({elapsed:.1f}s)")
            return solver.metrics
        
        # Get memory usage
        mem_after = process.memory_info().rss / 1024  # KB
        mem_used = max(0, mem_after - mem_before)
        solver.metrics.add_extra("memory_kb", round(mem_used, 2))
        
        # Check if solution found
        if result is not None:
            solver.metrics.mark_solved(True)
            print(f"✓ ({elapsed:.3f}s, {solver.metrics.nodes_expanded} nodes)")
        else:
            solver.metrics.mark_solved(False)
            print(f"✗ No solution ({elapsed:.3f}s)")
        
        return solver.metrics
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        # Create error metrics
        metrics = SolverMetrics(algorithm=solver_name)
        metrics.puzzle_id = puzzle_metadata["puzzle_id"]
        metrics.mark_error(str(e))
        metrics.add_extra("grid_size", puzzle_metadata["size"])
        metrics.add_extra("difficulty", puzzle_metadata["difficulty"])
        return metrics


def run_experiments(
    puzzle_dir: Path,
    output_path: Path,
    timeout: float = 300.0,
    solvers: Optional[List[str]] = None
) -> None:
    """Run all experiments and save results to CSV.
    
    Args:
        puzzle_dir: Directory containing puzzle files
        output_path: Path to output CSV file
        timeout: Maximum time per solver run in seconds
        solvers: List of solver names to run (None = default solvers, excluding backward_chaining)
    """
    # Get available solvers
    available_solvers = list(SolverFactory.registered_solvers().keys())
    
    if solvers is None:
        # Default: run all solvers EXCEPT backward_chaining
        # (backward_chaining can still be run if explicitly specified)
        solvers_to_run = [s for s in available_solvers if s != 'backward_chaining']
    else:
        solvers_to_run = [s.lower() for s in solvers if s.lower() in available_solvers]
    
    if not solvers_to_run:
        print(f"No valid solvers found. Available: {available_solvers}")
        return
    
    print(f"Running experiments with solvers: {solvers_to_run}")
    print(f"Timeout: {timeout}s per solver")
    print("-" * 70)
    
    # Get puzzle files
    puzzle_files = get_puzzle_files(puzzle_dir)
    print(f"Found {len(puzzle_files)} puzzles")
    print()
    
    # Metrics store
    store = MetricsStore()
    
    # Run experiments
    for i, puzzle_path in enumerate(puzzle_files, 1):
        print(f"[{i}/{len(puzzle_files)}] {puzzle_path.name}")
        
        # Parse puzzle
        try:
            puzzle_data = ParserFactory.get_standard_data(str(puzzle_path))
            metadata = parse_puzzle_metadata(puzzle_path)
        except Exception as e:
            print(f"  ERROR parsing puzzle: {e}")
            continue
        
        # Run each solver
        for solver_name in solvers_to_run:
            metrics = run_solver_with_timeout(
                solver_name,
                puzzle_data,
                metadata,
                timeout
            )
            
            if metrics:
                store.add(metrics)
        
        print()
    
    # Save results
    print("=" * 70)
    print(f"Saving results to {output_path}")
    
    # Convert to simplified CSV format
    save_experiment_csv(store, output_path)
    
    print(f"✓ Done! Ran {len(store.all())} experiments")
    print_summary(store)


def save_experiment_csv(store: MetricsStore, output_path: Path) -> None:
    """Save metrics to experiment.csv with simplified format."""
    
    rows = []
    for metrics in store.all():
        row = {
            "puzzle_id": metrics.puzzle_id or "unknown",
            "algorithm": metrics.algorithm,
            "grid_size": metrics.extra.get("grid_size", "unknown"),
            "difficulty": metrics.extra.get("difficulty", "unknown"),
            "time_ms": round(metrics.elapsed_seconds * 1000, 2),
            "nodes_explored": metrics.nodes_expanded,
            "nodes_generated": metrics.nodes_generated,
            "memory_kb": metrics.extra.get("memory_kb", 0),
            "solution_found": metrics.solved,
            "assignments": metrics.assignments,
            "backtracks": metrics.backtracks,
            "constraint_checks": metrics.constraint_checks,
            "timed_out": metrics.timed_out,
            "error": metrics.error or "",
        }
        rows.append(row)
    
    # Write CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not rows:
        output_path.write_text("", encoding="utf-8")
        return
    
    fieldnames = list(rows[0].keys())
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(store: MetricsStore) -> None:
    """Print summary statistics."""
    all_metrics = store.all()
    
    if not all_metrics:
        return
    
    print()
    print("Summary by Algorithm:")
    print("-" * 70)
    
    # Group by algorithm
    by_algo: Dict[str, List[SolverMetrics]] = {}
    for m in all_metrics:
        if m.algorithm not in by_algo:
            by_algo[m.algorithm] = []
        by_algo[m.algorithm].append(m)
    
    # Print stats for each
    for algo, metrics_list in sorted(by_algo.items()):
        solved = sum(1 for m in metrics_list if m.solved)
        total = len(metrics_list)
        avg_time = sum(m.elapsed_seconds for m in metrics_list) / total
        avg_nodes = sum(m.nodes_expanded for m in metrics_list) / total
        
        print(f"{algo:20s}: {solved}/{total} solved, "
              f"avg time: {avg_time:.3f}s, avg nodes: {avg_nodes:.0f}")


def main():
    parser = argparse.ArgumentParser(
        description="Run Futoshiki solver experiments and generate CSV"
    )
    parser.add_argument(
        "--puzzles-dir",
        type=Path,
        default=None,
        help="Directory containing puzzle files (default: src/test_generate)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV file path (default: experiment.csv in project root)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Timeout per solver in seconds (default: 300)"
    )
    parser.add_argument(
        "--solvers",
        nargs="+",
        default=None,
        help="Solvers to run (default: backtracking, astar, forward_chaining). Use 'backward_chaining' to include it explicitly."
    )
    
    args = parser.parse_args()
    
    # Determine paths
    if args.puzzles_dir is None:
        # Default to src/test_generate
        script_dir = Path(__file__).parent
        puzzles_dir = script_dir.parent.parent / "test_generate"
    else:
        puzzles_dir = args.puzzles_dir
    
    if args.output is None:
        # Default to project root
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent.parent
        output_path = project_root / "experiment.csv"
    else:
        output_path = args.output
    
    # Run experiments
    run_experiments(
        puzzle_dir=puzzles_dir,
        output_path=output_path,
        timeout=args.timeout,
        solvers=args.solvers
    )


if __name__ == "__main__":
    main()
