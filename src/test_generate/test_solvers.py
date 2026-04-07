"""Simple test runner for Futoshiki puzzles."""
import os
import sys
from pathlib import Path

# Add current dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Add src to path for imports from core
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from core.solvers.base_solver import SolverFactory
from core.solvers.forward_chaining import ForwardChainingSolver
from core.solvers.backtrack import BacktrackingSolver
import core.solvers.astar  # noqa: F401 — triggers @SolverFactory.register("astar")
from core.utils.metrics import GLOBAL_METRICS_STORE
from core.problem.parser import ParserFactory, AlgorithmAdapter, FutoshikiData


def validate_solution(n: int, solution: list, h_constraints: list, v_constraints: list) -> bool:
	"""Validate a Futoshiki solution."""
	# Check each row has 1 to n
	for row in solution:
		if sorted(row) != list(range(1, n + 1)):
			return False
	
	# Check each column has 1 to n
	for col in range(n):
		column = [solution[row][col] for row in range(n)]
		if sorted(column) != list(range(1, n + 1)):
			return False
	
	# Check horizontal constraints
	for i in range(n):
		for j in range(n - 1):
			constraint = h_constraints[i][j] if j < len(h_constraints[i]) else 0
			if constraint == 1 and solution[i][j] >= solution[i][j + 1]:
				return False
			if constraint == -1 and solution[i][j] <= solution[i][j + 1]:
				return False
	
	# Check vertical constraints
	for i in range(n - 1):
		for j in range(n):
			constraint = v_constraints[i][j] if j < len(v_constraints[i]) else 0
			if constraint == 1 and solution[i][j] >= solution[i + 1][j]:
				return False
			if constraint == -1 and solution[i][j] <= solution[i + 1][j]:
				return False
	
	return True


def save_solution(puzzle_name: str, n: int, solution: list, results_dir: Path) -> Path:
	"""Save solution to a .txt file in results folder."""
	results_dir.mkdir(parents=True, exist_ok=True)
	output_file = results_dir / f"{puzzle_name}_solution.txt"
	with output_file.open("w", encoding="utf-8") as f:
		f.write(f"Solution for {puzzle_name}\n")
		f.write(f"Grid size: {n}x{n}\n")
		f.write("=" * (n * 2 + 1) + "\n")
		for row in solution:
			f.write(" ".join(str(val) for val in row) + "\n")
	return output_file


def run_tests(solver_name: str = "backtracking"):
	"""Run all futoshiki_*.txt puzzle files with specified solver.

	Args:
		solver_name: "backtracking", "forward_chaining", or "astar"
	"""
	test_dir = Path(os.path.dirname(os.path.abspath(__file__)))
	results_dir = test_dir / "results" / solver_name
	puzzle_files = sorted(test_dir.glob("futoshiki_*.txt"))

	if not puzzle_files:
		print("No puzzle files found!")
		return

	passed = 0
	failed = 0
	errors = 0
	invalid = 0

	print(f"\n{'='*60}")
	print(f"Running {len(puzzle_files)} tests with {solver_name}...")
	print(f"{'='*60}\n")

	GLOBAL_METRICS_STORE.clear()

	for puzzle_file in puzzle_files:
		puzzle_name = puzzle_file.stem
		try:
			futoshiki_data = ParserFactory.get_standard_data(str(puzzle_file))
			n = futoshiki_data.size
			h_constraints = futoshiki_data.h_constraints
			v_constraints = futoshiki_data.v_constraints

			# A* nhận dict từ AlgorithmAdapter; các solver khác nhận FutoshikiData
			if solver_name == "astar":
				problem = AlgorithmAdapter(futoshiki_data).to_astar()
			else:
				problem = futoshiki_data

			solver = SolverFactory.create(solver_name, problem)

			# Tắt snapshots khi chạy batch test (tiết kiệm memory)
			if solver_name == "astar":
				solver.record_snapshots = False

			result = solver.solve()

			solution = result.get("solution") if result else None
			metrics  = result.get("metrics")  if result else None

			# BT/FC trả metrics là dict (và đã tự add vào GLOBAL_METRICS_STORE)
			# A* trả SolverMetrics object (chưa add vào store)
			if metrics is not None and not isinstance(metrics, dict):
				metrics.puzzle_id = puzzle_name
				GLOBAL_METRICS_STORE.add(metrics)

			if solution is not None:
				if validate_solution(n, solution, h_constraints, v_constraints):
					save_solution(puzzle_name, n, solution, results_dir)
					_print_pass(puzzle_file.name, metrics)
					passed += 1
				else:
					print(f"✗ {puzzle_file.name}: SOLVED but INVALID")
					invalid += 1
			else:
				_print_fail(puzzle_file.name, metrics)
				failed += 1

		except Exception as e:
			import traceback
			print(f"✗ {puzzle_file.name}: ERROR - {e}")
			traceback.print_exc()
			errors += 1

	print(f"\n{'='*60}")
	print(f"Results: {passed} solved | {failed} no solution | {invalid} invalid | {errors} errors")
	print(f"Solutions saved to: {results_dir}")

	if GLOBAL_METRICS_STORE.all():
		metrics_file = results_dir / f"metrics_{solver_name}.json"
		GLOBAL_METRICS_STORE.save_json(metrics_file)
		print(f"Metrics saved to: {metrics_file}")

	print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# Print helpers
# ---------------------------------------------------------------------------

def _get(metrics, key: str, default=None):
	"""Lấy field từ metrics dù là dict hay SolverMetrics object."""
	if metrics is None:
		return default
	if isinstance(metrics, dict):
		return metrics.get(key, default)
	return getattr(metrics, key, default)


def _print_pass(filename: str, metrics) -> None:
	elapsed = _get(metrics, "elapsed_seconds", 0.0)
	expanded = _get(metrics, "nodes_expanded", 0)
	backtracks = _get(metrics, "backtracks", 0)
	time_s = f"{elapsed:.4f}s"
	extra = f" | expanded={expanded} backtracks={backtracks}" if expanded else ""
	print(f"✓ {filename}: SOLVED ({time_s}{extra})")


def _print_fail(filename: str, metrics) -> None:
	elapsed = _get(metrics, "elapsed_seconds", 0.0)
	time_s = f"{elapsed:.4f}s"
	print(f"✗ {filename}: NO SOLUTION ({time_s})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Test Futoshiki puzzles with different solvers")
	parser.add_argument(
		"--solver",
		choices=["backtracking", "forward_chaining", "astar"],
		default="forward_chaining",
		help="Which solver to use (default: backtracking)"
	)

	args = parser.parse_args()
	run_tests(solver_name=args.solver)