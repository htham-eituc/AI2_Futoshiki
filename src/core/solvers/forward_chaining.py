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
from typing import Any, Dict, List, Optional, Set, Tuple

from .base_solver import BaseSolver, SolverFactory
from ..utils.metrics import GLOBAL_METRICS_STORE
from ..utils.KB_generate.clause import Literal, pos, neg
from ..utils.KB_generate.propositions import Val
from ..utils.KB_generate.kb_generate import ground_kb
from ..utils.KB_generate.knowledge_base import KnowledgeBase
from ..problem.parser import futoshiki_to_puzzle_dict


# ─────────────────────────────────────────────────────────────────────────────
# Forward Chaining Engine  (pure reasoning logic, no solver interface)
# ─────────────────────────────────────────────────────────────────────────────

class ForwardChainer:
    """
    FOL Forward Chaining over a grounded CNF knowledge base.

    Algorithm
    ---------
    The grounded KB for Futoshiki is already in CNF, so "FOL forward
    chaining" reduces to iterated unit propagation (the standard FOL-FC
    completeness result for Horn-like fragments) extended with a splitting
    rule to handle non-Horn clauses.

    Each call to _fc() executes:

        1. SIMPLIFY  – run unit propagation inside the KB
        2. CHECK     – return UNSAT if empty clause or complementary facts found
        3. EXTRACT   – derive Val(i,j,v) facts from singleton domains
        4. INJECT    – push new facts as unit clauses; goto 1 if any new facts
        5. SPLIT     – pick the atom with the smallest remaining domain (MRV)
                       and recurse on each candidate value (LCV-ordered).
                       The first satisfying branch wins.

    Metrics are written directly to the SolverMetrics object supplied by
    the enclosing BaseSolver so they are compatible with BacktrackingSolver.
    """

    def __init__(self, metrics: Any, N: int) -> None:
        self.N       = N
        self.metrics = metrics   # SolverMetrics passed in from BaseSolver

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
        # If only one value remains possible for a cell, assert it as a fact.
        # This is the core "forward chaining" step: a new ground fact is
        # derived from the current KB state and immediately fed back in.
        domains  = self._compute_domains(kb)
        injected = False

        for (i, j), possible in domains.items():
            self.metrics.inc_constraint_checks()
            if len(possible) == 0:
                return None                      # domain wipe-out
            if len(possible) == 1:
                v   = next(iter(possible))
                lit = pos(Val(i, j, v))
                if not kb.is_true(lit):
                    kb.clauses.append(frozenset({lit}))
                    injected = True
                    self.metrics.inc_assignments()

        if injected:
            return self._fc(kb)                  # re-enter with new facts

        # ── Phase 3: stuck — splitting rule on MRV cell ───────────────────
        split = self._mrv_cell(domains)
        if split is None:
            # All cells have singleton domains — one final propagation pass
            # clears any remaining non-Val clauses that are now satisfied.
            return self._propagate(kb)

        (i, j), possible = split
        self.metrics.inc_nodes_generated()

        for v in self._lcv_order(i, j, possible, domains):
            self.metrics.inc_nodes_generated()
            kb_branch = deepcopy(kb)
            kb_branch.clauses.append(frozenset({pos(Val(i, j, v))}))
            self.metrics.inc_assignments()

            result = self._fc(kb_branch)
            if result is not None:
                return result

            self.metrics.inc_backtracks()

        return None   # all branches exhausted

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

        # Complementary-fact check: if L is a known fact but ¬L is also
        # a known fact, the branch is contradictory.
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

        v is impossible for (i,j)  ↔  ¬Val(i,j,v) is a known fact
        v is fixed   for (i,j)     ↔   Val(i,j,v)  is a known fact
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

    # ── variable / value ordering ─────────────────────────────────────────

    def _mrv_cell(
        self, domains: Dict[Tuple[int, int], Set[int]]
    ) -> Optional[Tuple[Tuple[int, int], Set[int]]]:
        """
        Minimum Remaining Values heuristic.
        Returns the unassigned cell with the fewest candidates (size > 1),
        or None if every cell is already decided (singleton domain).
        """
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
        """
        Least Constraining Value heuristic.
        Orders candidates so that the value eliminating the fewest options
        from row/column peers is tried first.
        """
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

    # ── solution extraction ───────────────────────────────────────────────

    def _extract_grid(self, kb: KnowledgeBase) -> Optional[List[List[int]]]:
        """
        Build a 0-indexed 2-D integer grid from Val facts in a solved KB.
        Returns None if any cell is still unassigned.
        """
        cells = range(1, self.N + 1)
        vals  = range(1, self.N + 1)
        buf   = [[0] * (self.N + 1) for _ in range(self.N + 1)]  # 1-indexed scratch

        for i in cells:
            for j in cells:
                for v in vals:
                    if kb.is_true(pos(Val(i, j, v))):
                        buf[i][j] = v
                        break
                if buf[i][j] == 0:
                    return None   # incomplete — shouldn't happen after _fc

        # Convert to 0-indexed to match BacktrackingSolver output
        return [[buf[i][j] for j in cells] for i in cells]


# ─────────────────────────────────────────────────────────────────────────────
# BaseSolver integration
# ─────────────────────────────────────────────────────────────────────────────

@SolverFactory.register("forward_chaining")
class ForwardChainingSolver(BaseSolver):
    """
    FOL Forward Chaining solver for Futoshiki puzzles.

    Registered as "forward_chaining" in SolverFactory, so it is created
    and used the same way as BacktrackingSolver:

        solver = SolverFactory.create("forward_chaining", problem)
        result = solver.solve()

    The problem object must expose the same interface as accepted by
    BacktrackingSolver (size, grid, h_constraints, v_constraints).

    solve() return value mirrors BacktrackingSolver exactly:
        {
            "status":   "unique" | "multiple" | "none",
            "solution": List[List[int]] | None,   # 0-indexed
            "metrics":  dict,
        }
    """

    def __init__(self, problem: Any, *, name: Optional[str] = None) -> None:
        super().__init__(problem, name=name or "ForwardChaining")

        self.n       = problem.size
        self._puzzle = futoshiki_to_puzzle_dict(problem)

    # ── helpers ───────────────────────────────────────────────────────────

    def _denial_clause(self, solution: List[List[int]]) -> frozenset:
        """
        Returns a clause that forbids `solution` from being found again.
        The clause asserts: at least one cell must differ from this solution.
            ∨_{i,j}  ¬Val(i, j, solution[i-1][j-1])
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
        Solve the Futoshiki puzzle using FOL Forward Chaining.

        Returns:
            Dict with keys:
                - status:   "unique" | "multiple" | "none"
                - solution: solved grid (0-indexed List[List[int]]) or None
                - metrics:  solver metrics dict
        """
        self.metrics.start()

        try:
            base_clauses = ground_kb(self.n, self._puzzle)
            chainer      = ForwardChainer(self.metrics, self.n)
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


__all__ = ["ForwardChainer", "ForwardChainingSolver"]