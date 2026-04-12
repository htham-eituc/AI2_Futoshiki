"""
Compare Mode Screen - Multi-algorithm comparison with charts.
"""

from pathlib import Path
from typing import List, Optional
import streamlit as st

from ..service.visualization_service import (
    VisualizationService,
    ExperimentVisualizationError,
    ExperimentVisualizationProgress,
)


def _init_session_state() -> None:
    """Initialize session state variables for compare mode."""
    defaults = {
        "compare_experiment_available_algorithms": [],
        "compare_experiment_selected_algorithms": [],
        "compare_experiment_options_error": None,
        "compare_experiment_charts": [],
        "compare_experiment_error": None,
        "compare_experiment_running": False,
        "compare_experiment_step": 0,
        "compare_experiment_total": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _set_experiment_viz_running() -> None:
    """Set experiment visualization UI state to running."""
    st.session_state["compare_experiment_running"] = True
    st.session_state["compare_experiment_error"] = None
    st.session_state["compare_experiment_charts"] = []
    st.session_state["compare_experiment_step"] = 0
    st.session_state["compare_experiment_total"] = 0


def _record_experiment_viz_progress(progress: ExperimentVisualizationProgress) -> None:
    """Record one generated chart and update progress counters."""
    chart_path = str(progress.chart_path)
    if chart_path not in st.session_state["compare_experiment_charts"]:
        st.session_state["compare_experiment_charts"].append(chart_path)
    st.session_state["compare_experiment_step"] = progress.step
    st.session_state["compare_experiment_total"] = progress.total


def _set_experiment_viz_success(chart_paths: Optional[List[Path]] = None) -> None:
    """Set experiment visualization UI state to success."""
    st.session_state["compare_experiment_running"] = False
    st.session_state["compare_experiment_error"] = None
    if chart_paths is not None:
        st.session_state["compare_experiment_charts"] = [str(path) for path in chart_paths]
    count = len(st.session_state["compare_experiment_charts"])
    st.session_state["compare_experiment_step"] = count
    st.session_state["compare_experiment_total"] = max(
        st.session_state["compare_experiment_total"],
        count,
    )


def _set_experiment_viz_error(message: str, clear_charts: bool = False) -> None:
    """Set experiment visualization UI state to error."""
    st.session_state["compare_experiment_running"] = False
    st.session_state["compare_experiment_error"] = message
    if clear_charts:
        st.session_state["compare_experiment_charts"] = []
        st.session_state["compare_experiment_step"] = 0
        st.session_state["compare_experiment_total"] = 0


def _render_saved_charts() -> None:
    """Render charts currently stored in session state."""
    for chart_path in st.session_state["compare_experiment_charts"]:
        st.image(chart_path, use_container_width=True)


def _load_algorithm_options() -> List[str]:
    """Load and sync available algorithm options from experiment.csv."""
    try:
        options = VisualizationService.get_experiment_algorithms()
    except ExperimentVisualizationError as exc:
        st.session_state["compare_experiment_options_error"] = str(exc)
        st.session_state["compare_experiment_available_algorithms"] = []
        st.session_state["compare_experiment_selected_algorithms"] = []
        return []

    st.session_state["compare_experiment_options_error"] = None
    st.session_state["compare_experiment_available_algorithms"] = options
    selected = [
        algo
        for algo in st.session_state["compare_experiment_selected_algorithms"]
        if algo in options
    ]
    if not selected:
        selected = options.copy()
    st.session_state["compare_experiment_selected_algorithms"] = selected
    return options


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
    available_algorithms = _load_algorithm_options()

    selected_algorithms: List[str] = []
    if st.session_state["compare_experiment_options_error"]:
        st.error(st.session_state["compare_experiment_options_error"])
    elif available_algorithms:
        selected_algorithms = st.multiselect(
            "Select algorithms from experiment.csv",
            options=available_algorithms,
            default=st.session_state["compare_experiment_selected_algorithms"],
            help="Only selected algorithms will be used for CSV visualization.",
        )
        st.session_state["compare_experiment_selected_algorithms"] = selected_algorithms
        if not selected_algorithms:
            st.warning("Please select at least one algorithm to visualize.")
    else:
        st.warning("No algorithms are available in experiment.csv.")

    live_rendered = False
    visualize_disabled = (
        st.session_state["compare_experiment_running"]
        or not available_algorithms
        or not selected_algorithms
    )
    if st.button(
        "Visualize experiment.csv",
        use_container_width=True,
        disabled=visualize_disabled,
    ):
        _set_experiment_viz_running()
        live_rendered = True
        status_placeholder = st.empty()
        progress_bar = st.progress(0.0)
        charts_placeholder = st.empty()
        status_placeholder.info("Starting experiment visualization...")
        try:
            for progress in VisualizationService.stream_experiment_visualizations(
                selected_algorithms=selected_algorithms
            ):
                _record_experiment_viz_progress(progress)
                ratio = progress.step / progress.total if progress.total else 0.0
                progress_bar.progress(ratio)
                status_placeholder.info(
                    f"Generated {progress.step}/{progress.total}: {progress.chart_name}"
                )
                with charts_placeholder.container():
                    _render_saved_charts()
            _set_experiment_viz_success()
            progress_bar.progress(1.0)
            status_placeholder.success(
                f"Generated {len(st.session_state['compare_experiment_charts'])} experiment charts."
            )
        except ExperimentVisualizationError as exc:
            _set_experiment_viz_error(str(exc))
            status_placeholder.error(str(exc))
            if st.session_state["compare_experiment_charts"]:
                with charts_placeholder.container():
                    _render_saved_charts()

    if not live_rendered and st.session_state["compare_experiment_running"]:
        total = st.session_state["compare_experiment_total"]
        step = st.session_state["compare_experiment_step"]
        if total > 0:
            st.info(f"Generating experiment charts... ({step}/{total})")
        else:
            st.info("Generating experiment charts...")

    if not live_rendered and st.session_state["compare_experiment_error"]:
        st.error(st.session_state["compare_experiment_error"])

    if not live_rendered and st.session_state["compare_experiment_charts"]:
        if st.session_state["compare_experiment_error"]:
            st.warning(
                f"Showing {len(st.session_state['compare_experiment_charts'])} chart(s) generated before failure."
            )
        else:
            st.success(
                f"Generated {len(st.session_state['compare_experiment_charts'])} experiment charts."
            )
        _render_saved_charts()

__all__ = ["render_compare_mode"]
