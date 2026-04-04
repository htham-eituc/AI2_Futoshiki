"""
Home Screen Component - Main navigation entry point.
"""

import streamlit as st


def render_home_screen() -> None:
    """
    Render the home screen with navigation buttons.
    
    Sets st.session_state["screen"] to navigate to other screens.
    """
    # Header
    st.markdown(
        """
        <div style="text-align: center; padding: 40px 0;">
            <h1 style="color: #1e88e5; margin-bottom: 10px;">
                🧩 Futoshiki Algorithm Visualizer
            </h1>
            <p style="color: #666; font-size: 18px; max-width: 600px; margin: 0 auto;">
                Explore and compare AI algorithms for solving Futoshiki puzzles.
                Watch step-by-step execution or analyze performance across multiple solvers.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("---")
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Choose a Mode")
        st.markdown("")
        
        # Button A - Step-by-Step Visualization
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
                color: white;
            ">
                <h3 style="margin: 0;">🔍 Step-by-Step Visualization</h3>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">
                    Watch algorithms solve puzzles one step at a time.
                    See how decisions are made and backtracks occur.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        if st.button(
            "Start Step-by-Step Mode",
            key="btn_step_viz",
            use_container_width=True,
            type="primary",
        ):
            st.session_state["screen"] = "step_visualization"
            st.rerun()
        
        st.markdown("")
        st.markdown("")
        
        # Button B - Compare Mode
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
                color: white;
            ">
                <h3 style="margin: 0;">📊 Compare Algorithms</h3>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">
                    Run multiple algorithms on all test cases.
                    View performance charts and statistics.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        if st.button(
            "Start Compare Mode",
            key="btn_compare",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state["screen"] = "compare_mode"
            st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #999; font-size: 14px;">
            <p>Built with Streamlit • AI2 Course Project</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


__all__ = ["render_home_screen"]
