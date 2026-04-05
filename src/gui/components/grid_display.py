"""
Grid Display Component - Renders Futoshiki puzzle grid with constraints.
"""

from typing import List, Optional, Set, Tuple
import streamlit as st


# Color constants for highlighting
COLORS = {
    "active": "#ffeb3b",      # Yellow - currently processing
    "changed": "#4caf50",     # Green - just assigned
    "conflict": "#f44336",    # Red - constraint violation
    "default": "#ffffff",     # White - normal cell
    "given": "#e3f2fd",       # Light blue - initial given values
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
        font-family: 'Courier New', monospace;
        font-size: 24px;
        margin: 20px auto;
    }
    .futoshiki-grid table {
        border-collapse: collapse;
    }
    .futoshiki-grid .cell {
        width: 50px;
        height: 50px;
        text-align: center;
        vertical-align: middle;
        border: 2px solid #555;
        font-weight: bold;
        color: #111111 !important;   /* always dark text — works on both light/dark theme */
    }
    .futoshiki-grid .h-constraint {
        width: 30px;
        text-align: center;
        vertical-align: middle;
        font-size: 20px;
        color: #aaaaaa;
    }
    .futoshiki-grid .v-constraint {
        height: 20px;
        text-align: center;
        vertical-align: middle;
        font-size: 16px;
        color: #aaaaaa;
    }
    .futoshiki-grid .spacer {
        width: 30px;
        height: 20px;
    }
    </style>
    """

    rows_html = []

    for row in range(size):
        cells_html = []
        for col in range(size):
            value = grid[row][col]
            display_value = str(value) if value != 0 else ""

            # Determine background color (priority: changed > active > conflict > given > default)
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

            # Horizontal constraint symbol
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

        # Vertical constraint row
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
    """Render a simple grid without constraints (for quick display)."""
    render_grid(grid=grid, size=size)


__all__ = ["render_grid", "render_grid_simple", "COLORS"]