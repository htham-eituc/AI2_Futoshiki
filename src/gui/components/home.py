"""
Home Screen Component - Main navigation entry point.
"""

import streamlit as st


def render_home_screen() -> None:
    """
    Render the home screen with navigation buttons.
    
    Sets st.session_state["screen"] to navigate to other screens.
    """
                                        
    st.markdown(
        """
        <div style="
            text-align: center; 
            padding: 48px 24px 32px 24px;
            max-width: 720px;
            margin: 0 auto;
        ">
            <h1 style="
                color: var(--text-primary); 
                margin-bottom: 16px; 
                font-size: 32px;
                font-weight: 600; 
                letter-spacing: -0.02em;
                line-height: 1.2;
            ">
                Futoshiki Algorithm Visualizer
            </h1>
            <p style="
                color: var(--text-secondary); 
                font-size: 17px; 
                line-height: 1.7;
                margin: 0;
            ">
                Explore and compare AI algorithms for solving Futoshiki puzzles.
                Watch step-by-step execution or analyze performance across multiple solvers.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
                                           
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        st.markdown(
            '<p class="section-header" style="text-align: center; margin-bottom: 24px;">Choose a Mode</p>',
            unsafe_allow_html=True,
        )
        
                                     
        card_col1, card_col2 = st.columns(2)
        
        with card_col1:
                                                 
            st.markdown(
                """
                <div class="edu-card" style="height: 100%; min-height: 180px;">
                    <h3 style="
                        margin: 0 0 12px 0; 
                        color: var(--text-primary); 
                        font-weight: 600;
                        font-size: 18px;
                    ">Step-by-Step Visualization</h3>
                    <p style="
                        margin: 0; 
                        color: var(--text-secondary); 
                        line-height: 1.6;
                        font-size: 14px;
                    ">
                        Watch algorithms solve puzzles one step at a time.
                        See how decisions are made and backtracks occur.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)
            
            if st.button(
                "Start Step-by-Step Mode",
                key="btn_step_viz",
                use_container_width=True,
                type="primary",
            ):
                st.session_state["screen"] = "step_visualization"
                st.rerun()
        
        with card_col2:
                                   
            st.markdown(
                """
                <div class="edu-card" style="height: 100%; min-height: 180px;">
                    <h3 style="
                        margin: 0 0 12px 0; 
                        color: var(--text-primary); 
                        font-weight: 600;
                        font-size: 18px;
                    ">Compare Algorithms</h3>
                    <p style="
                        margin: 0; 
                        color: var(--text-secondary); 
                        line-height: 1.6;
                        font-size: 14px;
                    ">
                        Run multiple algorithms on all test cases.
                        View performance charts and statistics.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)
            
            if st.button(
                "Start Compare Mode",
                key="btn_compare",
                use_container_width=True,
                type="secondary",
            ):
                st.session_state["screen"] = "compare_mode"
                st.rerun()
    
            
    st.markdown("<div style='height: 48px'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="
            text-align: center; 
            color: var(--text-muted); 
            font-size: 13px;
            padding: 24px 0;
            border-top: 1px solid var(--border-light);
        ">
            Built with Streamlit · AI2 Course Project
        </div>
        """,
        unsafe_allow_html=True,
    )


__all__ = ["render_home_screen"]
