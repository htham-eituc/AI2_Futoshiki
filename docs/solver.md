# Solver Guide

This document explains how to use the shared solver foundation, how to update metrics, and how to add new algorithms.

## 1) Base architecture

Core classes are defined in [src/core/solvers/base_solver.py](src/core/solvers/base_solver.py):
- `BaseSolver`: abstract class for every algorithm
- `SolverFactory`: registry + factory for creating solvers by string name

Metrics classes are defined in [src/core/utils/metrics.py](src/core/utils/metrics.py):
- `SolverMetrics`: metrics for one run
- `MetricsStore`: store multiple runs
- `GLOBAL_METRICS_STORE`: global shared store

## 2) How to use `BaseSolver`

Every solver must:
1. Inherit `BaseSolver`
2. Implement `solve()`
3. Update `self.metrics` inside `solve()`
4. Push metrics to `GLOBAL_METRICS_STORE` when run ends

Example skeleton:

```python
from ..solvers.base_solver import BaseSolver, SolverFactory
from ..utils.metrics import GLOBAL_METRICS_STORE

@SolverFactory.register("my_solver")
class MySolver(BaseSolver):
    def solve(self):
        self.metrics.start()
        try:
            # solve logic
            self.metrics.mark_solved(True)
            return {"solution": None}
        except Exception as exc:
            self.metrics.mark_error(str(exc))
            raise
        finally:
            self.metrics.stop()
            GLOBAL_METRICS_STORE.add(self.metrics)
```

## 3) How to create a solver from factory

Use `SolverFactory.create()`:

```python
solver = SolverFactory.create("my_solver", problem)
result = solver.solve()
```

List registered algorithms:

```python
all_solvers = SolverFactory.registered_solvers()
```

## 4) How to update metrics during search

In `solve()` and expansion loops, call metrics methods when events happen.

Common methods:
- `self.metrics.start()` and `self.metrics.stop()`
- `self.metrics.mark_solved(True/False)`
- `self.metrics.mark_timeout(True)`
- `self.metrics.mark_error(message)`
- `self.metrics.inc_nodes_generated(n)`
- `self.metrics.inc_nodes_expanded(n)`
- `self.metrics.set_frontier_size(size)`
- `self.metrics.inc_assignments(n)`
- `self.metrics.inc_backtracks(n)`
- `self.metrics.inc_constraint_checks(n)`
- `self.metrics.set_solution_depth(depth)`
- `self.metrics.add_extra(key, value)`

Typical pattern:

```python
self.metrics.start()
try:
    while frontier:
        self.metrics.set_frontier_size(len(frontier))
        node = frontier.pop()
        self.metrics.inc_nodes_expanded()

        for child in expand(node):
            self.metrics.inc_nodes_generated()
            frontier.append(child)

    self.metrics.mark_solved(found)
finally:
    self.metrics.stop()
    GLOBAL_METRICS_STORE.add(self.metrics)
```

## 5) Save all metrics to files

After multiple runs, export metrics:

```python
from ..utils.metrics import GLOBAL_METRICS_STORE

GLOBAL_METRICS_STORE.save_json("data/outputs/metrics.json")
GLOBAL_METRICS_STORE.save_jsonl("data/outputs/metrics.jsonl")
GLOBAL_METRICS_STORE.save_csv("data/outputs/metrics.csv")
```

## 6) Add a new algorithm (checklist)

1. Create file in [src/core/solvers](src/core/solvers)
2. Import `BaseSolver`, `SolverFactory`
3. Register class with `@SolverFactory.register("algorithm_name")`
4. Implement `solve()`
5. Instrument metrics (`start`, counters, `stop`)
6. Add `GLOBAL_METRICS_STORE.add(self.metrics)` in `finally`
7. Test creation with `SolverFactory.create("algorithm_name", problem)`

## 7) Update existing algorithm to this standard

When migrating old solver code:
1. Change class parent to `BaseSolver`
2. Move setup data to `__init__` through `super().__init__(problem, name="...")` if needed
3. Wrap `solve()` body with `try/finally`
4. Replace local counters with `self.metrics.*`
5. Persist final run to global store

## 8) Recommended minimum metrics per run

For fair comparison across algorithms, always fill at least:
- `algorithm`
- `elapsed_seconds`
- `solved`
- `nodes_generated`
- `nodes_expanded`
- `constraint_checks`
- `solution_depth` (if available)
- `error` (if failed)
