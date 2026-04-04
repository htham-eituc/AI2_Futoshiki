"""
SLD Resolution Backward Chaining Solver for Futoshiki Puzzles
=============================================================

Implements a Prolog-style SLD (Selective Linear Definite) resolution
interpreter that proves Val(i,j,V) goals for each cell by resolving
against a Horn-clause rule base.

Architecture
------------
The KB is a set of *ungrounded* definite clauses (Horn clauses with
variables) expressed as Python Rule objects.  The interpreter works
top-down:

    1.  Start with the conjunctive goal:
            [val(1,1,?V11), val(1,2,?V12), …, val(N,N,?VNN)]
    2.  For the leftmost goal atom, find every rule whose head unifies
        with it (SLD selection rule = leftmost).
    3.  Replace the goal with (body of chosen rule) + (remaining goals),
        after applying the most-general unifier (MGU).
    4.  Recurse depth-first; backtrack when the resolvent becomes empty
        (success) or has no applicable rule (failure).

Rule base (Prolog-style Horn clauses)
--------------------------------------
    % R1 – pre-filled cell
    val(R,C,V) :- given(R,C,V).

    % R2 – free cell: pick a domain value that satisfies all constraints
    val(R,C,V) :- domain(R,C,V),
                  row_ok(R,C,V),
                  col_ok(R,C,V),
                  h_ok(R,C,V),
                  v_ok(R,C,V).

Constraint predicates use Negation-As-Failure (NAF) over the
`assignments` dict — a clean (row,col)→value map that is extended
immutably every time a val(i,j,v) goal is proven. This guarantees that
row_ok / col_ok / h_ok / v_ok always see *every* previously committed
cell, not just those reachable by walking the unification substitution.

Key design decisions
--------------------
* Variables are strings prefixed with '?', e.g. '?R', '?V1_2'.
* Substitutions θ are plain dicts {var_name: ground_term}.
* `assignments: Dict[Tuple[int,int], int]` is passed alongside θ and
  updated only when a val/3 goal succeeds with fully-ground args. It is
  the single source of truth for constraint checking.
* Rule variables are freshened (renamed with a unique suffix) on each
  resolution step to prevent cross-branch variable clashes.
* The interpreter is a generator; the caller pulls solutions one at a
  time and stops after at most two (to detect uniqueness).
"""

from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional, Tuple

from .base_solver import BaseSolver, SolverFactory
from ..utils.metrics import GLOBAL_METRICS_STORE
from ..problem.parser import futoshiki_to_puzzle_dict


# ─────────────────────────────────────────────────────────────────────────────
# Type aliases
# ─────────────────────────────────────────────────────────────────────────────

Term        = Any                        # int | str (var "?x") | tuple (compound)
Substitution = Dict[str, Term]           # variable name → ground value / other var
Assignments  = Dict[Tuple[int,int], int] # (row, col) → committed value


# ─────────────────────────────────────────────────────────────────────────────
# Term utilities
# ─────────────────────────────────────────────────────────────────────────────

def is_var(t: Term) -> bool:
    """True iff t is a Prolog-style logic variable (string starting with '?')."""
    return isinstance(t, str) and t.startswith("?")


def walk(t: Term, theta: Substitution) -> Term:
    """
    Chase variable bindings to their ultimate value or unbound variable.
    Implements the 'walk' step of the union-find used in unification.
    """
    while is_var(t) and t in theta:
        t = theta[t]
    return t


def unify(t1: Term, t2: Term, theta: Substitution) -> Optional[Substitution]:
    """
    Robinson unification algorithm.

    Returns an extended substitution on success, or None on failure.
    Always works on a copy of theta — the caller's substitution is never
    mutated, preserving backtracking correctness.
    """
    theta = dict(theta)   # shallow copy — ground terms are ints, safe
    stack = [(t1, t2)]
    while stack:
        s, t = stack.pop()
        s = walk(s, theta)
        t = walk(t, theta)
        if s == t:
            continue          # already unified
        if is_var(s):
            theta[s] = t      # bind variable
        elif is_var(t):
            theta[t] = s      # bind variable (symmetric)
        elif (isinstance(s, tuple) and isinstance(t, tuple)
              and len(s) == len(t)):
            stack.extend(zip(s, t))  # decompose compound terms
        else:
            return None       # clash — unification fails
    return theta


def apply_subst(atom: tuple, theta: Substitution) -> tuple:
    """
    Apply substitution θ to every argument of a compound atom,
    walking variables to their bound values.
    """
    return tuple(walk(arg, theta) if is_var(arg) else arg for arg in atom)


# ─────────────────────────────────────────────────────────────────────────────
# Rule (Horn clause)
# ─────────────────────────────────────────────────────────────────────────────

class Rule:
    """
    A definite (Horn) clause:  head :- body[0], body[1], …

    head  – a compound tuple, e.g. ("val", "?R", "?C", "?V")
    body  – list of compound tuples; empty list = unit clause (fact)

    Variables in each rule must be *freshened* before use in resolution
    to avoid unintended unification with variables from other proof steps.
    The class-level counter guarantees globally unique fresh names.
    """
    __slots__ = ("head", "body")
    _counter: int = 0   # monotonically increasing rename counter

    def __init__(self, head: tuple, body: List[tuple]) -> None:
        self.head = head
        self.body = body

    # ------------------------------------------------------------------
    def freshen(self) -> "Rule":
        """
        Return a copy of this rule with all logic variables replaced by
        fresh, unique names.  Called once per resolution step so that
        variables in one activation cannot accidentally unify with
        variables in another branch.
        """
        Rule._counter += 1
        suffix  = f"_{Rule._counter}"
        mapping: Dict[str, str] = {}

        def rename(t: Term) -> Term:
            if is_var(t):
                if t not in mapping:
                    mapping[t] = t + suffix
                return mapping[t]
            if isinstance(t, tuple):
                return tuple(rename(x) for x in t)
            return t

        return Rule(
            rename(self.head),
            [rename(b) for b in self.body],
        )

    def __repr__(self) -> str:
        if not self.body:
            return f"{self.head}."
        return f"{self.head} :- {', '.join(str(b) for b in self.body)}"


# ─────────────────────────────────────────────────────────────────────────────
# Rule base construction
# ─────────────────────────────────────────────────────────────────────────────

def _build_rule_base(
    N: int,
    puzzle: dict,
) -> Tuple[List[Rule], List[tuple]]:
    """
    Build the Prolog-style rule base and ground fact set for a Futoshiki
    puzzle of size N×N.

    Horn clauses (rules)
    --------------------
    val(?R,?C,?V) :- given(?R,?C,?V).
    val(?R,?C,?V) :- domain(?R,?C,?V),
                     row_ok(?R,?C,?V),
                     col_ok(?R,?C,?V),
                     h_ok(?R,?C,?V),
                     v_ok(?R,?C,?V).

    Built-in predicates (evaluated by the interpreter, not resolved):
        given/3, domain/3                   – fact lookup / enumeration
        row_ok/3, col_ok/3, h_ok/3, v_ok/3 – NAF constraint checks

    Ground facts
    ------------
    given(i,j,v)    – pre-filled cells from the puzzle
    less_h(i,j)     – cell(i,j) < cell(i,j+1)
    greater_h(i,j)  – cell(i,j) > cell(i,j+1)
    less_v(i,j)     – cell(i,j) < cell(i+1,j)
    greater_v(i,j)  – cell(i,j) > cell(i+1,j)
    domain(i,j,v)   – every (cell, value) combination in [1..N]
    """
    facts: List[tuple] = []

    # Pre-filled cells
    for (i, j), v in puzzle["given"].items():
        facts.append(("given", i, j, v))

    # Horizontal inequality constraints
    for (i, j) in puzzle.get("less_h", []):
        facts.append(("less_h", i, j))
    for (i, j) in puzzle.get("greater_h", []):
        facts.append(("greater_h", i, j))

    # Vertical inequality constraints
    for (i, j) in puzzle.get("less_v", []):
        facts.append(("less_v", i, j))
    for (i, j) in puzzle.get("greater_v", []):
        facts.append(("greater_v", i, j))

    # Domain facts: every (cell, value) pair
    for i in range(1, N + 1):
        for j in range(1, N + 1):
            for v in range(1, N + 1):
                facts.append(("domain", i, j, v))

    # ── Horn clause rules ─────────────────────────────────────────────────
    R, C, V = "?R", "?C", "?V"

    rules: List[Rule] = [
        # R1 – given cell
        Rule(
            ("val", R, C, V),
            [("given", R, C, V)],
        ),
        # R2 – free cell: enumerate domain, check all constraints
        Rule(
            ("val", R, C, V),
            [
                ("domain",  R, C, V),
                ("row_ok",  R, C, V),
                ("col_ok",  R, C, V),
                ("h_ok",    R, C, V),
                ("v_ok",    R, C, V),
            ],
        ),
    ]

    return rules, facts


# ─────────────────────────────────────────────────────────────────────────────
# SLD Resolution Interpreter
# ─────────────────────────────────────────────────────────────────────────────

class SLDInterpreter:
    """
    Prolog-style SLD resolution engine for Futoshiki.

    Selection rule  : leftmost atom in the resolvent (standard Prolog).
    Search strategy : depth-first with chronological backtracking.
    NAF             : negation-as-failure for built-in constraint checks.

    Core invariant
    --------------
    Every call to _solve() carries both:
      • theta       – the unification substitution (var → term bindings)
      • assignments – a clean (row,col)→value dict of *committed* cells

    `assignments` is the single source of truth used by all constraint
    predicates.  It is extended exactly once per cell: when a val(i,j,v)
    goal succeeds with fully-ground arguments.  Importantly it is passed
    immutably (via dict spread) so backtracking automatically reverts it.

    This fixes the fundamental bug in naive implementations that rely on
    walk(f"?V{i}_{j}", theta) to find previous assignments: after variable
    freshening, canonical names like ?V1_2 may point through chains of
    renamed intermediaries, making cross-cell lookups unreliable.
    """

    # Predicates handled by _eval_builtin, not by resolution
    _BUILTINS = frozenset({
        "given", "domain",
        "less_h", "greater_h", "less_v", "greater_v",
        "row_ok", "col_ok", "h_ok", "v_ok",
    })

    def __init__(
        self,
        rules:   List[Rule],
        facts:   List[tuple],
        N:       int,
        metrics: Any,
    ) -> None:
        self.N       = N
        self.metrics = metrics

        # Index rules by head functor for O(1) candidate lookup
        self._rules: Dict[str, List[Rule]] = {}
        for rule in rules:
            self._rules.setdefault(rule.head[0], []).append(rule)

        # Index all ground facts as a set for O(1) membership tests
        self._facts: frozenset = frozenset(facts)

        # Secondary index: given/3 facts keyed by (row,col)
        self._given: Dict[Tuple[int,int], int] = {
            (f[1], f[2]): f[3]
            for f in facts if f[0] == "given"
        }

    # ─────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────

    def query_all_cells(
        self,
        initial_assignments: Optional[Assignments] = None,
    ) -> Optional[List[List[int]]]:
        """
        Issue the conjunctive goal:
            val(1,1,?V1_1), val(1,2,?V1_2), …, val(N,N,?VN_N)

        Returns the completed grid on the first successful proof, or None
        if no solution exists.

        Parameters
        ----------
        initial_assignments : pre-loaded (row,col)→value entries that seed
            the assignments dict before proof search begins.  The caller
            passes all given (pre-filled) cells here so that row_ok /
            col_ok / h_ok / v_ok can see them from the very first free-cell
            goal, regardless of reading order.

            Without this seeding, rule R1
                val(R,C,V) :- given(R,C,V).
            has no row_ok / col_ok in its body, so a given cell is only
            committed to assignments when its own val/3 goal is resolved.
            Any free cell earlier in the goal list can therefore be assigned
            the same value as a later given cell with no conflict detected —
            producing invalid duplicate-filled grids.
        """
        goals = [
            ("val", i, j, f"?V{i}_{j}")
            for i in range(1, self.N + 1)
            for j in range(1, self.N + 1)
        ]
        seed = dict(initial_assignments) if initial_assignments else {}

        for _, assignments in self._solve(goals, {}, seed):
            # Reconstruct grid from the assignments dict
            grid: List[List[int]] = []
            ok = True
            for i in range(1, self.N + 1):
                row: List[int] = []
                for j in range(1, self.N + 1):
                    v = assignments.get((i, j))
                    if v is None:
                        ok = False
                        break
                    row.append(v)
                if not ok:
                    break
                grid.append(row)
            if ok:
                return grid

        return None

    # ─────────────────────────────────────────────────────────────────────
    # Core SLD proof engine
    # ─────────────────────────────────────────────────────────────────────

    def _solve(
        self,
        goals:       List[tuple],
        theta:       Substitution,
        assignments: Assignments,
    ) -> Generator[Tuple[Substitution, Assignments], None, None]:
        """
        Depth-first SLD proof search over the goal list.

        Yields (theta, assignments) pairs for every successful proof.

        Parameters
        ----------
        goals       : remaining goals to prove (resolvent)
        theta       : current unification substitution
        assignments : (row,col)→value map of all committed cells;
                      the sole source of truth for constraint predicates.

        Resolution step
        ---------------
        For the leftmost goal G:

          1. Built-in predicate → _eval_builtin yields (θ', asgn') pairs;
             recurse on rest_goals with each.

          2. val(R,C,V) goal → special two-phase proof:
               a. Unify G with rule head → θ'.
               b. Prove rule body under θ' → yields (θ'', asgn'').
               c. Walk R,C,V in θ'' to get ground values gi,gj,gv.
               d. Record (gi,gj)→gv in assignments, then prove rest_goals.
             Phase separation is essential: we can only record assignments
             after the body (domain+constraints) has pinned V to a specific
             integer.  Checking groundness before the body runs would always
             fail because V starts unbound.

          3. Any other functor → standard SLD resolution:
             new resolvent = rule.body + rest_goals, all under θ'.
        """
        self.metrics.inc_nodes_expanded()

        if not goals:
            yield theta, assignments
            return

        head_goal, *rest_goals = goals
        functor = head_goal[0]

        # ── Built-in predicates ───────────────────────────────────────────
        if functor in self._BUILTINS:
            for theta2, asgn2 in self._eval_builtin(head_goal, theta, assignments):
                yield from self._solve(rest_goals, theta2, asgn2)
            return

        # ── Resolution against rule base ──────────────────────────────────
        candidates = self._rules.get(functor, [])
        self.metrics.inc_nodes_generated(len(candidates))

        for rule in candidates:
            fresh  = rule.freshen()
            theta2 = unify(head_goal, fresh.head, theta)

            if theta2 is None:
                self.metrics.inc_constraint_checks()
                continue   # heads don't unify — try next rule

            self.metrics.inc_assignments()

            if functor == "val":
                # Two-phase: prove body first, then commit assignment, then rest.
                #
                # We must NOT check groundness of V before proving the body —
                # V is always a variable at this point (it gets bound by
                # domain/3 inside the body).  Instead, prove the body goals
                # as a sub-proof, then read the now-ground R,C,V out of the
                # resulting substitution θ'' before continuing with rest_goals.
                body_goals = [apply_subst(b, theta2) for b in fresh.body]
                cont_goals = [apply_subst(g, theta2) for g in rest_goals]

                for theta3, asgn3 in self._solve(body_goals, theta2, assignments):
                    # Body proven: R, C, V are now ground in theta3.
                    gi = walk(head_goal[1], theta3)
                    gj = walk(head_goal[2], theta3)
                    gv = walk(head_goal[3], theta3)

                    if is_var(gi) or is_var(gj) or is_var(gv):
                        # Should not happen for a well-formed puzzle, but
                        # skip silently rather than recording a bad entry.
                        continue

                    # Commit this cell's value, then prove remaining goals.
                    new_asgn = {**asgn3, (gi, gj): gv}
                    yield from self._solve(cont_goals, theta3, new_asgn)

            else:
                # Standard SLD resolution: flatten body + rest into one resolvent.
                new_goals = (
                    [apply_subst(b, theta2) for b in fresh.body]
                    + [apply_subst(g, theta2) for g in rest_goals]
                )
                yield from self._solve(new_goals, theta2, assignments)

        self.metrics.inc_backtracks()

    # ─────────────────────────────────────────────────────────────────────
    # Built-in predicate evaluator
    # ─────────────────────────────────────────────────────────────────────

    def _eval_builtin(
        self,
        atom:        tuple,
        theta:       Substitution,
        assignments: Assignments,
    ) -> Generator[Tuple[Substitution, Assignments], None, None]:
        """
        Evaluate a built-in predicate under the current substitution.

        Yields (theta', assignments') pairs, mirroring Prolog semantics:
          • Deterministic predicates yield exactly 0 (fail) or 1 (succeed).
          • domain/3 with an unbound V yields N times (enumeration).
          • given/3 with an unbound V yields 1 time (the stored value).

        All constraint predicates (row_ok, col_ok, h_ok, v_ok) read
        exclusively from `assignments` — never from theta — ensuring
        they see every committed cell regardless of variable renaming.
        """
        functor = atom[0]
        # Walk all arguments to their current values under theta
        args = tuple(walk(a, theta) if is_var(a) else a for a in atom[1:])
        self.metrics.inc_constraint_checks()

        # ── domain(R,C,V) ─────────────────────────────────────────────────
        # When V is unbound: enumerate 1..N, binding V to each in turn.
        # This is the Prolog "between(1,N,V)" analogue that drives search.
        # When V is ground: succeed iff it is in range.
        #
        # Critical: if (R,C) is already committed in assignments (because it
        # is a given cell pre-loaded into given_seed), lock domain to that
        # single value.  Without this, R2's body (domain → row_ok → …) would
        # enumerate ALL values for given cells, because row_ok skips the cell
        # itself (c2 != C) and therefore cannot detect that the cell's own
        # pre-committed value conflicts with the candidate.
        if functor == "domain":
            R, C, V = args
            if is_var(R) or is_var(C):
                return   # R and C must always be ground at call time
            committed = assignments.get((R, C))
            if committed is not None:
                # Cell already has a value (given) — only yield that value.
                if is_var(V):
                    yield {**theta, V: committed}, assignments
                elif V == committed:
                    yield theta, assignments
                # Any other ground V → fail (yield nothing)
                return
            # Free cell: enumerate all values in domain order
            if is_var(V):
                for v in range(1, self.N + 1):
                    yield {**theta, V: v}, assignments
            else:
                if 1 <= V <= self.N:
                    yield theta, assignments
            return

        # ── given(R,C,V) ──────────────────────────────────────────────────
        # Look up pre-filled value. If V is unbound, bind it; if ground,
        # check equality.  Do NOT write assignments here — the val/3
        # two-phase wrapper in _solve() handles the commit after the
        # body (which contains this call) succeeds.
        if functor == "given":
            R, C, V = args
            if is_var(R) or is_var(C):
                return
            stored = self._given.get((R, C))
            if stored is None:
                return   # no clue for this cell
            if is_var(V):
                yield {**theta, V: stored}, assignments
            elif V == stored:
                yield theta, assignments
            return

        # ── row_ok(R,C,V) ─────────────────────────────────────────────────
        # NAF: succeed iff no other cell in row R already holds value V.
        # Reads assignments dict — never theta.
        if functor == "row_ok":
            R, C, V = args
            if is_var(R) or is_var(C) or is_var(V):
                return   # must be fully ground
            for c2 in range(1, self.N + 1):
                if c2 != C and assignments.get((R, c2)) == V:
                    return   # row conflict → fail
            yield theta, assignments

        # ── col_ok(R,C,V) ─────────────────────────────────────────────────
        # NAF: succeed iff no other cell in col C already holds value V.
        elif functor == "col_ok":
            R, C, V = args
            if is_var(R) or is_var(C) or is_var(V):
                return
            for r2 in range(1, self.N + 1):
                if r2 != R and assignments.get((r2, C)) == V:
                    return   # column conflict → fail
            yield theta, assignments

        # ── h_ok(R,C,V) ───────────────────────────────────────────────────
        # Horizontal inequality constraints (left and right neighbours).
        # Only checks neighbours that are already committed.
        #
        # less_h(R,C)    means cell(R,C)   < cell(R,C+1)
        # greater_h(R,C) means cell(R,C)   > cell(R,C+1)
        #
        # Checking left neighbour (R, C-1):
        #   less_h(R,C-1)    → cell(R,C-1) < cell(R,C)   → left_v <  V
        #   greater_h(R,C-1) → cell(R,C-1) > cell(R,C)   → left_v >  V
        #
        # Checking right neighbour (R, C+1):
        #   less_h(R,C)      → cell(R,C)   < cell(R,C+1) → V      < right_v
        #   greater_h(R,C)   → cell(R,C)   > cell(R,C+1) → V      > right_v
        elif functor == "h_ok":
            R, C, V = args
            if is_var(R) or is_var(C) or is_var(V):
                return

            # Left neighbour
            if C > 1:
                left_v = assignments.get((R, C - 1))
                if left_v is not None:
                    if ("less_h",    R, C - 1) in self._facts and not (left_v < V):
                        return
                    if ("greater_h", R, C - 1) in self._facts and not (left_v > V):
                        return

            # Right neighbour
            if C < self.N:
                right_v = assignments.get((R, C + 1))
                if right_v is not None:
                    if ("less_h",    R, C) in self._facts and not (V < right_v):
                        return
                    if ("greater_h", R, C) in self._facts and not (V > right_v):
                        return

            yield theta, assignments

        # ── v_ok(R,C,V) ───────────────────────────────────────────────────
        # Vertical inequality constraints (above and below neighbours).
        #
        # less_v(R,C)    means cell(R,C)   < cell(R+1,C)
        # greater_v(R,C) means cell(R,C)   > cell(R+1,C)
        #
        # Checking top neighbour (R-1, C):
        #   less_v(R-1,C)    → cell(R-1,C) < cell(R,C)   → top_v  <  V
        #   greater_v(R-1,C) → cell(R-1,C) > cell(R,C)   → top_v  >  V
        #
        # Checking bottom neighbour (R+1, C):
        #   less_v(R,C)      → cell(R,C)   < cell(R+1,C) → V      < bot_v
        #   greater_v(R,C)   → cell(R,C)   > cell(R+1,C) → V      > bot_v
        elif functor == "v_ok":
            R, C, V = args
            if is_var(R) or is_var(C) or is_var(V):
                return

            # Top neighbour
            if R > 1:
                top_v = assignments.get((R - 1, C))
                if top_v is not None:
                    if ("less_v",    R - 1, C) in self._facts and not (top_v < V):
                        return
                    if ("greater_v", R - 1, C) in self._facts and not (top_v > V):
                        return

            # Bottom neighbour
            if R < self.N:
                bot_v = assignments.get((R + 1, C))
                if bot_v is not None:
                    if ("less_v",    R, C) in self._facts and not (V < bot_v):
                        return
                    if ("greater_v", R, C) in self._facts and not (V > bot_v):
                        return

            yield theta, assignments

        # Unknown built-in — fail silently (safe default)
        return


# ─────────────────────────────────────────────────────────────────────────────
# BaseSolver integration
# ─────────────────────────────────────────────────────────────────────────────

@SolverFactory.register("backward_chaining")
class BackwardChainingSolver(BaseSolver):
    """
    Prolog-style SLD resolution backward chaining solver for Futoshiki.

    Registered as "backward_chaining" in SolverFactory:

        solver = SolverFactory.create("backward_chaining", problem)
        result = solver.solve()

    solve() return value:
        {
            "status":   "unique" | "multiple" | "none",
            "solution": List[List[int]] | None,
            "metrics":  dict,
        }

    Uniqueness check
    ----------------
    The solver runs up to two proof searches.  On the second run, the
    domain facts for every (i,j,v) triple from the first solution are
    removed, forcing the interpreter to find a *different* assignment.
    If no second solution exists the puzzle is unique.
    """

    def __init__(self, problem: Any, *, name: Optional[str] = None) -> None:
        super().__init__(problem, name=name or "BackwardChaining")
        self.n       = problem.size
        self._puzzle = futoshiki_to_puzzle_dict(problem)

    def solve(self) -> Dict[str, Any]:
        self.metrics.start()
        solutions: List[List[List[int]]] = []

        try:
            rules, facts = _build_rule_base(self.n, self._puzzle)

            # Pre-load all given cells into the seed assignments dict.
            # Without this, R1 (val(R,C,V) :- given(R,C,V)) has no
            # constraint checks in its body, so a free cell proven before
            # a given cell cannot detect a duplicate with that given cell.
            given_seed: Assignments = {
                (r, c): v
                for (r, c), v in self._puzzle["given"].items()
            }

            for attempt in range(2):
                current_facts = facts

                if attempt == 1 and solutions:
                    # Remove domain facts for every (i,j,v) in solution 0.
                    # This forces the second search to find a different grid.
                    first     = solutions[0]
                    banned    = {
                        ("domain", i + 1, j + 1, v)
                        for i, row in enumerate(first)
                        for j, v  in enumerate(row)
                    }
                    current_facts = [f for f in facts if f not in banned]

                interp = SLDInterpreter(rules, current_facts, self.n, self.metrics)
                sol    = interp.query_all_cells(initial_assignments=given_seed)

                if sol is None:
                    break
                solutions.append(sol)

            # ── Determine status ──────────────────────────────────────────
            if not solutions:
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
                "status":   status,
                "solution": solution,
                "metrics":  self.metrics.to_dict(),
            }

        finally:
            self.metrics.stop()
            GLOBAL_METRICS_STORE.add(self.metrics)


__all__ = ["SLDInterpreter", "BackwardChainingSolver"]