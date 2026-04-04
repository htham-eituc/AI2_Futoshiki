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
    """
    Render algorithm metrics display.
    
    Args:
        metrics: Dictionary of metric values.
        is_live: Whether metrics are updating live.
        show_title: Whether to show the "Metrics" title.
    """
    if show_title:
        title = "📊 Live Metrics" if is_live else "📊 Final Metrics"
        st.markdown(f"### {title}")
    
    # Primary metrics in columns
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
    
    # Secondary metrics
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
    """
    Render final solve status.
    
    Args:
        is_solved: Whether puzzle was solved.
        message: Optional status message.
    """
    if is_solved:
        st.success("✅ " + (message or "Puzzle Solved!"))
    else:
        st.error("❌ " + (message or "No solution found"))


def render_algorithm_badge(algorithm_name: str) -> None:
    """
    Display the current algorithm name prominently.
    
    Args:
        algorithm_name: Name of the algorithm.
    """
    st.markdown(
        f"""
        <div style="
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 16px;
            margin: 10px 0;
        ">
            🔬 {algorithm_name.upper()}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_step_message(message: str) -> None:
    """
    Display a step message/status.
    
    Args:
        message: Message to display.
    """
    if message:
        st.info(f"💡 {message}")


def _format_number(n: int) -> str:
    """Format large numbers with comma separators."""
    return f"{n:,}"


__all__ = [
    "render_metrics",
    "render_final_status",
    "render_algorithm_badge",
    "render_step_message",
]