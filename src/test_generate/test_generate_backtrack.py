import random
import argparse
import os
import sys

                                                     
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solver import count_backtracks

                                                                             
                                               
                                                                             
                                                                                 
                                                                           
                                                         
                                                                      

DIFFICULTY_THRESHOLDS = {
    "easy":   (0, 50),
    "medium": (50, 500),
    "hard":   (500, float("inf")),
}
                                                                   
                                                                

                                               
                                                               
                                                                    
                                  
DIFFICULTY_STRIP = {
    "easy":   0.6,
    "medium": 0.4,
    "hard":   0.2,
}

                                                             
                                                                               
CONSTRAINT_KEEP = 0.5

MAX_ATTEMPTS = 1000                                                       


                                                                             
                         
                                                                             

def generate_latin_square(n):
    """Generate a random valid N×N Latin Square (values 1..N)."""
    base = [[((i + j) % n) + 1 for j in range(n)] for i in range(n)]

    rows = list(range(n))
    random.shuffle(rows)
    grid = [base[r] for r in rows]

    cols = list(range(n))
    random.shuffle(cols)
    grid = [[row[c] for c in cols] for row in grid]

    mapping = list(range(1, n + 1))
    random.shuffle(mapping)
    grid = [[mapping[v - 1] for v in row] for row in grid]

    return grid


                                                                             
                       
                                                                             

def extract_horizontal_constraints(grid, n):
    """
    Returns N lines, each with N-1 values.
    1 = left < right, -1 = left > right
    """
    constraints = []
    for row in range(n):
        row_constraints = []
        for col in range(n - 1):
            left = grid[row][col]
            right = grid[row][col + 1]
            row_constraints.append(1 if left < right else -1)
        constraints.append(row_constraints)
    return constraints


def extract_vertical_constraints(grid, n):
    """
    Returns N-1 lines, each with N values.
    1 = top < bottom, -1 = top > bottom
    """
    constraints = []
    for row in range(n - 1):
        row_constraints = []
        for col in range(n):
            top = grid[row][col]
            bottom = grid[row + 1][col]
            row_constraints.append(1 if top < bottom else -1)
        constraints.append(row_constraints)
    return constraints


def apply_sparsity(constraints, keep_probability):
    """Randomly zero out constraints based on keep_probability."""
    return [
        [v if random.random() < keep_probability else 0 for v in row]
        for row in constraints
    ]


                                                                             
                
                                                                             

def strip_grid_cells(grid, n, keep_probability):
    """Randomly set cells to 0 (empty) based on keep_probability."""
    puzzle = []
    for row in range(n):
        puzzle_row = []
        for col in range(n):
            if random.random() < keep_probability:
                puzzle_row.append(grid[row][col])
            else:
                puzzle_row.append(0)
        puzzle.append(puzzle_row)
    return puzzle


                                                                             
             
                                                                             

def format_row(values):
    """Format a list of integers as a comma-separated string."""
    return ", ".join(str(v) for v in values)


def write_puzzle_file(filepath, n, puzzle_grid, h_constraints, v_constraints):
    """Write the puzzle to a file in the required format."""
    lines = []
    lines.append(str(n))
    for row in puzzle_grid:
        lines.append(format_row(row))
    for row in h_constraints:
        lines.append(format_row(row))
    for row in v_constraints:
        lines.append(format_row(row))
    with open(filepath, "w") as f:
        f.write("\n".join(lines) + "\n")


                                                                             
           
                                                                             

def generate(n, difficulty="medium", seed=None, output_dir=".", filename=None):
    """
    Generate a Futoshiki puzzle of size N whose difficulty is determined by
    how many backtracks the solver needs to solve it:

        easy:   0-4   backtracks  (constraint propagation is enough)
        medium: 5-20  backtracks  (some guessing required)
        hard:   21+   backtracks  (significant trial-and-error)

    Retries up to MAX_ATTEMPTS times until a puzzle lands in the target band.
    """
    if seed is not None:
        random.seed(seed)

    low, high = DIFFICULTY_THRESHOLDS[difficulty]
    cell_keep = DIFFICULTY_STRIP[difficulty]

                                                                           
    solution = generate_latin_square(n)

                                                            
    full_h = extract_horizontal_constraints(solution, n)
    full_v = extract_vertical_constraints(solution, n)

    puzzle_grid = None
    h_constraints = None
    v_constraints = None
    actual_backtracks = -1
    bt = -1

    for attempt in range(1, MAX_ATTEMPTS + 1):
                                                
        h_constraints = apply_sparsity(full_h, CONSTRAINT_KEEP)
        v_constraints = apply_sparsity(full_v, CONSTRAINT_KEEP)

                                  
        puzzle_grid = strip_grid_cells(solution, n, cell_keep)

                                                                              
        bt = count_backtracks(n, puzzle_grid, h_constraints, v_constraints)

        if bt == -1:
            continue                                 

        if low <= bt <= high:
            actual_backtracks = bt
            break                                              
    else:
        print(
            f"Warning: could not reach {difficulty} difficulty in "
            f"{MAX_ATTEMPTS} attempts. Using last puzzle (backtracks: {bt})."
        )
        actual_backtracks = bt

                           
    if filename is None:
        filename = f"futoshiki_{n}x{n}_{difficulty}.txt"
    filepath = os.path.join(output_dir, filename)

    write_puzzle_file(filepath, n, puzzle_grid, h_constraints, v_constraints)

    high_str = str(int(high)) if high != float("inf") else "inf"
    print(f"Generated : {filepath}")
    print(f"  Grid size  : {n}x{n}")
    print(f"  Difficulty : {difficulty}  (target: {low}-{high_str} backtracks)")
    print(f"  Backtracks : {actual_backtracks}")
    if seed is not None:
        print(f"  Seed       : {seed}")

    return filepath, solution


                                                                             
     
                                                                             

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Futoshiki puzzle generator")
    parser.add_argument("n", type=int, help="Grid size (e.g. 4 for a 4x4 puzzle)")
    parser.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        default="medium",
        help="Puzzle difficulty based on solver backtrack count (default: medium)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory to write puzzle files (default: current directory)",
    )
    parser.add_argument(
        "--filename",
        default=None,
        help="Output filename (default: futoshiki_NxN_difficulty.txt)",
    )

    args = parser.parse_args()

    generate(
        n=args.n,
        difficulty=args.difficulty,
        seed=args.seed,
        output_dir=args.output_dir,
        filename=args.filename,
    )