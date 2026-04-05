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
            if st.button("Return to Home"):
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
        page_icon=None,
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    
    # Custom CSS - Human-style theme
    st.markdown(
        """
        <style>
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* ===== Human-Style Theme ===== */
        
        /* Soft color palette */
        :root {
            --bg-primary: #fafafa;
            --bg-surface: #ffffff;
            --text-primary: #2d3748;
            --text-secondary: #718096;
            --accent-primary: #4a5568;
            --accent-secondary: #718096;
            --success: #48bb78;
            --error: #f56565;
            --border-soft: #e2e8f0;
            --shadow-soft: rgba(0, 0, 0, 0.05);
        }
        
        /* Typography hierarchy */
        .primary-header {
            font-size: 28px;
            font-weight: 600;
            color: var(--text-primary);
            letter-spacing: -0.02em;
        }
        
        .secondary-header {
            font-size: 20px;
            font-weight: 500;
            color: var(--text-primary);
        }
        
        .body-text {
            font-size: 16px;
            font-weight: 400;
            color: var(--text-secondary);
            line-height: 1.6;
        }
        
        /* Custom button styles */
        .stButton > button {
            border-radius: 6px;
            font-weight: 500;
            border: 1px solid var(--border-soft);
            transition: all 0.2s ease;
        }
        
        .stButton > button:hover {
            border-color: var(--accent-primary);
            box-shadow: 0 2px 4px var(--shadow-soft);
        }
        
        /* Metric styling */
        [data-testid="stMetricValue"] {
            font-size: 24px;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 14px;
            color: var(--text-secondary);
        }
        
        /* Table styling */
        .dataframe {
            font-size: 14px;
        }
        
        /* Card-like containers */
        .soft-card {
            background: var(--bg-surface);
            border: 1px solid var(--border-soft);
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 1px 3px var(--shadow-soft);
        }
        
        /* Subtle badges */
        .subtle-badge {
            display: inline-block;
            background: var(--accent-primary);
            color: white;
            padding: 6px 14px;
            border-radius: 4px;
            font-weight: 500;
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
