"""
FOL Forward Chaining Solver for Futoshiki Puzzles

Implements forward chaining over a grounded CNF knowledge base to:
  1. Propagate facts via iterated unit propagation
  2. Detect contradictions (empty clause / complementary facts)
  3. Derive a complete assignment when possible

The solver works in three phases each iteration:
  - MATCH  : find clauses that have become unit clauses (one literal left)
  - FIRE   : assert those literals as new facts
  - UPDATE : simplify the KB and check for contradiction / completeness

When the KB alone cannot drive further progress (no new unit clauses),
the solver falls back to a *splitting rule* on the most-constrained atom,
which gives a complete DPLL-style procedure while still being fact-driven.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Generator, List, Optional, Set, Tuple

from .base_solver import BaseSolver, SolverFactory
from ..utils.metrics import GLOBAL_METRICS_STORE
from ..utils.KB_generate.clause import Literal, pos, neg
from ..utils.KB_generate.propositions import Val
from ..utils.KB_generate.kb_generate import ground_kb
from ..utils.KB_generate.knowledge_base import KnowledgeBase
from ..problem.parser import futoshiki_to_puzzle_dict


# ─────────────────────────────────────────────────────────────────────────────
# Forward Chaining Engine
# ─────────────────────────────────────────────────────────────────────────────

class ForwardChainer:
    """
    FOL Forward Chaining over a grounded CNF knowledge base.

    _fc() is a plain recursive function. During solve_steps(), snapshots
    are collected as a side effect via self.snapshots. solve() runs _fc()
    with no snapshot overhead.
    """

    def __init__(self, metrics: Any, N: int) -> None:
        self.N         = N
        self.metrics   = metrics
        self.snapshots: List[Tuple[str, List[List[int]]]] = []

    # ── public entry point ────────────────────────────────────────────────

    def run(self, kb: KnowledgeBase, record: bool = False) -> Optional[List[List[int]]]:
        """
        Solve and return the grid, or None on failure.
        If record=True, populate self.snapshots for step replay.
        """
        if record:
            self.snapshots.clear()
        result = self._fc(kb, record=record)
        if result is None:
            return None
        return self._extract_grid(result)

    # ── core recursive function ───────────────────────────────────────────

    def _fc(self, kb: KnowledgeBase, record: bool = False) -> Optional[KnowledgeBase]:
        self.metrics.inc_nodes_expanded()

        # ── Phase 1: unit propagation ─────────────────────────────────────
        kb = self._propagate(kb)
        if kb is None:
            return None

        if record:
            self.snapshots.append(("propagate", self._kb_to_grid(kb)))

        if kb.is_solved():
            if record:
                self.snapshots.append(("solved", self._kb_to_grid(kb)))
            return kb

        # ── Phase 2: singleton domain injection ───────────────────────────
        domains  = self._compute_domains(kb)
        injected = False

        for (i, j), possible in domains.items():
            self.metrics.inc_constraint_checks()
            if len(possible) == 0:
                return None
            if len(possible) == 1:
                v   = next(iter(possible))
                lit = pos(Val(i, j, v))
                if not kb.is_true(lit):
                    kb.clauses.append(frozenset({lit}))
                    injected = True
                    self.metrics.inc_assignments()
                    if record:
                        self.snapshots.append((f"inject:{i},{j}={v}", self._kb_to_grid(kb)))

        if injected:
            return self._fc(kb, record=record)

        # ── Phase 3: splitting rule on MRV cell ───────────────────────────
        split = self._mrv_cell(domains)
        if split is None:
            final = self._propagate(kb)
            if final is not None and record:
                self.snapshots.append(("solved", self._kb_to_grid(final)))
            return final

        (i, j), possible = split
        self.metrics.inc_nodes_generated()

        for v in self._lcv_order(i, j, possible, domains):
            self.metrics.inc_nodes_generated()
            kb_branch = deepcopy(kb)
            kb_branch.clauses.append(frozenset({pos(Val(i, j, v))}))
            self.metrics.inc_assignments()

            if record:
                self.snapshots.append((f"split:{i},{j}={v}", self._kb_to_grid(kb_branch)))

            result = self._fc(kb_branch, record=record)
            if result is not None:
                return result

            self.metrics.inc_backtracks()
            if record:
                self.snapshots.append((f"backtrack:{i},{j}", self._kb_to_grid(kb)))

        return None

    # ── propagation ───────────────────────────────────────────────────────

    def _propagate(self, kb: KnowledgeBase) -> Optional[KnowledgeBase]:
        kb.simplify()
        if kb.has_empty_clause():
            return None
        for lit in kb.facts:
            if kb.is_false(lit):
                return None
        return kb

    # ── domain inference ──────────────────────────────────────────────────

    def _compute_domains(
        self, kb: KnowledgeBase
    ) -> Dict[Tuple[int, int], Set[int]]:
        cells   = range(1, self.N + 1)
        vals    = range(1, self.N + 1)
        domains: Dict[Tuple[int, int], Set[int]] = {}

        for i in cells:
            for j in cells:
                possible: Set[int] = set()
                fixed: Optional[int] = None
                for v in vals:
                    lit = pos(Val(i, j, v))
                    if kb.is_true(lit):
                        fixed = v
                        break
                    if not kb.is_false(lit):
                        possible.add(v)
                domains[(i, j)] = {fixed} if fixed is not None else possible

        return domains

    # ── variable / value ordering ─────────────────────────────────────────

    def _mrv_cell(
        self, domains: Dict[Tuple[int, int], Set[int]]
    ) -> Optional[Tuple[Tuple[int, int], Set[int]]]:
        best      : Optional[Tuple[Tuple[int, int], Set[int]]] = None
        best_size : int = self.N + 1
        for (i, j), possible in domains.items():
            size = len(possible)
            if 1 < size < best_size:
                best      = ((i, j), possible)
                best_size = size
        return best

    def _lcv_order(
        self,
        i: int,
        j: int,
        possible: Set[int],
        domains: Dict[Tuple[int, int], Set[int]],
    ) -> List[int]:
        cells = range(1, self.N + 1)

        def conflict_count(v: int) -> int:
            count = 0
            for jj in cells:
                if jj != j and v in domains.get((i, jj), set()):
                    count += 1
            for ii in cells:
                if ii != i and v in domains.get((ii, j), set()):
                    count += 1
            return count

        return sorted(possible, key=conflict_count)

    # ── helpers ───────────────────────────────────────────────────────────

    def _kb_to_grid(self, kb: KnowledgeBase) -> List[List[int]]:
        """Extract current partial grid (0 = unassigned) from KB facts."""
        grid = [[0] * self.N for _ in range(self.N)]
        for i in range(1, self.N + 1):
            for j in range(1, self.N + 1):
                for v in range(1, self.N + 1):
                    if kb.is_true(pos(Val(i, j, v))):
                        grid[i - 1][j - 1] = v
                        break
        return grid

    def _extract_grid(self, kb: KnowledgeBase) -> Optional[List[List[int]]]:
        cells = range(1, self.N + 1)
        vals  = range(1, self.N + 1)
        buf   = [[0] * (self.N + 1) for _ in range(self.N + 1)]
        for i in cells:
            for j in cells:
                for v in vals:
                    if kb.is_true(pos(Val(i, j, v))):
                        buf[i][j] = v
                        break
                if buf[i][j] == 0:
                    return None
        return [[buf[i][j] for j in cells] for i in cells]


# ─────────────────────────────────────────────────────────────────────────────
# BaseSolver integration
# ─────────────────────────────────────────────────────────────────────────────

@SolverFactory.register("forward_chaining")
class ForwardChainingSolver(BaseSolver):

    def __init__(self, problem: Any, *, name: Optional[str] = None) -> None:
        super().__init__(problem, name=name or "ForwardChaining")
        self.n        = problem.size
        self._puzzle  = futoshiki_to_puzzle_dict(problem)
        self._problem = problem

    def _denial_clause(self, solution: List[List[int]]) -> frozenset:
        cells = range(1, self.n + 1)
        return frozenset(
            neg(Val(i, j, solution[i - 1][j - 1]))
            for i in cells
            for j in cells
        )

    # ── step-by-step visualization ────────────────────────────────────────

    def solve_steps(self, puzzle_data: Any) -> Generator[Any, None, None]:
        """
        Run the solver with snapshot recording enabled, then replay
        snapshots as StepState objects for the visualizer.

        Snapshot event types
        --------------------
        propagate        — unit propagation pass completed
        inject:i,j=v     — singleton domain forced cell (i,j) to value v
        split:i,j=v      — branching: trying value v at cell (i,j)
        backtrack:i,j    — branch failed, reverting cell (i,j)
        solved           — complete solution reached (skipped in replay,
                           handled by the explicit final StepState)
        """
        from gui.service.visualization_service import StepState

        self.metrics.start()

        def current_metrics() -> Dict[str, Any]:
            return {
                "nodes_generated"  : self.metrics.nodes_generated,
                "nodes_expanded"   : self.metrics.nodes_expanded,
                "constraint_checks": self.metrics.constraint_checks,
                "assignments"      : self.metrics.assignments,
                "backtracks"       : self.metrics.backtracks,
            }

        try:
            base_clauses = ground_kb(self.n, self._puzzle)
            chainer      = ForwardChainer(self.metrics, self.n)
            kb           = KnowledgeBase(list(base_clauses), self.n)

            # Run with recording — snapshots collected as side effect
            solution = chainer.run(kb, record=True)

            step_num = 1
            for event, grid in chainer.snapshots:
                etype, _, detail = event.partition(":")

                # Skip internal solved marker — final StepState handles it
                if etype == "solved":
                    continue

                active_cell    = None
                changed_cell   = None
                conflict_cells = []

                if detail:
                    cell_part = detail.split("=")[0]
                    parts     = cell_part.split(",")
                    if len(parts) == 2:
                        try:
                            active_cell = (int(parts[0]) - 1, int(parts[1]) - 1)
                        except ValueError:
                            pass

                    v_str = detail.split("=")[1] if "=" in detail else None

                    if etype == "inject" and active_cell:
                        changed_cell = active_cell
                        message = (
                            f"Singleton domain: cell "
                            f"({active_cell[0]+1},{active_cell[1]+1}) = {v_str} "
                            f"— only candidate remaining"
                        )
                    elif etype == "split" and active_cell:
                        changed_cell = active_cell
                        message = (
                            f"Splitting: try value {v_str} "
                            f"at ({active_cell[0]+1},{active_cell[1]+1})"
                        )
                    elif etype == "backtrack" and active_cell:
                        conflict_cells = [active_cell]
                        message = (
                            f"Contradiction — backtrack "
                            f"from ({active_cell[0]+1},{active_cell[1]+1})"
                        )
                    else:
                        message = detail
                else:
                    message = "Unit propagation pass"

                yield StepState(
                    step_number    = step_num,
                    grid           = grid,
                    active_cell    = active_cell,
                    changed_cell   = changed_cell,
                    conflict_cells = conflict_cells,
                    message        = message,
                    metrics        = current_metrics(),
                    is_complete    = False,
                    is_solved      = False,
                )
                step_num += 1

            # Final step
            final_grid = solution if solution else [row[:] for row in puzzle_data.grid]
            yield StepState(
                step_number    = step_num,
                grid           = final_grid,
                message        = "✅ Puzzle solved!" if solution else "❌ No solution found",
                metrics        = current_metrics(),
                is_complete    = True,
                is_solved      = solution is not None,
            )

        finally:
            self.metrics.stop()
            GLOBAL_METRICS_STORE.add(self.metrics)

    # ── solve() — unchanged from original ────────────────────────────────

    def solve(self) -> Dict[str, Any]:
        self.metrics.start()
        try:
            base_clauses = ground_kb(self.n, self._puzzle)
            chainer      = ForwardChainer(self.metrics, self.n)
            solutions    : List[List[List[int]]] = []

            for attempt in range(2):
                clauses = list(base_clauses)
                if attempt == 1 and solutions:
                    clauses.append(self._denial_clause(solutions[0]))
                kb  = KnowledgeBase(clauses, self.n)
                sol = chainer.run(kb, record=False)
                if sol is None:
                    break
                solutions.append(sol)

            if len(solutions) == 0:
                status, solution = "none", None
                self.metrics.mark_solved(False)
            elif len(solutions) == 1:
                status, solution = "unique", solutions[0]
                self.metrics.mark_solved(True)
                self.metrics.set_solution_depth(self.n * self.n)
            else:
                status, solution = "multiple", solutions[0]
                self.metrics.mark_solved(True)

            return {
                "status"  : status,
                "solution": solution,
                "metrics" : self.metrics.to_dict(),
            }
        finally:
            self.metrics.stop()
            GLOBAL_METRICS_STORE.add(self.metrics)


__all__ = ["ForwardChainer", "ForwardChainingSolver"]