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
from core.utils.metrics import GLOBAL_METRICS_STORE
from core.problem.parser import ParserFactory, FutoshikiData


def validate_solution(n: int, solution: list, h_constraints: list, v_constraints: list) -> bool:
	"""Validate a Futoshiki solution.
	
	Args:
		n: Grid size
		solution: NxN grid with values 1 to n
		h_constraints: Horizontal constraints (1 means <, -1 means >, 0 means none)
		v_constraints: Vertical constraints (1 means <, -1 means >, 0 means none)
	
	Returns:
		True if solution is valid, False otherwise
	"""
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
			if constraint == 1:  # left < right
				if solution[i][j] >= solution[i][j + 1]:
					return False
			elif constraint == -1:  # left > right
				if solution[i][j] <= solution[i][j + 1]:
					return False
	
	# Check vertical constraints
	for i in range(n - 1):
		for j in range(n):
			constraint = v_constraints[i][j] if j < len(v_constraints[i]) else 0
			if constraint == 1:  # top < bottom
				if solution[i][j] >= solution[i + 1][j]:
					return False
			elif constraint == -1:  # top > bottom
				if solution[i][j] <= solution[i + 1][j]:
					return False
	
	return True


def save_solution(puzzle_name: str, n: int, solution: list, results_dir: Path) -> Path:
	"""Save solution to a .txt file in results folder.
	
	Args:
		puzzle_name: Name of the puzzle (without extension)
		n: Grid size
		solution: NxN grid with values
		results_dir: Results directory path
	
	Returns:
		Path to saved file
	"""
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
		solver_name: "backtracking" or "forward_chaining"
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

	# Clear metrics store for this test run
	GLOBAL_METRICS_STORE.clear()

	for puzzle_file in puzzle_files:
		puzzle_name = puzzle_file.stem
		try:
			# Parse puzzle using FutoshikiData from parser
			futoshiki_data = ParserFactory.get_standard_data(str(puzzle_file))
			n = futoshiki_data.size
			h_constraints = futoshiki_data.h_constraints
			v_constraints = futoshiki_data.v_constraints

			# Use SolverFactory for both solvers uniformly
			solver = SolverFactory.create(solver_name, futoshiki_data)
			result = solver.solve()

			solution = result.get("solution") if result else None
			status = result.get("status") if result else "none"

			if solution is not None:
				# Validate the solution
				if validate_solution(n, solution, h_constraints, v_constraints):
					save_solution(puzzle_name, n, solution, results_dir)
					print(f"✓ {puzzle_file.name}: SOLVED and VALIDATED")
					passed += 1
				else:
					print(f"✗ {puzzle_file.name}: SOLVED but INVALID")
					invalid += 1
			else:
				print(f"✗ {puzzle_file.name}: NO SOLUTION")
				failed += 1
		except Exception as e:
			print(f"✗ {puzzle_file.name}: ERROR - {e}")
			errors += 1

	print(f"\n{'='*60}")
	print(f"Results: {passed} solved | {failed} no solution | {invalid} invalid | {errors} errors")
	print(f"Solutions saved to: {results_dir}")
	
	# Save metrics if available
	if GLOBAL_METRICS_STORE.all():
		metrics_file = results_dir / f"metrics_{solver_name}.json"
		GLOBAL_METRICS_STORE.save_json(metrics_file)
		print(f"Metrics saved to: {metrics_file}")
	
	print(f"{'='*60}\n")


if __name__ == "__main__":
	import argparse
	
	parser = argparse.ArgumentParser(description="Test Futoshiki puzzles with different solvers")
	parser.add_argument(
		"--solver",
		choices=["backtracking", "forward_chaining"],
		default="backtracking",
		help="Which solver to use (default: backtracking)"
	)
	
	args = parser.parse_args()
	run_tests(solver_name=args.solver)