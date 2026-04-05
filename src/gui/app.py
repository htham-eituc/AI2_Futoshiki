"""
Futoshiki Algorithm Visualizer - Main Streamlit Application.

This application provides:
1. Step-by-step algorithm visualization
2. Multi-algorithm comparison with analytics

Run with: streamlit run src/gui/app.py
"""

import sys
from pathlib import Path

# Add src directory to path for imports
SRC_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st

# Import screen components
from gui.components.home import render_home_screen
from gui.components.step_visualizer import render_step_visualization
from gui.components.compare_mode import render_compare_mode


def init_session_state() -> None:
    """Initialize global session state."""
    if "screen" not in st.session_state:
        st.session_state["screen"] = "home"


def render_error_boundary(func):
    """Decorator to wrap screen rendering with error handling."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.markdown("---")
            if st.button("🏠 Return to Home"):
                st.session_state["screen"] = "home"
                st.rerun()
            
            # Show error details in expander
            with st.expander("Error Details"):
                st.exception(e)
    return wrapper


def main():
    """Main application entry point."""
    # Page configuration
    st.set_page_config(
        page_title="Futoshiki Algorithm Visualizer",
        page_icon="🧩",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    
    # Custom CSS
    st.markdown(
        """
        <style>
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Custom button styles */
        .stButton > button {
            border-radius: 8px;
            font-weight: 500;
        }
        
        /* Metric styling */
        [data-testid="stMetricValue"] {
            font-size: 24px;
        }
        
        /* Table styling */
        .dataframe {
            font-size: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Initialize session state
    init_session_state()
    
    # Route to appropriate screen
    screen = st.session_state.get("screen", "home")
    
    if screen == "home":
        render_error_boundary(render_home_screen)()
    elif screen == "step_visualization":
        render_error_boundary(render_step_visualization)()
    elif screen == "compare_mode":
        render_error_boundary(render_compare_mode)()
    else:
        st.error(f"Unknown screen: {screen}")
        st.session_state["screen"] = "home"
        st.rerun()


if __name__ == "__main__":
    main()
