from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional, Tuple

from .base_solver import BaseSolver, SolverFactory
from ..utils.metrics import GLOBAL_METRICS_STORE
from ..problem.parser import futoshiki_to_puzzle_dict

Term         = Any
Substitution = Dict[str, Term]
Assignments  = Dict[Tuple[int, int], int]

def is_var(t: Term) -> bool:
    return isinstance(t, str) and t.startswith("?")


def walk(t: Term, theta: Substitution) -> Term:
    while is_var(t) and t in theta:
        t = theta[t]
    return t


def unify(t1: Term, t2: Term, theta: Substitution) -> Optional[Substitution]:
    theta = dict(theta)
    stack = [(t1, t2)]
    while stack:
        s, t = stack.pop()
        s = walk(s, theta)
        t = walk(t, theta)
        if s == t:
            continue
        if is_var(s):
            theta[s] = t
        elif is_var(t):
            theta[t] = s
        elif (isinstance(s, tuple) and isinstance(t, tuple)
              and len(s) == len(t)):
            stack.extend(zip(s, t))
        else:
            return None
    return theta


def apply_subst(atom: tuple, theta: Substitution) -> tuple:
    return tuple(walk(arg, theta) if is_var(arg) else arg for arg in atom)

class Rule:
    __slots__ = ("head", "body")
    _counter: int = 0

    def __init__(self, head: tuple, body: List[tuple]) -> None:
        self.head = head
        self.body = body

    def freshen(self) -> "Rule":
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

        return Rule(rename(self.head), [rename(b) for b in self.body])

    def __repr__(self) -> str:
        if not self.body:
            return f"{self.head}."
        return f"{self.head} :- {', '.join(str(b) for b in self.body)}"

def _build_rule_base(
    N: int,
    puzzle: dict,
) -> Tuple[List[Rule], List[tuple]]:
    facts: List[tuple] = []

    for (i, j), v in puzzle["given"].items():
        facts.append(("given", i, j, v))
    for (i, j) in puzzle.get("less_h", []):
        facts.append(("less_h", i, j))
    for (i, j) in puzzle.get("greater_h", []):
        facts.append(("greater_h", i, j))
    for (i, j) in puzzle.get("less_v", []):
        facts.append(("less_v", i, j))
    for (i, j) in puzzle.get("greater_v", []):
        facts.append(("greater_v", i, j))
    for i in range(1, N + 1):
        for j in range(1, N + 1):
            for v in range(1, N + 1):
                facts.append(("domain", i, j, v))

    R, C, V = "?R", "?C", "?V"
    rules: List[Rule] = [
        Rule(("val", R, C, V), [("given",  R, C, V)]),
        Rule(("val", R, C, V), [
            ("domain", R, C, V),
            ("row_ok", R, C, V),
            ("col_ok", R, C, V),
            ("h_ok",   R, C, V),
            ("v_ok",   R, C, V),
        ]),
    ]
    return rules, facts

class SLDInterpreter:
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
        snapshots: Optional[List[Tuple[str, int, int, int, bool]]] = None,
    ) -> None:
        self.N         = N
        self.metrics   = metrics
        self.snapshots = snapshots  # injected by solve_steps(), None in solve()

        self._rules: Dict[str, List[Rule]] = {}
        for rule in rules:
            self._rules.setdefault(rule.head[0], []).append(rule)

        self._facts: frozenset = frozenset(facts)
        self._given: Dict[Tuple[int, int], int] = {
            (f[1], f[2]): f[3]
            for f in facts if f[0] == "given"
        }

    def query_all_cells(
        self,
        initial_assignments: Optional[Assignments] = None,
    ) -> Optional[List[List[int]]]:
        goals = [
            ("val", i, j, f"?V{i}_{j}")
            for i in range(1, self.N + 1)
            for j in range(1, self.N + 1)
        ]
        seed = dict(initial_assignments) if initial_assignments else {}

        for _, assignments in self._solve(goals, {}, seed):
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

    def _solve(
        self,
        goals:       List[tuple],
        theta:       Substitution,
        assignments: Assignments,
    ) -> Generator[Tuple[Substitution, Assignments], None, None]:
        self.metrics.inc_nodes_expanded()

        if not goals:
            yield theta, assignments
            return

        head_goal, *rest_goals = goals
        functor = head_goal[0]

        if functor in self._BUILTINS:
            for theta2, asgn2 in self._eval_builtin(head_goal, theta, assignments):
                yield from self._solve(rest_goals, theta2, asgn2)
            return

        candidates = self._rules.get(functor, [])
        self.metrics.inc_nodes_generated(len(candidates))

        for rule in candidates:
            fresh  = rule.freshen()
            theta2 = unify(head_goal, fresh.head, theta)
            if theta2 is None:
                self.metrics.inc_constraint_checks()
                continue

            self.metrics.inc_assignments()

            if functor == "val":
                body_goals = [apply_subst(b, theta2) for b in fresh.body]
                cont_goals = [apply_subst(g, theta2) for g in rest_goals]

                for theta3, asgn3 in self._solve(body_goals, theta2, assignments):
                    gi = walk(head_goal[1], theta3)
                    gj = walk(head_goal[2], theta3)
                    gv = walk(head_goal[3], theta3)

                    if is_var(gi) or is_var(gj) or is_var(gv):
                        continue

                    new_asgn = {**asgn3, (gi, gj): gv}

                    # Record snapshot if visualizing
                    if self.snapshots is not None:
                        is_given = (gi, gj) in self._given
                        self.snapshots.append((gi, gj, gv, is_given))

                    yield from self._solve(cont_goals, theta3, new_asgn)
            else:
                new_goals = (
                    [apply_subst(b, theta2) for b in fresh.body]
                    + [apply_subst(g, theta2) for g in rest_goals]
                )
                yield from self._solve(new_goals, theta2, assignments)

        self.metrics.inc_backtracks()

    def _eval_builtin(
        self,
        atom:        tuple,
        theta:       Substitution,
        assignments: Assignments,
    ) -> Generator[Tuple[Substitution, Assignments], None, None]:
        functor = atom[0]
        args    = tuple(walk(a, theta) if is_var(a) else a for a in atom[1:])
        self.metrics.inc_constraint_checks()

        if functor == "domain":
            R, C, V = args
            if is_var(R) or is_var(C):
                return
            committed = assignments.get((R, C))
            if committed is not None:
                if is_var(V):
                    yield {**theta, V: committed}, assignments
                elif V == committed:
                    yield theta, assignments
                return
            if is_var(V):
                for v in range(1, self.N + 1):
                    yield {**theta, V: v}, assignments
            else:
                if 1 <= V <= self.N:
                    yield theta, assignments
            return

        if functor == "given":
            R, C, V = args
            if is_var(R) or is_var(C):
                return
            stored = self._given.get((R, C))
            if stored is None:
                return
            if is_var(V):
                yield {**theta, V: stored}, assignments
            elif V == stored:
                yield theta, assignments
            return

        if functor == "row_ok":
            R, C, V = args
            if is_var(R) or is_var(C) or is_var(V):
                return
            for c2 in range(1, self.N + 1):
                if c2 != C and assignments.get((R, c2)) == V:
                    return
            yield theta, assignments

        elif functor == "col_ok":
            R, C, V = args
            if is_var(R) or is_var(C) or is_var(V):
                return
            for r2 in range(1, self.N + 1):
                if r2 != R and assignments.get((r2, C)) == V:
                    return
            yield theta, assignments

        elif functor == "h_ok":
            R, C, V = args
            if is_var(R) or is_var(C) or is_var(V):
                return
            if C > 1:
                left_v = assignments.get((R, C - 1))
                if left_v is not None:
                    if ("less_h",    R, C - 1) in self._facts and not (left_v < V):
                        return
                    if ("greater_h", R, C - 1) in self._facts and not (left_v > V):
                        return
            if C < self.N:
                right_v = assignments.get((R, C + 1))
                if right_v is not None:
                    if ("less_h",    R, C) in self._facts and not (V < right_v):
                        return
                    if ("greater_h", R, C) in self._facts and not (V > right_v):
                        return
            yield theta, assignments

        elif functor == "v_ok":
            R, C, V = args
            if is_var(R) or is_var(C) or is_var(V):
                return
            if R > 1:
                top_v = assignments.get((R - 1, C))
                if top_v is not None:
                    if ("less_v",    R - 1, C) in self._facts and not (top_v < V):
                        return
                    if ("greater_v", R - 1, C) in self._facts and not (top_v > V):
                        return
            if R < self.N:
                bot_v = assignments.get((R + 1, C))
                if bot_v is not None:
                    if ("less_v",    R, C) in self._facts and not (V < bot_v):
                        return
                    if ("greater_v", R, C) in self._facts and not (V > bot_v):
                        return
            yield theta, assignments

        return


@SolverFactory.register("backward_chaining")
class BackwardChainingSolver(BaseSolver):

    def __init__(self, problem: Any, *, name: Optional[str] = None) -> None:
        super().__init__(problem, name=name or "BackwardChaining")
        self.n       = problem.size
        self._puzzle = futoshiki_to_puzzle_dict(problem)

    # ── step-by-step visualization ────────────────────────────────────────

    def solve_steps(self, puzzle_data: Any) -> Generator[Any, None, None]:
        """
        Run the solver with snapshot recording enabled, then replay
        snapshots as StepState objects for the visualizer.

        Snapshots are (row, col, value, is_given) tuples recorded each
        time a val(i,j,v) goal is proven — i.e. each cell commitment in
        SLD goal order (row by row, left to right).

        is_given=True  → proven via R1 (given cell, unit clause fired)
        is_given=False → proven via R2 (domain enumeration + constraints)
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
            rules, facts = _build_rule_base(self.n, self._puzzle)
            given_seed: Assignments = {
                (r, c): v
                for (r, c), v in self._puzzle["given"].items()
            }

            # Snapshot list injected into interpreter
            snapshots: List[Tuple[int, int, int, bool]] = []

            interp  = SLDInterpreter(rules, facts, self.n, self.metrics,
                                     snapshots=snapshots)
            solution = interp.query_all_cells(initial_assignments=given_seed)

            # Replay snapshots
            display_grid = [row[:] for row in puzzle_data.grid]
            step_num     = 1

            for (gi, gj, gv, is_given) in snapshots:
                r, c = gi - 1, gj - 1   # convert to 0-indexed
                display_grid[r][c] = gv

                if is_given:
                    message = (
                        f"Goal val({gi},{gj},{gv}) proven via R1 — given cell"
                    )
                else:
                    message = (
                        f"Goal val({gi},{gj},{gv}) proven via R2 — "
                        f"domain enumeration + constraint checks"
                    )

                yield StepState(
                    step_number    = step_num,
                    grid           = [row[:] for row in display_grid],
                    active_cell    = (r, c),
                    changed_cell   = (r, c) if not is_given else None,
                    conflict_cells = [],
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
                message        = "Puzzle solved" if solution else "No solution found",
                metrics        = current_metrics(),
                is_complete    = True,
                is_solved      = solution is not None,
            )

        finally:
            self.metrics.stop()
            GLOBAL_METRICS_STORE.add(self.metrics)

    def solve(self) -> Dict[str, Any]:
        self.metrics.start()
        status   = "none"
        solution = None

        try:
            rules, facts = _build_rule_base(self.n, self._puzzle)
            given_seed: Assignments = {
                (r, c): v
                for (r, c), v in self._puzzle["given"].items()
            }

            solutions: List[List[List[int]]] = []

            for attempt in range(2):
                current_facts = facts
                if attempt == 1 and solutions:
                    first  = solutions[0]
                    banned = {
                        ("domain", i + 1, j + 1, v)
                        for i, row in enumerate(first)
                        for j, v   in enumerate(row)
                    }
                    current_facts = [f for f in facts if f not in banned]

                interp = SLDInterpreter(rules, current_facts, self.n,
                                        self.metrics, snapshots=None)
                sol    = interp.query_all_cells(initial_assignments=given_seed)
                if sol is None:
                    break
                solutions.append(sol)

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

        finally:
            # stop() ALWAYS runs before to_dict() so elapsed_seconds is correct
            self.metrics.stop()
            GLOBAL_METRICS_STORE.add(self.metrics)

        return {
            "status"  : status,
            "solution": solution,
            "metrics" : self.metrics.to_dict(),
        }

__all__ = ["SLDInterpreter", "BackwardChainingSolver"]
