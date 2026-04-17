# Futoshiki AI Solver

This project solves Futoshiki puzzles with multiple AI strategies and includes a Streamlit interface for step-by-step visualization and algorithm comparison.

## Project structure

```text
AI2_Futoshiki/
├── src/
│   ├── core/                    # Puzzle model, heuristics, solvers, metrics
│   ├── gui/
│   │   ├── app.py               # Canonical GUI entrypoint
│   │   ├── components/
│   │   └── services/
│   ├── experiments/             # Experiment runner + visualization modules
│   ├── test_generate/           # Puzzle fixtures and test helpers
│   └── main.py                  # Canonical CLI entrypoint
├── docs/
├── charts/
└── requirements.txt
```

## Canonical entrypoints

1. Install dependencies
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Run GUI
   ```bash
   python src/main.py gui
   ```
3. Run benchmark experiments
   ```bash
   python src/main.py experiments run --timeout 60
   ```
4. Generate experiment charts
   ```bash
   python src/main.py experiments visualize --input experiment.csv --output charts
   ```

## Migration map

| Old path | New path |
| --- | --- |
| `src/gui/service/` | `src/gui/services/` |
| `src/core/experiments/run_experiments.py` | `src/experiments/run_experiments.py` |
| `visualize_experiments.py` (implementation) | `src/experiments/visualize_experiments.py` |
| Root wrapper scripts (`run_experiments.py`, `visualize_experiments.py`) | Removed (use `python src/main.py ...`) |

## Contribution rules

1. Keep solver logic inside `src/core` and UI logic inside `src/gui`.
2. Place experiment/benchmark scripts in `src/experiments`.
3. Use `src/main.py` as the canonical entrypoint in docs and automation.
4. Update imports and tests in the same change whenever modules move.

## Source comment governance

1. Remove non-essential inline comments from source files.
2. Keep only required directives or legally required headers.
3. Keep meaningful docstrings for public behavior and interfaces.
