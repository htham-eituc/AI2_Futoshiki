"""
Step Visualizer Screen - Step-by-step algorithm visualization.
"""

import time
from typing import List, Optional, Set, Tuple
import streamlit as st

from ..services.visualization_service import VisualizationService, StepState
from .grid_display import render_grid
from .step_controls import render_step_controls, render_speed_slider
from .metrics_display import (
    render_metrics,
    render_final_status,
    render_algorithm_badge,
    render_step_message,
)


def _init_session_state() -> None:
    """Initialize session state variables for step visualization."""
    defaults = {
        "viz_algorithm": None,
        "viz_testcase": None,
        "viz_steps": [],
        "viz_current_step": 0,
        "viz_is_playing": False,
        "viz_speed": 500,
        "viz_puzzle_data": None,
        "viz_given_cells": set(),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _get_given_cells(grid: List[List[int]], size: int) -> Set[Tuple[int, int]]:
    """Get set of cells that have initial values."""
    given = set()
    for r in range(size):
        for c in range(size):
            if grid[r][c] != 0:
                given.add((r, c))
    return given


def render_step_visualization() -> None:
    """Render the step-by-step visualization screen."""
    _init_session_state()
    
                             
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("← Back to Home"):
                                       
            for key in list(st.session_state.keys()):
                if key.startswith("viz_"):
                    del st.session_state[key]
            st.session_state["screen"] = "home"
            st.rerun()
    
    with col_title:
        st.markdown("## Step-by-Step Visualization")
    
                
    st.markdown(
        '<p style="color: var(--text-muted); font-size: 14px;">Home > Step-by-Step Visualization</p>',
        unsafe_allow_html=True,
    )
    
    st.markdown("---")
    
                       
    left_col, right_col = st.columns([1, 2])
    
                            
    with left_col:
        st.markdown("### Configuration")
        
                             
        algorithms = VisualizationService.get_available_algorithms()
        if not algorithms:
            st.error("No algorithms found! Make sure solvers are registered.")
            return
        
        selected_algo = st.selectbox(
            "Select Algorithm",
            options=algorithms,
            index=0 if st.session_state["viz_algorithm"] is None else (
                algorithms.index(st.session_state["viz_algorithm"])
                if st.session_state["viz_algorithm"] in algorithms else 0
            ),
            key="algo_select",
        )
        
                            
        testcases = VisualizationService.get_available_testcases()
        if not testcases:
            st.error("No test cases found!")
            return
        
        testcase_names = [tc["name"] for tc in testcases]
        testcase_paths = {tc["name"]: tc["path"] for tc in testcases}
        
        selected_testcase = st.selectbox(
            "Select Test Case",
            options=testcase_names,
            index=0,
            key="testcase_select",
        )
        
        st.markdown("---")
        
                            
        if st.session_state["viz_steps"]:
            if st.button("Load New Puzzle", use_container_width=True):
                st.session_state["viz_steps"] = []
                st.session_state["viz_current_step"] = 0
                st.session_state["viz_is_playing"] = False
                st.rerun()
        else:
            if st.button("Start Visualization", use_container_width=True, type="primary"):
                                     
                if not selected_algo or not selected_testcase:
                    st.error("Please select both an algorithm and a test case.")
                else:
                    with st.spinner("Loading puzzle and generating steps..."):
                        try:
                                         
                            filepath = testcase_paths[selected_testcase]
                            puzzle_data = VisualizationService.load_puzzle(filepath)
                            
                                               
                            given_cells = _get_given_cells(puzzle_data.grid, puzzle_data.size)
                            
                                                
                            steps = list(VisualizationService.run_algorithm_steps(
                                selected_algo, puzzle_data
                            ))
                            
                                                    
                            st.session_state["viz_algorithm"] = selected_algo
                            st.session_state["viz_testcase"] = selected_testcase
                            st.session_state["viz_puzzle_data"] = puzzle_data
                            st.session_state["viz_steps"] = steps
                            st.session_state["viz_current_step"] = 0
                            st.session_state["viz_given_cells"] = given_cells
                            st.session_state["viz_is_playing"] = False
                            
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error loading puzzle: {e}")
        
                                                           
        if st.session_state["viz_steps"]:
            st.markdown("---")
            st.markdown("### Playback Speed")
            st.session_state["viz_speed"] = render_speed_slider(
                min_delay=100,
                max_delay=2000,
                default_delay=st.session_state["viz_speed"],
                key="speed_control",
            )
    
                                  
    with right_col:
        if not st.session_state["viz_steps"]:
                                                        
            st.markdown(
                """
                <div class="empty-state">
                    <h3>Ready to Visualize</h3>
                    <p style="margin: 0; font-size: 15px;">
                        Select an algorithm and test case from the left panel, then click "Start Visualization"
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
                              
            steps = st.session_state["viz_steps"]
            current_idx = st.session_state["viz_current_step"]
            current_step: StepState = steps[current_idx]
            puzzle_data = st.session_state["viz_puzzle_data"]
            
                             
            render_algorithm_badge(st.session_state["viz_algorithm"])
            
                           
            can_previous = current_idx > 0
            can_next = current_idx < len(steps) - 1
            
            controls = render_step_controls(
                is_playing=st.session_state["viz_is_playing"],
                can_go_previous=can_previous,
                can_go_next=can_next,
                current_step=current_idx,
                total_steps=len(steps) - 1,
            )
            
                                    
            if controls["action"] == "reset":
                st.session_state["viz_current_step"] = 0
                st.session_state["viz_is_playing"] = False
                st.rerun()
            elif controls["action"] == "previous":
                if can_previous:
                    st.session_state["viz_current_step"] -= 1
                    st.rerun()
            elif controls["action"] == "next":
                if can_next:
                    st.session_state["viz_current_step"] += 1
                    st.rerun()
            elif controls["action"] == "play":
                st.session_state["viz_is_playing"] = True
                st.rerun()
            elif controls["action"] == "pause":
                st.session_state["viz_is_playing"] = False
                st.rerun()
            
                          
            render_step_message(current_step.message)
            
                          
            st.markdown("### Puzzle Grid")
            render_grid(
                grid=current_step.grid,
                size=puzzle_data.size,
                h_constraints=puzzle_data.h_constraints,
                v_constraints=puzzle_data.v_constraints,
                active_cell=current_step.active_cell,
                changed_cell=current_step.changed_cell,
                conflict_cells=current_step.conflict_cells,
                given_cells=st.session_state["viz_given_cells"],
            )
            
                     
            render_metrics(
                metrics=current_step.metrics,
                is_live=not current_step.is_complete,
            )
            
                               
            if current_step.is_complete:
                render_final_status(
                    is_solved=current_step.is_solved,
                    message=current_step.message,
                )
            
                             
            if st.session_state["viz_is_playing"] and can_next:
                time.sleep(st.session_state["viz_speed"] / 1000.0)
                st.session_state["viz_current_step"] += 1
                st.rerun()
            elif st.session_state["viz_is_playing"] and not can_next:
                st.session_state["viz_is_playing"] = False


__all__ = ["render_step_visualization"]
