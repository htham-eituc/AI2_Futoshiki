# 🧠 Futoshiki AI Solver

This project implements multiple AI approaches to solve the **Futoshiki puzzle**, including:
- Backtracking / Brute-force
- A* Search
- Forward Chaining
- Backward Chaining (SLD Resolution)
- First-Order Logic → CNF

It also includes a **Streamlit GUI** for visualization and comparison.

---

## 📁 Project Structure

```
futoshiki-ai/
│
├── data/
│ ├── inputs/ # Input puzzles (.txt)
│ └── outputs/ # Solver outputs
│
├── src/
│ ├── core/ # 🔥 All solving logic (NO GUI)
│ │
│ │ ├── problem/ # Problem + State representation
│ │ ├── solvers/ # All algorithms (A*, backtracking, FOL, ...)
│ │ ├── fol/ # First-Order Logic + CNF
│ │ ├── heuristics/# A* heuristics
│ │ └── utils/ # Helper utilities
│ │
│ ├── gui/ # 🎨 Streamlit GUI
│ │ ├── app.py # Entry point
│ │ ├── pages/ # Solver & comparison pages
│ │ ├── components/# UI components (grid, stats, controls)
│ │ └── services/ # Connect GUI ↔ core logic
│ │
│ ├── experiments/ # Benchmark & batch testing
│ └── main.py # CLI entry (optional)
│
├── docs/ # Report, references
├── requirements.txt
└── README.md
```

---

## 🧩 Design Principles

- **Separation of concerns**
  - `core/` → logic only
  - `gui/` → visualization only

- **Reusable architecture**
  - All solvers inherit from a common `BaseSolver`
  - Shared `Problem`, `State`, and `Metrics`

- **Extensible**
  - Easy to add new algorithms or heuristics

---

## 🚀 How to Run

### 1. Install dependencies

pip install -r requirements.txt


### 2. Run GUI

streamlit run src/gui/app.py


---

## 👥 Notes for Team

- Do **NOT mix GUI and solving logic**
- Always use the shared `Problem` and `Constraint` modules
- Track metrics (time, nodes, etc.) for every solver
- Follow the existing structure when adding new features

---
