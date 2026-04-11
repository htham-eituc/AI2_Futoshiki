"""
Heuristic helpers for Futoshiki solvers.

Constraint format (chuẩn Futoshiki):
  h_constraints[r][c] = 1   →  cell (r,c) < cell (r, c+1)
  h_constraints[r][c] = -1  →  cell (r,c) > cell (r, c+1)
  h_constraints[r][c] = 0   →  không có ràng buộc
  (tương tự cho v_constraints theo chiều dọc)

h2 (inequality-aware):
  h2(s) = Σ (|domain(cell)| - 1)   [raw domain size, không qua ineq filter]
        = 0   iff every cell is assigned
        = ∞   iff any domain is empty

  Tại sao dùng raw size thay vì effective size?
  - effective size đòi hỏi gọi _effective_size() cho mỗi cell bị prune,
    benchmark cho thấy chậm hơn 5× so với raw count.
  - Raw size vẫn admissible (raw >= effective nên h <= h*).
  - Correctness đảm bảo bằng is_goal() validate đầy đủ, không phải bằng
    việc h phải tight.

  forward_check_ineq trả về delta_h = -(số giá trị bị loại khỏi raw domain),
  nhất quán với định nghĩa h2 ở trên.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

Cell   = Tuple[int, int]
Domain = Dict[Cell, Set[int]]

# ---------------------------------------------------------------------------
# Constraint helpers
# ---------------------------------------------------------------------------

def build_ineq_map(
    n: int,
    h_constraints: List[List[int]],
    v_constraints: List[List[int]],
) -> Dict[Cell, List[Tuple[Cell, int]]]:
    """
    Xây dựng bảng tra cứu nhanh:
      ineq_map[cell] = [(neighbour, sign), ...]
    với sign = +1 nghĩa là cell < neighbour,
         sign = -1 nghĩa là cell > neighbour.
    Gọi một lần duy nhất lúc khởi tạo solver.
    """
    ineq_map: Dict[Cell, List[Tuple[Cell, int]]] = {
        (r, c): [] for r in range(n) for c in range(n)
    }
    for r in range(n):
        for c in range(n - 1):
            s = h_constraints[r][c]
            if s != 0:
                ineq_map[(r, c)].append(((r, c + 1),  s))
                ineq_map[(r, c + 1)].append(((r, c), -s))
    for r in range(n - 1):
        for c in range(n):
            s = v_constraints[r][c]
            if s != 0:
                ineq_map[(r, c)].append(((r + 1, c),  s))
                ineq_map[(r + 1, c)].append(((r, c), -s))
    return ineq_map


def build_peers_map(n: int) -> Dict[Cell, List[Cell]]:
    """
    Precompute danh sách peers (cùng hàng + cột) cho mỗi cell.
    Tránh list-comprehension O(N) lặp lại trong mỗi node expansion.
    """
    peers_map: Dict[Cell, List[Cell]] = {}
    for r in range(n):
        for c in range(n):
            peers_map[(r, c)] = (
                [(r, col) for col in range(n) if col != c] +
                [(row, c)  for row in range(n) if row != r]
            )
    return peers_map


# ---------------------------------------------------------------------------
# Domain initialisation
# ---------------------------------------------------------------------------

def build_initial_domains(n: int, grid: List[List[int]]) -> Domain:
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
    """h2 = Σ (|domain(cell)| - 1). inf nếu có domain rỗng."""
    total = 0
    for vals in domains.values():
        k = len(vals)
        if k == 0:
            return float("inf")
        total += k - 1
    return total


def compute_heuristic_ineq(
    domains: Domain,
    ineq_map: Dict[Cell, List[Tuple[Cell, int]]],
) -> float:
    """
    Alias của compute_heuristic — dùng raw domain size.
    Giữ tên để tương thích với caller (astar.py).
    ineq_map không dùng ở đây nhưng giữ signature để không cần sửa caller.
    """
    return compute_heuristic(domains)


# ---------------------------------------------------------------------------
# Variable / value ordering
# ---------------------------------------------------------------------------

def select_mrv_cell(domains: Domain) -> Optional[Cell]:
    """MRV: pick unassigned cell with smallest domain (> 1)."""
    unassigned = {cell: vals for cell, vals in domains.items() if len(vals) > 1}
    if not unassigned:
        return None
    return min(unassigned, key=lambda cell: len(unassigned[cell]))


def select_mrv_cell_ineq(
    domains: Domain,
    ineq_map: Dict[Cell, List[Tuple[Cell, int]]],
) -> Optional[Cell]:
    """
    MRV tích hợp inequality: ưu tiên cell có effective domain nhỏ nhất.
    Fail-first: trả ngay nếu phát hiện cell có effective domain = 0.

    Chỉ compute effective domain cho MRV (gọi 1 lần per node, không per child)
    → chi phí chấp nhận được.
    """
    best_cell: Optional[Cell] = None
    best_size: int = 10**9

    for cell, vals in domains.items():
        if len(vals) <= 1:
            continue

        effective = set(vals)
        for neighbour, sign in ineq_map.get(cell, []):
            nb_vals = domains[neighbour]
            if len(nb_vals) != 1:
                continue
            (nb_val,) = nb_vals
            if sign == 1:
                effective = {v for v in effective if v < nb_val}
            else:
                effective = {v for v in effective if v > nb_val}
            if not effective:
                return cell   # fail-first

        size = len(effective)
        if size < best_size:
            best_size = size
            best_cell = cell

    return best_cell


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


def lcv_order_ineq(
    cell: Cell,
    domains: Domain,
    n: int,
    ineq_map: Dict[Cell, List[Tuple[Cell, int]]],
    peers_map: Optional[Dict[Cell, List[Cell]]] = None,
) -> List[int]:
    """
    LCV tích hợp inequality.
    peers_map: precomputed để tránh list-comp O(N) mỗi lần.
    """
    r, c = cell

    # Lọc effective domain
    effective = set(domains[cell])
    for neighbour, sign in ineq_map.get(cell, []):
        nb_vals = domains[neighbour]
        if len(nb_vals) != 1:
            continue
        (nb_val,) = nb_vals
        if sign == 1:
            effective = {v for v in effective if v < nb_val}
        else:
            effective = {v for v in effective if v > nb_val}
        if not effective:
            return []

    row_col_peers = peers_map[cell] if peers_map is not None else (
        [(r, col) for col in range(n) if col != c] +
        [(row, c)  for row in range(n) if row != r]
    )

    def count_eliminated(v: int) -> int:
        elim = sum(1 for peer in row_col_peers if v in domains[peer])
        for nb, sign in ineq_map.get(cell, []):
            if len(domains[nb]) <= 1:
                continue
            if sign == 1:
                elim += sum(1 for nb_val in domains[nb] if nb_val <= v)
            else:
                elim += sum(1 for nb_val in domains[nb] if nb_val >= v)
        return elim

    return sorted(effective, key=count_eliminated)


# ---------------------------------------------------------------------------
# Forward checking  (delta_h = raw discard count, nhất quán với h2 raw)
# ---------------------------------------------------------------------------

def forward_check_ineq(
    domains: Domain,
    assigned: Cell,
    n: int,
    ineq_map: Dict[Cell, List[Tuple[Cell, int]]],
    peers_map: Optional[Dict[Cell, List[Cell]]] = None,
) -> Tuple[Optional[Domain], float]:
    """
    Forward checking tích hợp inequality constraints.

    delta_h = -(số giá trị bị loại khỏi raw domain).
    Nhất quán với h2 = Σ (|domain| - 1):
      mỗi giá trị bị loại giảm |domain| đi 1 → h giảm 1.

    Trả về:
      (None, inf)          nếu có domain nào rỗng
      (domains, delta_h)   delta_h <= 0
    """
    r, c = assigned
    (val,) = domains[assigned]
    delta_h = 0.0

    # --- ≠ constraint (hàng + cột) ---
    peers = peers_map[assigned] if peers_map is not None else (
        [(r, col) for col in range(n) if col != c] +
        [(row, c)  for row in range(n) if row != r]
    )
    for peer in peers:
        if val in domains[peer]:
            domains[peer].discard(val)
            if not domains[peer]:
                return None, float("inf")
            delta_h -= 1

    # --- inequality constraints ---
    for neighbour, sign in ineq_map.get(assigned, []):
        nb_vals = domains[neighbour]
        if len(nb_vals) == 1:
            continue
        if sign == 1:
            to_remove = {v for v in nb_vals if v <= val}
        else:
            to_remove = {v for v in nb_vals if v >= val}
        if to_remove:
            nb_vals -= to_remove
            if not nb_vals:
                return None, float("inf")
            delta_h -= len(to_remove)

    return domains, delta_h


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def domains_to_grid(domains: Domain, n: int) -> List[List[int]]:
    grid = [[0] * n for _ in range(n)]
    for (r, c), vals in domains.items():
        if len(vals) == 1:
            (grid[r][c],) = vals
    return grid


def shallow_copy_domains(domains: Domain) -> Domain:
    return {cell: set(vals) for cell, vals in domains.items()}


__all__ = [
    "Cell", "Domain",
    "build_initial_domains",
    "build_ineq_map",
    "build_peers_map",
    "compute_heuristic",
    "compute_heuristic_ineq",
    "select_mrv_cell",
    "select_mrv_cell_ineq",
    "lcv_order",
    "lcv_order_ineq",
    "forward_check_ineq",
    "domains_to_grid",
    "shallow_copy_domains",
]