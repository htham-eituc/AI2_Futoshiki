"""
AC-3 (Arc Consistency Algorithm 3) for Futoshiki.

Backtracking solvers.
"""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from typing import Dict, List, Optional, Set, Tuple

Cell = Tuple[int, int]
Domain = Dict[Cell, Set[int]]                                                                     

def build_initial_domains(n: int, grid: List[List[int]]) -> Domain:
    """
    Build cell → set-of-values mapping from a partial grid.
    Assigned cells get a singleton domain; empty cells get {1..N}.
    """
    domains: Domain = {}
    for r in range(n):
        for c in range(n):
            v = grid[r][c]
            domains[(r, c)] = {v} if v != 0 else set(range(1, n + 1))
    return domains

def _inequality_arcs(
    n: int,
    h_constraints: List[List[int]],
    v_constraints: List[List[int]],
) -> List[Tuple[Cell, Cell, int]]:
    """
    Return inequality arcs as (cell_a, cell_b, direction):
        +1  → value(a) must be < value(b)
        -1  → value(a) must be > value(b)
    Both directions are emitted for each constraint.
    """
    ineq: List[Tuple[Cell, Cell, int]] = []
    for r in range(n):
        for c in range(n - 1):
            d = h_constraints[r][c]
            if d == 1:
                ineq.append(((r, c), (r, c + 1),  1))
                ineq.append(((r, c + 1), (r, c), -1))
            elif d == -1:
                ineq.append(((r, c), (r, c + 1), -1))
                ineq.append(((r, c + 1), (r, c),  1))

    for r in range(n - 1):
        for c in range(n):
            d = v_constraints[r][c]
            if d == 1:
                ineq.append(((r, c), (r + 1, c),  1))
                ineq.append(((r + 1, c), (r, c), -1))
            elif d == -1:
                ineq.append(((r, c), (r + 1, c), -1))
                ineq.append(((r + 1, c), (r, c),  1))
    return ineq                                                     

def _revise_neq(domains: Domain, xi: Cell, xj: Cell) -> bool:
    if len(domains[xj]) == 1:
        (fixed,) = domains[xj]
        if fixed in domains[xi]:
            domains[xi].discard(fixed)
            return True
    return False

def _revise_ineq(domains: Domain, xi: Cell, xj: Cell, direction: int) -> bool:
    if direction == 1:
        max_xj = max(domains[xj])
        to_remove = {v for v in domains[xi] if v >= max_xj}
    else:
        min_xj = min(domains[xj])
        to_remove = {v for v in domains[xi] if v <= min_xj}

    if to_remove:
        domains[xi] -= to_remove
        return True
    return False

def run_ac3(
    domains: Domain,
    n: int,
    h_constraints: List[List[int]],
    v_constraints: List[List[int]],
) -> Optional[Domain]:
    domains = deepcopy(domains)
    queue: deque = deque()

                                        
    for r in range(n):
        cols = [(r, c) for c in range(n)]
        for xi in cols:
            for xj in cols:
                if xi != xj:
                    queue.append(("neq", xi, xj))

                                           
    for c in range(n):
        rows = [(r, c) for r in range(n)]
        for xi in rows:
            for xj in rows:
                if xi != xj:
                    queue.append(("neq", xi, xj))

                     
    ineq_arcs = _inequality_arcs(n, h_constraints, v_constraints)
    for cell_a, cell_b, direction in ineq_arcs:
        queue.append(("ineq", cell_a, cell_b, direction))

    while queue:
        item = queue.popleft()

        if item[0] == "neq":
            _, xi, xj = item
            if _revise_neq(domains, xi, xj):
                if not domains[xi]:
                    return None
                r, c = xi
                for col in range(n):
                    xk = (r, col)
                    if xk != xi and xk != xj:
                        queue.append(("neq", xk, xi))
                for row in range(n):
                    xk = (row, c)
                    if xk != xi and xk != xj:
                        queue.append(("neq", xk, xi))

        else:          
            _, xi, xj, direction = item
            if _revise_ineq(domains, xi, xj, direction):
                if not domains[xi]:
                    return None
                for cell_a, cell_b, d in ineq_arcs:
                    if cell_b == xi and cell_a != xj:
                        queue.append(("ineq", cell_a, cell_b, d))

    return domains                                                                        

def compute_heuristic(domains: Domain) -> float:
    """h(s) = number of unassigned cells (domain size > 1)."""
    return sum(1 for vals in domains.values() if len(vals) > 1)


def select_mrv_cell(domains: Domain) -> Optional[Cell]:
    """MRV: pick unassigned cell with smallest domain. None if all assigned."""
    unassigned = {cell: vals for cell, vals in domains.items() if len(vals) > 1}
    if not unassigned:
        return None
    return min(unassigned, key=lambda cell: len(unassigned[cell]))


def lcv_order(
    cell: Cell,
    domains: Domain,
    n: int,
    h_constraints: List[List[int]],
    v_constraints: List[List[int]],
) -> List[int]:
    r, c = cell
    peers: List[Cell] = (
        [(r, col) for col in range(n) if col != c] +
        [(row, c) for row in range(n) if row != r]
    )

    def count_eliminated(v: int) -> int:
        return sum(1 for peer in peers if v in domains[peer])

    return sorted(domains[cell], key=count_eliminated)                                                         

def domains_to_grid(domains: Domain, n: int) -> List[List[int]]:
    grid = [[0] * n for _ in range(n)]
    for (r, c), vals in domains.items():
        if len(vals) == 1:
            (grid[r][c],) = vals
    return grid