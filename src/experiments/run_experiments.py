
                      
"""
Experiment runner for Futoshiki AI solvers.

Usage:
    python src/main.py experiments run --timeout 300
    python src/main.py experiments run --puzzles-dir src/test_generate --output experiment.csv
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
import importlib

current_dir = Path(__file__).parent
src_dir = current_dir.parent
sys.path.insert(0, str(src_dir))

# Dynamically import all solver modules to register them
solver_modules = ['astar', 'backtracking', 'backward_chaining', 'bruteforce', 'forward_chaining']
for mod_name in solver_modules:
    try:
        importlib.import_module(f'core.solvers.{mod_name}')
    except ImportError:
        pass  # Skip if module doesn't exist

from core.problem.parser import ParserFactory, FutoshikiData, AlgorithmAdapter
from core.solvers.base_solver import SolverFactory, BaseSolver
from core.utils.metrics import SolverMetrics, MetricsStore

def get_puzzle_files(puzzle_dir: Path) -> List[Path]:
    """Get all .txt puzzle files from directory, sorted by name."""
    if not puzzle_dir.exists():
        raise FileNotFoundError(f"Puzzle directory not found: {puzzle_dir}")
    
    puzzle_files = sorted(puzzle_dir.glob("input_*.txt"))
                                               
    puzzle_files = [p for p in puzzle_files if "no_solve" not in p.name]
    
    return puzzle_files


def parse_puzzle_metadata(puzzle_path: Path) -> Dict[str, str]:
    """Extract metadata from puzzle filename.
    
    Example: futoshiki_5x5_medium.txt -> {size: '5x5', difficulty: 'medium'}
    """
    name = puzzle_path.stem                        
    parts = name.split("_")
    
    metadata = {
        "puzzle_id": puzzle_path.stem,
        "size": "unknown",
        "difficulty": "unknown"
    }
    
    if len(parts) >= 2:
        metadata["size"] = parts[1]       
    if len(parts) >= 3:
        metadata["difficulty"] = parts[2]          
    
    return metadata


def format_solution(grid: List[List[int]], h_constraints: List[List[int]], v_constraints: List[List[int]]) -> str:
    """Format the solved grid with inequality signs."""
    n = len(grid)
    lines = []
    
    for r in range(n):
        row_parts = []
        for c in range(n):
            row_parts.append(str(grid[r][c]))
            if c < n - 1:
                if h_constraints[r][c] == 1:
                    row_parts.append("<")
                elif h_constraints[r][c] == -1:
                    row_parts.append(">")
                else:
                    row_parts.append(" ")
        lines.append(" ".join(row_parts))
    
    # Insert vertical constraint lines
    for r in range(n - 1):
        v_parts = []
        for c in range(n):
            if v_constraints[r][c] == 1:
                v_parts.append("^")
            elif v_constraints[r][c] == -1:
                v_parts.append("v")
            else:
                v_parts.append(" ")
            if c < n - 1:
                v_parts.append(" ")
        lines.insert(2 * r + 1, " ".join(v_parts))
    
    return "\n".join(lines)


def run_solver_with_timeout(
    solver_name: str,
    puzzle_data: FutoshikiData,
    puzzle_metadata: Dict[str, str],
    timeout: float = 300.0
) -> Tuple[Optional[SolverMetrics], Optional[List[List[int]]]]:
    print(f"  Running {solver_name}...", end=" ", flush=True)
    
    try:
                                                                   
        adapter = AlgorithmAdapter(puzzle_data)
        if solver_name.lower() == 'astar':
            problem_data = adapter.to_astar()
        else:
                                                         
            problem_data = puzzle_data
        
                                
        solver = SolverFactory.create(solver_name, problem_data)
        solver.metrics.puzzle_id = puzzle_metadata["puzzle_id"]
        
                                 
        solver.metrics.add_extra("grid_size", puzzle_metadata["size"])
        solver.metrics.add_extra("difficulty", puzzle_metadata["difficulty"])
        
                                         
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024      
        
                      
        solver.metrics.start()
        start_time = time.time()
        
                    
        result = solver.solve()
        
                     
        elapsed = time.time() - start_time
        solver.metrics.stop()
        
                       
        if elapsed > timeout:
            solver.metrics.mark_timeout()
            print(f"TIMEOUT ({elapsed:.1f}s)")
            return solver.metrics, None
        
                          
        mem_after = process.memory_info().rss / 1024      
        mem_used = max(0, mem_after - mem_before)
        solver.metrics.add_extra("memory_kb", round(mem_used, 2))
        
        # Extract solution
        if isinstance(result, dict):
            solution = result.get("solution")
        elif isinstance(result, list):
            solution = result
        else:
            solution = None
                                 
        if solution is not None:
            solver.metrics.mark_solved(True)
            print(f"✓ ({elapsed:.3f}s, {solver.metrics.nodes_expanded} nodes)")
        else:
            solver.metrics.mark_solved(False)
            print(f"✗ No solution ({elapsed:.3f}s)")
        
        return solver.metrics, solution
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
                              
        metrics = SolverMetrics(algorithm=solver_name)
        metrics.puzzle_id = puzzle_metadata["puzzle_id"]
        metrics.mark_error(str(e))
        metrics.add_extra("grid_size", puzzle_metadata["size"])
        metrics.add_extra("difficulty", puzzle_metadata["difficulty"])
        return metrics, None


def run_experiments(
    puzzle_dir: Path,
    output_path: Path,
    timeout: float = 300.0,
    solvers: Optional[List[str]] = None
) -> None:
    available_solvers = list(SolverFactory.registered_solvers().keys())
    
    if solvers is None:                                                 
        solvers_to_run = [s for s in available_solvers]
    else:
        solvers_to_run = [s.lower() for s in solvers if s.lower() in available_solvers]
    
    if not solvers_to_run:
        print(f"No valid solvers found. Available: {available_solvers}")
        return
    
    print(f"Running experiments with solvers: {solvers_to_run}")
    print(f"Timeout: {timeout}s per solver")
    print("-" * 70)
    
                      
    puzzle_files = get_puzzle_files(puzzle_dir)
    print(f"Found {len(puzzle_files)} puzzles")
    print()
    
    store = MetricsStore()
    
    for i, puzzle_path in enumerate(puzzle_files, 1):
        print(f"[{i}/{len(puzzle_files)}] {puzzle_path.name}")
        
                      
        try:
            puzzle_data = ParserFactory.get_standard_data(str(puzzle_path))
            metadata = parse_puzzle_metadata(puzzle_path)
        except Exception as e:
            print(f"  ERROR parsing puzzle: {e}")
            continue
        
                         
        for solver_name in solvers_to_run:
            metrics, solution = run_solver_with_timeout(
                solver_name,
                puzzle_data,
                metadata,
                timeout
            )
            
            if metrics:
                store.add(metrics)
            
            if solution is not None:
                output_name = metadata["puzzle_id"].replace("input_", "output_")
                output_dir = Path("Outputs") / solver_name
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / f"{output_name}.txt"
                formatted = format_solution(solution, puzzle_data.h_constraints, puzzle_data.v_constraints)
                output_file.write_text(formatted)
                print(f"Solution for {output_name} by {solver_name}:\n{formatted}\n")
        
        print()
    
                  
    print("=" * 70)
    print(f"Saving results to {output_path}")
    
                                      
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
    
                        
    by_algo: Dict[str, List[SolverMetrics]] = {}
    for m in all_metrics:
        if m.algorithm not in by_algo:
            by_algo[m.algorithm] = []
        by_algo[m.algorithm].append(m)
    
                          
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
        help="Directory containing puzzle files (default: Output/)"
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
    
    if args.puzzles_dir is None:
        script_dir = Path(__file__).parent
        puzzles_dir = script_dir.parent.parent / "Inputs"
    else:
        puzzles_dir = args.puzzles_dir
    
    if args.output is None:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent
        output_path = project_root / "experiment.csv"
    else:
        output_path = args.output
    
    run_experiments(
        puzzle_dir=puzzles_dir,
        output_path=output_path,
        timeout=args.timeout,
        solvers=args.solvers
    )


if __name__ == "__main__":
    main()
