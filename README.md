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
   pip install -r requirements.txt
   ```
2. Run GUI
   ```bash
   python src/main.py gui
   ```
3. Run benchmark experiments
   ```bash
   python src/main.py experiments run
   ```
4. Generate experiment charts
   ```bash
   python src/main.py experiments visualize --input experiment.csv --output charts
   ```
