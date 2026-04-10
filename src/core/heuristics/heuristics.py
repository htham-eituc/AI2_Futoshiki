"""
Heuristic helpers for Futoshiki solvers.

h2(s) = sum over all unassigned cells of (|domain(cell)| - 1)
      = 0  iff every cell is assigned (goal state)
      = ∞  iff any domain is empty   (infeasible)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

Cell   = Tuple[int, int]
Domain = Dict[Cell, Set[int]]


# ---------------------------------------------------------------------------
# Domain initialisation
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# h2 heuristic
# ---------------------------------------------------------------------------

def compute_heuristic(domains: Domain) -> float:
    """
    h2 = Σ (|domain(cell)| - 1)
       = 0   iff every cell is assigned (goal)
       = inf iff any domain is empty    (infeasible — prune immediately)
    """
    total = 0
    for vals in domains.values():
        n = len(vals)
        if n == 0:
            return float("inf")   # domain rỗng → nhánh không khả thi
        total += n - 1
    return total


# ---------------------------------------------------------------------------
# Variable / value ordering
# ---------------------------------------------------------------------------

def select_mrv_cell(domains: Domain) -> Optional[Cell]:
    """MRV: pick unassigned cell with smallest domain (> 1). None if all assigned."""
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
    """LCV: order values by fewest eliminations from row/column peers."""
    r, c = cell
    peers: List[Cell] = (
        [(r, col) for col in range(n) if col != c] +
        [(row, c)  for row in range(n) if row != r]
    )

    def count_eliminated(v: int) -> int:
        return sum(1 for peer in peers if v in domains[peer])

    return sorted(domains[cell], key=count_eliminated)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def domains_to_grid(domains: Domain, n: int) -> List[List[int]]:
    """Convert domains to N×N grid. Unassigned cells (|domain| > 1) → 0."""
    grid = [[0] * n for _ in range(n)]
    for (r, c), vals in domains.items():
        if len(vals) == 1:
            (grid[r][c],) = vals
    return grid


def shallow_copy_domains(domains: Domain) -> Domain:
    """
    Shallow copy: tạo dict mới nhưng copy từng set riêng.
    Nhanh hơn deepcopy ~5–10× vì không đệ quy vào các object lồng nhau.
    Dùng thay deepcopy(domains) trong A* khi chỉ cần tách state.
    """
    return {cell: set(vals) for cell, vals in domains.items()}


__all__ = [
    "Cell", "Domain",
    "build_initial_domains",
    "compute_heuristic",
    "select_mrv_cell",
    "lcv_order",
    "domains_to_grid",
    "shallow_copy_domains",
]