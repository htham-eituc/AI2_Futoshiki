"""
Compare Mode Screen - Multi-algorithm comparison with charts.
"""

from pathlib import Path
from typing import List
import streamlit as st

from ..service.visualization_service import (
    VisualizationService,
    ExperimentVisualizationError,
)


def _init_session_state() -> None:
    """Initialize session state variables for compare mode."""
    defaults = {
        "compare_experiment_charts": [],
        "compare_experiment_error": None,
        "compare_experiment_running": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _set_experiment_viz_running() -> None:
    """Set experiment visualization UI state to running."""
    st.session_state["compare_experiment_running"] = True
    st.session_state["compare_experiment_error"] = None


def _set_experiment_viz_success(chart_paths: List[Path]) -> None:
    """Set experiment visualization UI state to success."""
    st.session_state["compare_experiment_running"] = False
    st.session_state["compare_experiment_error"] = None
    st.session_state["compare_experiment_charts"] = [str(path) for path in chart_paths]


def _set_experiment_viz_error(message: str) -> None:
    """Set experiment visualization UI state to error."""
    st.session_state["compare_experiment_running"] = False
    st.session_state["compare_experiment_error"] = message
    st.session_state["compare_experiment_charts"] = []


def render_compare_mode() -> None:
    """Render the compare mode screen."""
    _init_session_state()
    
    # Header with back button
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("← Back to Home"):
            # Clear compare state
            for key in list(st.session_state.keys()):
                if key.startswith("compare_"):
                    del st.session_state[key]
            st.session_state["screen"] = "home"
            st.rerun()
    
    with col_title:
        st.markdown("## Compare Algorithms")
    
    # Breadcrumb
    st.markdown(
        '<p style="color: var(--text-muted); font-size: 14px;">Home > Compare Algorithms</p>',
        unsafe_allow_html=True,
    )
    
    st.markdown("---")

    # Experiment CSV visualization section
    st.markdown("### Experiment CSV Visualization")
    st.caption("Touch/click to generate charts from experiment.csv and show them here.")

    if st.button(
        "Visualize experiment.csv",
        use_container_width=True,
        disabled=st.session_state["compare_experiment_running"],
    ):
        _set_experiment_viz_running()
        with st.spinner("Generating experiment visualizations..."):
            try:
                chart_paths = VisualizationService.generate_experiment_visualizations()
                _set_experiment_viz_success(chart_paths)
            except ExperimentVisualizationError as exc:
                _set_experiment_viz_error(str(exc))

    if st.session_state["compare_experiment_running"]:
        st.info("Generating experiment charts...")
    elif st.session_state["compare_experiment_error"]:
        st.error(st.session_state["compare_experiment_error"])
    elif st.session_state["compare_experiment_charts"]:
        st.success(
            f"Generated {len(st.session_state['compare_experiment_charts'])} experiment charts."
        )
        for chart_path in st.session_state["compare_experiment_charts"]:
            st.image(chart_path, use_container_width=True)


__all__ = ["render_compare_mode"]
