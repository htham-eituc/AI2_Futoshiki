"""
FOL Forward Chaining Solver for Futoshiki Puzzles (WITHOUT HEURISTICS)

Implements forward chaining over a grounded CNF knowledge base to:
  1. Propagate facts via iterated unit propagation
  2. Detect contradictions (empty clause / complementary facts)
  3. Derive a complete assignment when possible

When the KB alone cannot drive further progress (no new unit clauses),
the solver falls back to a *splitting rule* on the FIRST UNASSIGNED CELL
in row-major order, trying values in natural order (1 to N).

This version removes the MRV (Minimum Remaining Values) and LCV (Least
Constraining Value) heuristics to demonstrate their impact on search
efficiency.
"""

from __future__ import annotations
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set, Tuple

from .base_solver import BaseSolver, SolverFactory
from ..utils.metrics import GLOBAL_METRICS_STORE
from ..utils.KB_generate.clause import Literal, pos, neg
from ..utils.KB_generate.propositions import Val
from ..utils.KB_generate.kb_generate import ground_kb
from ..utils.KB_generate.knowledge_base import KnowledgeBase
from ..problem.parser import futoshiki_to_puzzle_dict


# ─────────────────────────────────────────────────────────────────────────────
# Forward Chaining Engine (NO HEURISTICS)
# ─────────────────────────────────────────────────────────────────────────────

class ForwardChainerNoHeuristics:
    """
    FOL Forward Chaining over a grounded CNF knowledge base WITHOUT heuristics.

    Algorithm
    ---------
    Same as ForwardChainer but uses naive search strategies:
      - Variable selection: First unassigned cell in row-major order
      - Value ordering: Natural order (1 to N)

    This trades optimality in search for simplicity, resulting in a baseline
    for comparing against heuristic-guided search performance.
    """

    def __init__(self, metrics: Any, N: int) -> None:
        self.N       = N
        self.metrics = metrics

    # ── public entry point ────────────────────────────────────────────────

    def run(self, kb: KnowledgeBase) -> Optional[List[List[int]]]:
        """
        Entry point.
        Returns the solved grid as a 0-indexed List[List[int]], or None (UNSAT).
        """
        result = self._fc(kb)
        if result is None:
            return None
        return self._extract_grid(result)

    # ── core recursive procedure ──────────────────────────────────────────

    def _fc(self, kb: KnowledgeBase) -> Optional[KnowledgeBase]:
        """
        Forward-chain on `kb` until solved, contradiction, or stuck.
        Returns a solved KB, or None on contradiction / exhaustion.
        """
        self.metrics.inc_nodes_expanded()

        # ── Phase 1: unit propagation to fixed point ──────────────────────
        kb = self._propagate(kb)
        if kb is None:
            return None

        if kb.is_solved():
            return kb

        # ── Phase 2: singleton-domain forward chaining ────────────────────
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

        if injected:
            return self._fc(kb)

        # ── Phase 3: split on FIRST unassigned cell (NO MRV) ──────────────
        split = self._first_unassigned_cell(domains)
        if split is None:
            return self._propagate(kb)

        (i, j), possible = split
        self.metrics.inc_nodes_generated()

        # Try values in natural order (NO LCV) ────────────────────────────
        for v in self._natural_value_order(possible):
            self.metrics.inc_nodes_generated()
            kb_branch = deepcopy(kb)
            kb_branch.clauses.append(frozenset({pos(Val(i, j, v))}))
            self.metrics.inc_assignments()

            result = self._fc(kb_branch)
            if result is not None:
                return result

            self.metrics.inc_backtracks()

        return None

    # ── propagation ───────────────────────────────────────────────────────

    def _propagate(self, kb: KnowledgeBase) -> Optional[KnowledgeBase]:
        """
        Run kb.simplify() (unit propagation) to a fixed point, then check
        for two kinds of contradiction:
          1. Empty clause        — standard DPLL / unit-propagation signal
          2. Complementary facts — both L and ¬L asserted in kb.facts
        Returns the simplified kb on success, None on contradiction.
        """
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
        """
        For every cell (i,j), compute the set of values still possible
        under the current KB facts.
        """
        cells   = range(1, self.N + 1)
        vals    = range(1, self.N + 1)
        domains : Dict[Tuple[int, int], Set[int]] = {}

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

    # ── naive variable / value ordering (NO HEURISTICS) ──────────────────

    def _first_unassigned_cell(
        self, domains: Dict[Tuple[int, int], Set[int]]
    ) -> Optional[Tuple[Tuple[int, int], Set[int]]]:
        """
        Return the first unassigned cell in row-major order (size > 1).
        No intelligent variable selection — purely sequential.
        """
        for i in range(1, self.N + 1):
            for j in range(1, self.N + 1):
                possible = domains.get((i, j), set())
                if len(possible) > 1:
                    return ((i, j), possible)
        return None

    def _natural_value_order(self, possible: Set[int]) -> List[int]:
        """
        Return values in natural ascending order (1 to N).
        No intelligent value selection — purely sequential.
        """
        return sorted(possible)

    # ── solution extraction ───────────────────────────────────────────────

    def _extract_grid(self, kb: KnowledgeBase) -> Optional[List[List[int]]]:
        """
        Build a 0-indexed 2-D integer grid from Val facts in a solved KB.
        Returns None if any cell is still unassigned.
        """
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

@SolverFactory.register("forward_chaining_no_heuristics")
class ForwardChainingSolverNoHeuristics(BaseSolver):
    """
    FOL Forward Chaining solver WITHOUT heuristics.

    Registered as "forward_chaining_no_heuristics" in SolverFactory:

        solver = SolverFactory.create("forward_chaining_no_heuristics", problem)
        result = solver.solve()

    Identical return format to ForwardChainingSolver.
    """

    def __init__(self, problem: Any, *, name: Optional[str] = None) -> None:
        super().__init__(problem, name=name or "FCNoHeuristics")

        self.n       = problem.size
        self._puzzle = futoshiki_to_puzzle_dict(problem)

    # ── helpers ───────────────────────────────────────────────────────────

    def _denial_clause(self, solution: List[List[int]]) -> frozenset:
        """
        Returns a clause that forbids `solution` from being found again.
        """
        cells = range(1, self.n + 1)
        return frozenset(
            neg(Val(i, j, solution[i - 1][j - 1]))
            for i in cells
            for j in cells
        )

    # ── BaseSolver.solve() ────────────────────────────────────────────────

    def solve(self) -> Dict[str, Any]:
        """
        Solve the Futoshiki puzzle using FOL Forward Chaining WITHOUT heuristics.

        Returns:
            Dict with keys:
                - status:   "unique" | "multiple" | "none"
                - solution: solved grid (0-indexed List[List[int]]) or None
                - metrics:  solver metrics dict
        """
        self.metrics.start()

        try:
            base_clauses = ground_kb(self.n, self._puzzle)
            chainer      = ForwardChainerNoHeuristics(self.metrics, self.n)
            solutions    : List[List[List[int]]] = []

            # ── find up to 2 solutions (uniqueness check) ─────────────────
            for attempt in range(2):
                clauses = list(base_clauses)
                if attempt == 1 and solutions:
                    clauses.append(self._denial_clause(solutions[0]))

                kb  = KnowledgeBase(clauses, self.n)
                sol = chainer.run(kb)

                if sol is None:
                    break
                solutions.append(sol)

            # ── determine status ──────────────────────────────────────────
            if len(solutions) == 0:
                status   = "none"
                solution = None
                self.metrics.mark_solved(False)

            elif len(solutions) == 1:
                status   = "unique"
                solution = solutions[0]
                self.metrics.mark_solved(True)
                self.metrics.set_solution_depth(self.n * self.n)

            else:
                status   = "multiple"
                solution = solutions[0]
                self.metrics.mark_solved(True)

            return {
                "status"  : status,
                "solution": solution,
                "metrics" : self.metrics.to_dict(),
            }

        finally:
            self.metrics.stop()
            GLOBAL_METRICS_STORE.add(self.metrics)


__all__ = ["ForwardChainerNoHeuristics", "ForwardChainingSolverNoHeuristics"]