import streamlit as st
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solver import solve_puzzle
from test_generate_backtrack import generate

# ─── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Futoshiki",
    page_icon="🔢",
    layout="centered",
)

# ─── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Playfair+Display:wght@700;900&display=swap');

:root {
    --bg:       #0f0f0f;
    --surface:  #1a1a1a;
    --border:   #2e2e2e;
    --accent:   #e8c547;
    --accent2:  #e87447;
    --text:     #f0f0f0;
    --muted:    #666;
    --given:    #e8c547;
    --error:    #e84747;
    --pencil:   #7ab8e8;
    --ok:       #47e894;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'DM Mono', monospace !important;
}

[data-testid="stSidebar"] { display: none; }
[data-testid="stHeader"] { display: none; }
footer { display: none; }

/* Remove streamlit default padding */
.block-container { padding: 2rem 1rem 2rem 1rem !important; max-width: 800px !important; }

/* Title */
.fuто-title {
    font-family: 'Playfair Display', serif;
    font-size: 3rem;
    font-weight: 900;
    letter-spacing: -1px;
    color: var(--text);
    margin: 0;
    line-height: 1;
}
.futo-title span { color: var(--accent); }
.futo-subtitle {
    font-family: 'DM Mono', monospace;
    font-size: 0.75rem;
    color: var(--muted);
    letter-spacing: 4px;
    text-transform: uppercase;
    margin-top: 0.4rem;
    margin-bottom: 2rem;
}

/* Controls row */
.ctrl-label {
    font-size: 0.65rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 4px;
}

/* Timer badge */
.timer-badge {
    font-family: 'DM Mono', monospace;
    font-size: 1.6rem;
    font-weight: 500;
    color: var(--accent);
    letter-spacing: 2px;
    padding: 0.4rem 1rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--surface);
    display: inline-block;
    min-width: 90px;
    text-align: center;
}

/* Status message */
.status-ok  { color: var(--ok);    font-size:0.85rem; letter-spacing:2px; text-transform:uppercase; }
.status-err { color: var(--error); font-size:0.85rem; letter-spacing:2px; text-transform:uppercase; }
.status-inf { color: var(--muted); font-size:0.85rem; letter-spacing:2px; text-transform:uppercase; }

/* Pencil mode badge */
.mode-badge {
    font-size: 0.7rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 20px;
    display: inline-block;
}
.mode-pencil { background: rgba(122,184,232,0.15); color: var(--pencil); border: 1px solid var(--pencil); }
.mode-normal { background: rgba(232,197,71,0.12);  color: var(--accent);  border: 1px solid var(--accent); }

/* Grid table */
.futo-grid-wrap { display: flex; justify-content: center; margin: 1.5rem 0; }
table.futo-grid {
    border-collapse: separate;
    border-spacing: 0;
}
table.futo-grid td { padding: 0; }

.futo-cell {
    width: 56px; height: 56px;
    border: 2px solid var(--border);
    text-align: center; vertical-align: middle;
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem;
    font-weight: 700;
    cursor: pointer;
    user-select: none;
    border-radius: 4px;
    transition: all 0.15s ease;
    background: var(--surface);
    color: var(--text);
    position: relative;
}
.futo-cell.given      { color: var(--given); background: rgba(232,197,71,0.08); cursor: default; }
.futo-cell.selected   { border-color: var(--accent); box-shadow: 0 0 0 2px rgba(232,197,71,0.35); }
.futo-cell.highlight  { background: rgba(232,197,71,0.05); }
.futo-cell.error      { color: var(--error); border-color: rgba(232,71,71,0.5); }
.futo-cell.solved-anim{ color: var(--ok); }
.futo-cell.pencil-cell{
    font-family: 'DM Mono', monospace;
    font-size: 0.55rem;
    color: var(--pencil);
    line-height: 1.2;
    display: flex; align-items: center; justify-content: center;
    flex-wrap: wrap;
}

/* Constraint cells */
.futo-hcon {
    width: 28px; height: 56px;
    text-align: center; vertical-align: middle;
    font-family: 'DM Mono', monospace;
    font-size: 1.2rem;
    color: var(--accent2);
    font-weight: 500;
}
.futo-vcon {
    width: 56px; height: 24px;
    text-align: center; vertical-align: middle;
    font-family: 'DM Mono', monospace;
    font-size: 1rem;
    color: var(--accent2);
    font-weight: 500;
}
.futo-corner { width: 28px; height: 24px; }

/* Streamlit button overrides */
.stButton > button {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.72rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    border-radius: 4px !important;
    border: 1px solid var(--border) !important;
    background: var(--surface) !important;
    color: var(--text) !important;
    padding: 0.5rem 1rem !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}
.stSelectbox > div, .stSlider { font-family: 'DM Mono', monospace !important; }

div[data-testid="stSelectbox"] > div > div {
    background: var(--surface) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.8rem !important;
}

/* Divider */
.futo-divider { border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)


# ─── Session state init ──────────────────────────────────────────────────────
def init_state():
    defaults = {
        "n": 5,
        "grid": None,          # puzzle (0 = empty)
        "given": None,         # bool mask of pre-filled cells
        "h_con": None,
        "v_con": None,
        "user_grid": None,     # user's answers
        "pencil": None,        # pencil notes: list of sets
        "selected": None,      # (row, col)
        "pencil_mode": False,
        "timer_start": None,
        "timer_elapsed": 0,
        "timer_running": False,
        "solved": False,
        "solution": None,
        "status_msg": "",
        "status_type": "inf",  # ok | err | inf
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
s = st.session_state


# ─── Helpers ────────────────────────────────────────────────────────────────
def load_puzzle(n, difficulty):
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath, solution = generate(n=n, difficulty=difficulty, output_dir=tmpdir)
        from solver import parse_puzzle_file
        pn, grid, h_con, v_con = parse_puzzle_file(filepath)

    s.n = pn
    s.grid = grid
    s.h_con = h_con
    s.v_con = v_con
    s.given = [[grid[r][c] != 0 for c in range(pn)] for r in range(pn)]
    s.user_grid = [[grid[r][c] for c in range(pn)] for r in range(pn)]
    s.pencil = [[set() for _ in range(pn)] for _ in range(pn)]
    s.selected = None
    s.pencil_mode = False
    s.solved = False
    s.solution = solution
    s.status_msg = f"New {pn}×{pn} {difficulty} puzzle — good luck!"
    s.status_type = "inf"
    s.timer_start = time.time()
    s.timer_running = True
    s.timer_elapsed = 0


def elapsed_str():
    if s.timer_running and s.timer_start:
        total = int(time.time() - s.timer_start) + s.timer_elapsed
    else:
        total = s.timer_elapsed
    m, sec = divmod(total, 60)
    return f"{m:02d}:{sec:02d}"


def has_errors():
    if s.user_grid is None:
        return False
    n = s.n
    ug = s.user_grid
    for r in range(n):
        vals = [ug[r][c] for c in range(n) if ug[r][c] != 0]
        if len(vals) != len(set(vals)):
            return True
    for c in range(n):
        vals = [ug[r][c] for r in range(n) if ug[r][c] != 0]
        if len(vals) != len(set(vals)):
            return True
    # Check constraints
    for r in range(n):
        for c in range(n - 1):
            con = s.h_con[r][c]
            left, right = ug[r][c], ug[r][c + 1]
            if con != 0 and left != 0 and right != 0:
                if con == 1 and not left < right:
                    return True
                if con == -1 and not left > right:
                    return True
    for r in range(n - 1):
        for c in range(n):
            con = s.v_con[r][c]
            top, bot = ug[r][c], ug[r + 1][c]
            if con != 0 and top != 0 and bot != 0:
                if con == 1 and not top < bot:
                    return True
                if con == -1 and not top > bot:
                    return True
    return False


def cell_has_error(r, c):
    if s.user_grid is None:
        return False
    val = s.user_grid[r][c]
    if val == 0:
        return False
    n = s.n
    ug = s.user_grid
    # Row dup
    for cc in range(n):
        if cc != c and ug[r][cc] == val:
            return True
    # Col dup
    for rr in range(n):
        if rr != r and ug[rr][c] == val:
            return True
    # H constraints
    for cc in range(n - 1):
        con = s.h_con[r][cc]
        if con == 0: continue
        l, ri = ug[r][cc], ug[r][cc + 1]
        if l != 0 and ri != 0:
            if con == 1 and not l < ri and (c == cc or c == cc + 1): return True
            if con == -1 and not l > ri and (c == cc or c == cc + 1): return True
    # V constraints
    for rr in range(n - 1):
        con = s.v_con[rr][c]
        if con == 0: continue
        t, b = ug[rr][c], ug[rr + 1][c]
        if t != 0 and b != 0:
            if con == 1 and not t < b and (r == rr or r == rr + 1): return True
            if con == -1 and not t > b and (r == rr or r == rr + 1): return True
    return False


def check_complete():
    if s.user_grid is None:
        return False
    n = s.n
    for r in range(n):
        for c in range(n):
            if s.user_grid[r][c] == 0:
                return False
    return not has_errors()


def auto_solve():
    status, sol, bt = solve_puzzle(s.n, s.grid, s.h_con, s.v_con)
    if status == "unique":
        s.user_grid = [row[:] for row in sol]
        s.solution = sol
        s.solved = True
        s.timer_running = False
        if s.timer_start:
            s.timer_elapsed += int(time.time() - s.timer_start)
        s.status_msg = f"Solved! ({bt} backtracks)"
        s.status_type = "ok"
    else:
        s.status_msg = "No unique solution found."
        s.status_type = "err"


H_CHARS = {1: "<", -1: ">", 0: ""}
V_CHARS = {1: "∨", -1: "∧", 0: ""}


def build_grid_html():
    if s.grid is None:
        return ""
    n = s.n
    sel = s.selected
    ug = s.user_grid
    pencil = s.pencil

    rows_html = []
    for r in range(n):
        # ── Data row ──────────────────────────────────────────────────────
        tds = []
        for c in range(n):
            val = ug[r][c]
            is_given = s.given[r][c]
            is_sel = sel == (r, c)
            is_hl = sel is not None and (sel[0] == r or sel[1] == c) and not is_sel
            is_err = cell_has_error(r, c)
            is_solved = s.solved

            classes = ["futo-cell"]
            if is_given:   classes.append("given")
            if is_sel:     classes.append("selected")
            elif is_hl:    classes.append("highlight")
            if is_err:     classes.append("error")
            if is_solved and not is_given: classes.append("solved-anim")

            # Pencil notes
            notes = pencil[r][c]
            if val == 0 and notes:
                note_str = " ".join(str(x) for x in sorted(notes))
                inner = f'<span style="font-size:0.6rem;color:var(--pencil);font-family:\'DM Mono\',monospace;">{note_str}</span>'
            elif val != 0:
                inner = str(val)
            else:
                inner = ""

            onclick = f"window.location.href='?sel={r},{c}'" if not is_given else ""
            tds.append(
                f'<td><div class="{" ".join(classes)}" '
                f'onclick="{onclick}">{inner}</div></td>'
            )
            # Horizontal constraint
            if c < n - 1:
                con_char = H_CHARS.get(s.h_con[r][c], "")
                tds.append(f'<td class="futo-hcon">{con_char}</td>')

        rows_html.append("<tr>" + "".join(tds) + "</tr>")

        # ── Constraint row ────────────────────────────────────────────────
        if r < n - 1:
            vtds = []
            for c in range(n):
                con_char = V_CHARS.get(s.v_con[r][c], "")
                vtds.append(f'<td class="futo-vcon">{con_char}</td>')
                if c < n - 1:
                    vtds.append('<td class="futo-corner"></td>')
            rows_html.append("<tr>" + "".join(vtds) + "</tr>")

    return f'<div class="futo-grid-wrap"><table class="futo-grid">{"".join(rows_html)}</table></div>'


# ─── Handle URL param for cell selection (JS workaround) ────────────────────
params = st.query_params
if "sel" in params:
    sel_val = params["sel"]
    try:
        r, c = map(int, sel_val.split(","))
        s.selected = (r, c)
    except Exception:
        pass
    st.query_params.clear()


# ─── HEADER ─────────────────────────────────────────────────────────────────
st.markdown("""
<div>
  <p class="fuто-title">Futo<span>shiki</span></p>
  <p class="futo-subtitle">Logic &nbsp;·&nbsp; Inequalities &nbsp;·&nbsp; No guessing</p>
</div>
""", unsafe_allow_html=True)

# ─── CONTROLS ───────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns([1.5, 1.5, 1, 1, 1.2])

with c1:
    st.markdown('<div class="ctrl-label">Grid Size</div>', unsafe_allow_html=True)
    size_choice = st.selectbox("size", [4, 5, 6, 7, 9], index=1,
                               label_visibility="collapsed",
                               key="size_select")

with c2:
    st.markdown('<div class="ctrl-label">Difficulty</div>', unsafe_allow_html=True)
    diff_choice = st.selectbox("diff", ["easy", "medium", "hard"], index=1,
                               label_visibility="collapsed",
                               key="diff_select")

with c3:
    st.markdown('<div class="ctrl-label">&nbsp;</div>', unsafe_allow_html=True)
    if st.button("⟳  Generate", use_container_width=True):
        with st.spinner("Generating…"):
            load_puzzle(size_choice, diff_choice)
        st.rerun()

with c4:
    st.markdown('<div class="ctrl-label">&nbsp;</div>', unsafe_allow_html=True)
    if st.button("✦  Solve", use_container_width=True):
        if s.grid is not None:
            auto_solve()
            st.rerun()

with c5:
    st.markdown('<div class="ctrl-label">Timer</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="timer-badge">{elapsed_str()}</div>', unsafe_allow_html=True)

st.markdown('<hr class="futo-divider">', unsafe_allow_html=True)

# ─── STATUS + MODE BADGE ─────────────────────────────────────────────────────
row_status = st.columns([3, 1])
with row_status[0]:
    if s.status_msg:
        cls = f"status-{s.status_type}"
        st.markdown(f'<p class="{cls}">{s.status_msg}</p>', unsafe_allow_html=True)
with row_status[1]:
    mode_cls = "mode-pencil" if s.pencil_mode else "mode-normal"
    mode_lbl = "✏ Pencil" if s.pencil_mode else "✦ Normal"
    st.markdown(f'<p style="text-align:right"><span class="mode-badge {mode_cls}">{mode_lbl}</span></p>',
                unsafe_allow_html=True)

# ─── GRID ───────────────────────────────────────────────────────────────────
if s.grid is None:
    st.markdown("""
    <div style="text-align:center;padding:4rem 0;color:var(--muted);font-size:0.85rem;letter-spacing:3px;text-transform:uppercase;">
        Select a size and difficulty, then hit Generate
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(build_grid_html(), unsafe_allow_html=True)

    # ── Input row ────────────────────────────────────────────────────────────
    st.markdown('<hr class="futo-divider">', unsafe_allow_html=True)

    if s.selected and not s.solved:
        r, c = s.selected
        if not s.given[r][c]:
            inp_cols = st.columns([2, 2, 2, 1])
            with inp_cols[0]:
                st.markdown('<div class="ctrl-label">Enter value</div>', unsafe_allow_html=True)
                num_str = st.selectbox(
                    "val", ["(clear)"] + [str(i) for i in range(1, s.n + 1)],
                    label_visibility="collapsed", key="val_select"
                )
                if st.button("Place", use_container_width=True):
                    if num_str == "(clear)":
                        s.user_grid[r][c] = 0
                        s.pencil[r][c] = set()
                    else:
                        v = int(num_str)
                        if s.pencil_mode:
                            notes = s.pencil[r][c]
                            if v in notes:
                                notes.discard(v)
                            else:
                                notes.add(v)
                            s.user_grid[r][c] = 0
                        else:
                            s.user_grid[r][c] = v
                            s.pencil[r][c] = set()
                    # Check completion
                    if check_complete():
                        s.solved = True
                        s.timer_running = False
                        if s.timer_start:
                            s.timer_elapsed += int(time.time() - s.timer_start)
                        s.status_msg = f"🎉 Puzzle complete! Time: {elapsed_str()}"
                        s.status_type = "ok"
                    else:
                        errs = has_errors()
                        s.status_msg = "⚠ Error detected" if errs else ""
                        s.status_type = "err" if errs else "inf"
                    st.rerun()

            with inp_cols[1]:
                st.markdown('<div class="ctrl-label">Mode</div>', unsafe_allow_html=True)
                if st.button(
                    "✏ Pencil ON" if not s.pencil_mode else "✦ Normal mode",
                    use_container_width=True
                ):
                    s.pencil_mode = not s.pencil_mode
                    st.rerun()

            with inp_cols[2]:
                st.markdown('<div class="ctrl-label">Cell</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<p style="font-size:0.8rem;color:var(--muted);padding-top:8px;">'
                    f'Row {r+1}, Col {c+1} selected</p>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown('<p class="status-inf">Given cell — select an empty cell to enter a value</p>',
                        unsafe_allow_html=True)
    elif s.solved:
        st.markdown('<p class="status-ok">✦ Puzzle solved — generate a new one!</p>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<p class="status-inf">Click a cell to select it</p>',
                    unsafe_allow_html=True)

    # ── Timer auto-refresh ───────────────────────────────────────────────────
    if s.timer_running:
        time.sleep(1)
        st.rerun()