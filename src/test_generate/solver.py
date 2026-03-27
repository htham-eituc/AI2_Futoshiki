import argparse
import os


# ---------------------------------------------------------------------------
# File parser
# ---------------------------------------------------------------------------

def parse_puzzle_file(filepath):
    """
    Parse a Futoshiki puzzle file and return:
        n              - grid size
        grid           - n×n list of ints (0 = empty)
        h_constraints  - n lists of n-1 ints (1 = <, -1 = >, 0 = none)
        v_constraints  - (n-1) lists of n ints (1 = <, -1 = >, 0 = none)
    """
    with open(filepath) as f:
        lines = [line.strip() for line in f if line.strip()]

    idx = 0

    # Line 1: N
    n = int(lines[idx]); idx += 1

    # Lines 2 to N+1: grid
    grid = []
    for _ in range(n):
        row = [int(v.strip()) for v in lines[idx].split(",")]
        grid.append(row)
        idx += 1

    # Lines N+2 to 2N+1: horizontal constraints (N lines, N-1 values each)
    h_constraints = []
    for _ in range(n):
        row = [int(v.strip()) for v in lines[idx].split(",")]
        h_constraints.append(row)
        idx += 1

    # Lines 2N+2 to 3N: vertical constraints (N-1 lines, N values each)
    v_constraints = []
    for _ in range(n - 1):
        row = [int(v.strip()) for v in lines[idx].split(",")]
        v_constraints.append(row)
        idx += 1

    return n, grid, h_constraints, v_constraints


# ---------------------------------------------------------------------------
# Validity checks
# ---------------------------------------------------------------------------

def is_valid_placement(grid, n, row, col, value, h_constraints, v_constraints):
    """
    Check whether placing `value` at (row, col) is valid given:
    - No duplicate in the same row
    - No duplicate in the same column
    - All inequality constraints involving (row, col) are satisfied
      (only checked when both sides of the constraint are filled)
    """

    # --- Row uniqueness ---
    for c in range(n):
        if c != col and grid[row][c] == value:
            return False

    # --- Column uniqueness ---
    for r in range(n):
        if r != row and grid[r][col] == value:
            return False

    # --- Horizontal constraints for this row ---
    # Temporarily place the value to check constraints
    original = grid[row][col]
    grid[row][col] = value

    for c in range(n - 1):
        constraint = h_constraints[row][c]
        if constraint == 0:
            continue
        left = grid[row][c]
        right = grid[row][c + 1]
        if left == 0 or right == 0:
            continue  # One side empty — skip for now
        if constraint == 1 and not (left < right):
            grid[row][col] = original
            return False
        if constraint == -1 and not (left > right):
            grid[row][col] = original
            return False

    # --- Vertical constraints involving this cell ---
    for r in range(n - 1):
        constraint = v_constraints[r][col]
        if constraint == 0:
            continue
        top = grid[r][col]
        bottom = grid[r + 1][col]
        if top == 0 or bottom == 0:
            continue  # One side empty — skip for now
        if constraint == 1 and not (top < bottom):
            grid[row][col] = original
            return False
        if constraint == -1 and not (top > bottom):
            grid[row][col] = original
            return False

    grid[row][col] = original
    return True


# ---------------------------------------------------------------------------
# Solver (backtracking)
# ---------------------------------------------------------------------------

def find_empty_cell(grid, n):
    """Return the (row, col) of the next empty cell, or None if full."""
    for r in range(n):
        for c in range(n):
            if grid[r][c] == 0:
                return r, c
    return None


def solve(grid, n, h_constraints, v_constraints, solutions, counter, limit=2):
    """
    Backtracking solver. Fills `grid` in-place.
    Appends found solutions to `solutions` list.
    counter is a single-element list [int] used to track backtracks
    (mutable so it can be updated across recursive calls).
    Stops searching once `limit` solutions are found (default 2,
    enough to detect non-uniqueness without exhaustive search).

    Returns True if the search should stop early (limit reached).
    """
    if len(solutions) >= limit:
        return True  # Stop early

    cell = find_empty_cell(grid, n)

    if cell is None:
        # No empty cells — puzzle is complete
        solutions.append([row[:] for row in grid])  # Deep copy
        return len(solutions) >= limit

    row, col = cell

    for value in range(1, n + 1):
        if is_valid_placement(grid, n, row, col, value, h_constraints, v_constraints):
            grid[row][col] = value
            if solve(grid, n, h_constraints, v_constraints, solutions, counter, limit):
                return True  # Propagate early stop
            grid[row][col] = 0  # Backtrack
            counter[0] += 1     # Count each backtrack

    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def solve_puzzle(n, grid, h_constraints, v_constraints):
    """
    Solve a Futoshiki puzzle.

    Returns:
        status     - "unique", "multiple", or "none"
        solution   - solved grid, or None if no solution
        backtracks - number of backtracks the solver needed
    """
    working_grid = [row[:] for row in grid]  # Don't mutate the original
    solutions = []
    counter = [0]  # Mutable counter passed through recursion

    solve(working_grid, n, h_constraints, v_constraints, solutions, counter, limit=2)

    backtracks = counter[0]

    if len(solutions) == 0:
        return "none", None, backtracks
    elif len(solutions) == 1:
        return "unique", solutions[0], backtracks
    else:
        return "multiple", solutions[0], backtracks


def count_backtracks(n, grid, h_constraints, v_constraints):
    """
    Solve the puzzle and return only the backtrack count.
    Convenience function for the generator's difficulty check.
    Returns -1 if the puzzle has no unique solution.
    """
    status, _, backtracks = solve_puzzle(n, grid, h_constraints, v_constraints)
    if status != "unique":
        return -1
    return backtracks


def solve_from_file(filepath):
    """Parse a puzzle file and solve it. Returns (status, solution, backtracks, n)."""
    n, grid, h_constraints, v_constraints = parse_puzzle_file(filepath)
    status, solution, backtracks = solve_puzzle(n, grid, h_constraints, v_constraints)
    return status, solution, backtracks, n


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def format_grid_row(row, h_row):
    """
    Format a single grid row with horizontal constraints between cells.
    Empty cells (0) are displayed as a single space.
    h_row has N-1 values: 1 = '<', -1 = '>', 0 = ' '
    """
    h_chars = {1: "<", -1: ">", 0: " "}
    parts = []
    for col, val in enumerate(row):
        parts.append(str(val) if val != 0 else " ")
        if col < len(h_row):
            parts.append(h_chars[h_row[col]])
    return " ".join(parts)


def format_v_constraint_row(v_row):
    """
    Format a vertical constraint row.
    v_row has N values: 1 = 'v', -1 = '^', 0 = ' '
    Each symbol must align directly under its corresponding cell.

    Grid row pattern:  'X   X   X   X'
                        ^       ^
                        col0    col1 ...
    Each cell occupies 1 char, separated by 3 chars (' < ' or '   ').
    So each cell position is at index col * 4 in the string.
    We build the constraint row to the same width.
    """
    v_chars = {1: "v", -1: "^", 0: " "}
    n = len(v_row)
    # Total width of a grid row: n cells + (n-1) separators of 3 chars each
    # = n + (n-1)*3 = 4n - 3
    total_width = 4 * n - 3
    row_chars = [" "] * total_width
    for col, val in enumerate(v_row):
        pos = col * 4  # Each cell is at position col * 4
        row_chars[pos] = v_chars[val]
    return "".join(row_chars)


def print_grid(grid, n, h_constraints, v_constraints, label=""):
    """
    Print the Futoshiki grid with inline constraints.

    Example (4x4):
        1   2 < 3   4
            v
        1   2   3   4
        ^
        1   2 > 3   4
    """
    if label:
        print(f"\n{label}")

    for row in range(n):
        # Print grid row with horizontal constraints
        print(format_grid_row(grid[row], h_constraints[row]))

        # Print vertical constraint row (except after the last row)
        if row < n - 1:
            print(format_v_constraint_row(v_constraints[row]))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Futoshiki puzzle solver")
    parser.add_argument("filepath", help="Path to the puzzle file")
    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print(f"Error: file not found: {args.filepath}")
        exit(1)

    n, grid, h_constraints, v_constraints = parse_puzzle_file(args.filepath)

    print_grid(grid, n, h_constraints, v_constraints, label="Puzzle:")

    status, solution, backtracks = solve_puzzle(n, grid, h_constraints, v_constraints)

    if status == "unique":
        print(f"\nResult: Unique solution found ✓  (backtracks: {backtracks})")
        print_grid(solution, n, h_constraints, v_constraints, label="Solution:")
    elif status == "multiple":
        print(f"\nResult: Multiple solutions exist — puzzle is ambiguous ✗  (backtracks: {backtracks})")
        print_grid(solution, n, h_constraints, v_constraints, label="One possible solution:")
    else:
        print(f"\nResult: No solution exists — puzzle is invalid ✗  (backtracks: {backtracks})")