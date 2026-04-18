"""
Metrics Display Component - Shows algorithm execution statistics.
"""

from typing import Any, Dict, Optional
import streamlit as st


def render_metrics(
    metrics: Dict[str, Any],
    is_live: bool = False,
    show_title: bool = True,
) -> None:
    if show_title:
        title = "Live Metrics" if is_live else "Final Metrics"
        st.markdown(f"### {title}")
    
                                
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Nodes Generated",
            _format_number(metrics.get("nodes_generated", 0)),
        )
    
    with col2:
        st.metric(
            "Nodes Expanded",
            _format_number(metrics.get("nodes_expanded", 0)),
        )
    
    with col3:
        st.metric(
            "Constraint Checks",
            _format_number(metrics.get("constraint_checks", 0)),
        )
    
    with col4:
        st.metric(
            "Backtracks",
            _format_number(metrics.get("backtracks", 0)),
        )
    
                       
    col5, col6 = st.columns(2)
    
    with col5:
        st.metric(
            "Assignments",
            _format_number(metrics.get("assignments", 0)),
        )
    
    with col6:
        elapsed = metrics.get("elapsed_seconds", 0)
        if elapsed >= 1:
            display_time = f"{elapsed:.3f}s"
        elif elapsed >= 0.001:
            display_time = f"{elapsed * 1000:.2f}ms"
        elif elapsed >= 0.000001:
            display_time = f"{elapsed * 1_000_000:.2f}µs"
        elif elapsed > 0:
            display_time = f"{elapsed * 1_000_000:.4f}µs"
        else:
            display_time = "—"
        
    st.metric("Elapsed Time", display_time)


def render_final_status(
    is_solved: bool,
    message: str = "",
) -> None:
    if is_solved:
        st.success(message or "Puzzle Solved!")
    else:
        st.error(message or "No solution found")


def render_algorithm_badge(algorithm_name: str) -> None:
    st.markdown(
        f"""
        <div style="
            display: inline-flex;
            align-items: center;
            background: var(--accent-primary);
            color: var(--text-inverse);
            padding: 8px 18px;
            border-radius: var(--radius-md);
            font-weight: 600;
            font-size: 13px;
            letter-spacing: 0.04em;
            margin: 12px 0;
            box-shadow: var(--shadow-sm);
        ">
            {algorithm_name.upper()}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_step_message(message: str) -> None:
    if message:
        st.info(message)


def _format_number(n: int) -> str:
    return f"{n:,}"


__all__ = [
    "render_metrics",
    "render_final_status",
    "render_algorithm_badge",
    "render_step_message",
]
