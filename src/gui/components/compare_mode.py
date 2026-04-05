"""
Compare Mode Screen - Multi-algorithm comparison with charts.
"""

from typing import Dict, List
import pandas as pd
import streamlit as st

from ..service.visualization_service import VisualizationService, ComparisonResult
from .charts import (
    render_time_chart,
    render_nodes_chart,
    render_success_rate_chart,
    render_constraint_checks_chart,
    render_backtracks_chart,
    render_summary_table,
)


def _init_session_state() -> None:
    """Initialize session state variables for compare mode."""
    defaults = {
        "compare_selected_algos": set(),
        "compare_results": None,
        "compare_running": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _results_to_dataframe(results: List[ComparisonResult]) -> pd.DataFrame:
    """Convert comparison results to pandas DataFrame."""
    data = []
    for r in results:
        data.append({
            "algorithm": r.algorithm,
            "testcase": r.testcase,
            "solved": r.solved,
            "elapsed_seconds": r.elapsed_seconds,
            "nodes_generated": r.nodes_generated,
            "nodes_expanded": r.nodes_expanded,
            "constraint_checks": r.constraint_checks,
            "backtracks": r.backtracks,
            "assignments": r.assignments,
            "error": r.error,
        })
    return pd.DataFrame(data)


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
        '<p style="color: #999; font-size: 14px;">Home > Compare Algorithms</p>',
        unsafe_allow_html=True,
    )
    
    st.markdown("---")
    
    # Algorithm selection section
    st.markdown("### Select Algorithms to Compare")
    
    algorithms = VisualizationService.get_available_algorithms()
    if not algorithms:
        st.error("No algorithms found! Make sure solvers are registered.")
        return
    
    # Algorithm checkboxes
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]
    
    selected_algos = set()
    for i, algo in enumerate(algorithms):
        with cols[i % 3]:
            # Use unique key for each checkbox
            is_selected = st.checkbox(
                algo.upper(),
                value=algo in st.session_state["compare_selected_algos"],
                key=f"algo_checkbox_{algo}",
            )
            if is_selected:
                selected_algos.add(algo)
    
    st.session_state["compare_selected_algos"] = selected_algos
    
    # Select All / Clear All buttons
    col_select, col_clear, col_spacer = st.columns([1, 1, 4])
    
    with col_select:
        if st.button("Select All", use_container_width=True):
            st.session_state["compare_selected_algos"] = set(algorithms)
            st.rerun()
    
    with col_clear:
        if st.button("Clear All", use_container_width=True):
            st.session_state["compare_selected_algos"] = set()
            st.rerun()
    
    st.markdown("---")
    
    # Compare button
    num_selected = len(st.session_state["compare_selected_algos"])
    
    if num_selected < 2:
        st.warning("Please select at least 2 algorithms to compare.")
        compare_disabled = True
    else:
        st.success(f"{num_selected} algorithms selected")
        compare_disabled = False
    
    if st.button(
        "Run Comparison",
        disabled=compare_disabled,
        use_container_width=True,
        type="primary",
    ):
        selected_list = sorted(st.session_state["compare_selected_algos"])
        testcases = VisualizationService.get_available_testcases()
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_runs = len(selected_list) * len(testcases)
        current_run = 0
        
        all_results = []
        
        for testcase in testcases:
            for algo in selected_list:
                current_run += 1
                progress = current_run / total_runs
                progress_bar.progress(progress)
                status_text.text(f"Running {algo} on {testcase['name']}... ({current_run}/{total_runs})")
                
                # Run single comparison
                results = VisualizationService.run_batch_comparison(
                    algorithms=[algo],
                    testcases=[testcase],
                )
                all_results.extend(results)
        
        progress_bar.progress(1.0)
        status_text.text("Comparison complete!")
        
        st.session_state["compare_results"] = all_results
        st.rerun()
    
    # Results section
    if st.session_state["compare_results"]:
        st.markdown("---")
        st.markdown("## 📈 Results")
        
        df = _results_to_dataframe(st.session_state["compare_results"])
        
        # Summary table
        st.markdown("### Summary Statistics")
        render_summary_table(df)
        
        # Charts in tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Execution Time",
            "Nodes Generated",
            "Success Rate",
            "Constraint Checks",
            "Backtracks",
        ])
        
        with tab1:
            render_time_chart(df)
        
        with tab2:
            render_nodes_chart(df, metric="nodes_generated")
        
        with tab3:
            render_success_rate_chart(df)
        
        with tab4:
            render_constraint_checks_chart(df)
        
        with tab5:
            render_backtracks_chart(df)
        
        # Export section
        st.markdown("---")
        st.markdown("### Export Results")
        
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="Download Results as CSV",
            data=csv_data,
            file_name="algorithm_comparison_results.csv",
            mime="text/csv",
            use_container_width=True,
        )
        
        # Raw data expander
        with st.expander("View Raw Data"):
            st.dataframe(df, use_container_width=True)


__all__ = ["render_compare_mode"]
