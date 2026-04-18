"""
Grid Display Component - Renders Futoshiki puzzle grid with constraints.
"""

from typing import List, Optional, Set, Tuple
import streamlit as st


                                                                 
COLORS = {
    "active": "var(--grid-active)",                            
    "changed": "var(--grid-changed)",                   
    "conflict": "var(--grid-conflict)",                        
    "default": "var(--grid-default)",                 
    "given": "var(--grid-given)",                              
}


def render_grid(
    grid: List[List[int]],
    size: int,
    h_constraints: Optional[List[List[int]]] = None,
    v_constraints: Optional[List[List[int]]] = None,
    active_cell: Optional[Tuple[int, int]] = None,
    changed_cell: Optional[Tuple[int, int]] = None,
    conflict_cells: Optional[List[Tuple[int, int]]] = None,
    given_cells: Optional[Set[Tuple[int, int]]] = None,
) -> None:
    """
    Render the Futoshiki grid with inequality constraints.

    Args:
        grid: 2D list of cell values (0 = empty).
        size: Grid size (NxN).
        h_constraints: Horizontal constraints (1=<, -1=>, 0=none).
        v_constraints: Vertical constraints (1=<, -1=>, 0=none).
        active_cell: Cell currently being processed (row, col).
        changed_cell: Cell that was just changed (row, col).
        conflict_cells: List of cells with conflicts.
        given_cells: Set of cells that were initially given.
    """
    conflict_set = set(conflict_cells) if conflict_cells else set()
    given_set = given_cells or set()

    html = _build_grid_html(
        grid=grid,
        size=size,
        h_constraints=h_constraints,
        v_constraints=v_constraints,
        active_cell=active_cell,
        changed_cell=changed_cell,
        conflict_set=conflict_set,
        given_set=given_set,
    )

    st.markdown(html, unsafe_allow_html=True)


def _build_grid_html(
    grid: List[List[int]],
    size: int,
    h_constraints: Optional[List[List[int]]],
    v_constraints: Optional[List[List[int]]],
    active_cell: Optional[Tuple[int, int]],
    changed_cell: Optional[Tuple[int, int]],
    conflict_set: Set[Tuple[int, int]],
    given_set: Set[Tuple[int, int]],
) -> str:
    """Build HTML for the grid display."""

    css = """
    <style>
    .futoshiki-grid {
        display: inline-block;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 24px;
        margin: 24px auto;
        padding: 20px;
        background: var(--bg-surface);
        border-radius: var(--radius-lg);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .futoshiki-grid table {
        border-collapse: separate;
        border-spacing: 2px;
    }
    .futoshiki-grid .cell {
        width: 54px;
        height: 54px;
        text-align: center;
        vertical-align: middle;
        border: 2px solid var(--grid-border);
        font-weight: 600;
        color: var(--text-primary) !important;
        border-radius: var(--radius-sm);
        transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
    }
    .futoshiki-grid .cell:hover {
        transform: scale(1.05);
        z-index: 1;
    }
    .futoshiki-grid .h-constraint {
        width: 26px;
        text-align: center;
        vertical-align: middle;
        font-size: 20px;
        font-weight: 600;
        color: var(--accent-primary);
        opacity: 0.9;
    }
    .futoshiki-grid .v-constraint {
        height: 24px;
        text-align: center;
        vertical-align: middle;
        font-size: 16px;
        font-weight: 600;
        color: var(--accent-primary);
        opacity: 0.9;
    }
    .futoshiki-grid .spacer {
        width: 26px;
        height: 24px;
    }
    </style>
    """

    rows_html = []

    for row in range(size):
        cells_html = []
        for col in range(size):
            value = grid[row][col]
            display_value = str(value) if value != 0 else ""

                                                                                                  
            bg_color = COLORS["default"]
            if (row, col) == changed_cell:
                bg_color = COLORS["changed"]
            elif (row, col) == active_cell:
                bg_color = COLORS["active"]
            elif (row, col) in conflict_set:
                bg_color = COLORS["conflict"]
            elif (row, col) in given_set:
                bg_color = COLORS["given"]

            cells_html.append(
                f'<td class="cell" style="background-color: {bg_color};">'
                f'{display_value}</td>'
            )

                                          
            if col < size - 1:
                h_symbol = ""
                if h_constraints and len(h_constraints) > row and len(h_constraints[row]) > col:
                    constraint = h_constraints[row][col]
                    if constraint == 1:
                        h_symbol = "&lt;"
                    elif constraint == -1:
                        h_symbol = "&gt;"

                cells_html.append(f'<td class="h-constraint">{h_symbol}</td>')

        rows_html.append(f'<tr>{"".join(cells_html)}</tr>')

                                 
        if row < size - 1:
            v_cells_html = []
            for col in range(size):
                v_symbol = ""
                if v_constraints and len(v_constraints) > row and len(v_constraints[row]) > col:
                    constraint = v_constraints[row][col]
                    if constraint == 1:
                        v_symbol = "∧"
                    elif constraint == -1:
                        v_symbol = "∨"

                v_cells_html.append(f'<td class="v-constraint">{v_symbol}</td>')

                if col < size - 1:
                    v_cells_html.append('<td class="spacer"></td>')

            rows_html.append(f'<tr>{"".join(v_cells_html)}</tr>')

    table_html = f'<table>{"".join(rows_html)}</table>'
    return f'{css}<div class="futoshiki-grid">{table_html}</div>'


def render_grid_simple(grid: List[List[int]], size: int) -> None:
    render_grid(grid=grid, size=size)


__all__ = ["render_grid", "render_grid_simple", "COLORS"]
