# Futoshiki Solver & Generator

A Python toolkit for generating and solving [Futoshiki](https://en.wikipedia.org/wiki/Futoshiki) puzzles — a Latin-square logic puzzle with inequality constraints between adjacent cells.

## Files

| File | Purpose |
|---|---|
| `solver.py` | Parses puzzle files and solves them via backtracking |
| `generator.py` | Generates valid, uniquely-solvable puzzles at a target difficulty |

## Puzzle File Format

```
N                          # grid size
row_1_values, ...          # N rows of grid (0 = empty cell)
h_constraint_rows, ...     # N rows of N-1 values (horizontal: 1=<, -1=>, 0=none)
v_constraint_rows, ...     # N-1 rows of N values (vertical: 1=<, -1=>, 0=none)
```

## Usage

**Solve a puzzle:**
```bash
python solver.py puzzle.txt
```

**Generate a puzzle:**
```bash
python test_generate_backtrack.py 5 --difficulty medium --seed 42 --output-dir ./puzzles
```

Difficulty is determined by solver backtrack count:

| Level | Backtracks |
|---|---|
| easy | 0 – 50 |
| medium | 50 – 500 |
| hard | 500+ |

## Key Functions

- `solve_puzzle(n, grid, h, v)` → `(status, solution, backtracks)` — use in code directly
- `count_backtracks(...)` — used internally by the generator to rate difficulty
- `generate(n, difficulty, seed, output_dir)` — generate and write a puzzle file
