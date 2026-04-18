"""
Futoshiki Algorithm Visualizer - Main Streamlit Application.

This application provides:
1. Step-by-step algorithm visualization
2. Multi-algorithm comparison with analytics

Run with: streamlit run src/gui/app.py
"""

import sys
from pathlib import Path

                                       
SRC_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st

                          
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
            
                                            
            with st.expander("Error Details"):
                st.exception(e)
    return wrapper


def main():
    """Main application entry point."""
                        
    st.set_page_config(
        page_title="Futoshiki Algorithm Visualizer",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    
                                                           
    st.markdown(
        """
        <style>
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* ===== Education-Friendly Theme ===== */
        /* Warm, calming colors optimized for learning environments */
        
        :root {
            /* Warm neutral backgrounds - easy on the eyes for long sessions */
            --bg-primary: #f8f9fa;
            --bg-surface: #ffffff;
            --bg-elevated: #ffffff;
            --bg-muted: #f3f4f6;
            --bg-hover: #eef0f2;
            
            /* Text colors with good contrast for readability (WCAG AA compliant) */
            --text-primary: #1f2937;
            --text-secondary: #4b5563;
            --text-muted: #6b7280;
            --text-inverse: #ffffff;
            
            /* Friendly, approachable accent - soft blue/teal for education */
            --accent-primary: #0ea5e9;
            --accent-hover: #0284c7;
            --accent-soft: #e0f2fe;
            --accent-border: #bae6fd;
            
            /* Semantic colors - friendly and clear (inspired by Refactoring UI) */
            --success: #10b981;
            --success-bg: #d1fae5;
            --success-border: #6ee7b7;
            --warning: #f59e0b;
            --warning-bg: #fef3c7;
            --warning-border: #fcd34d;
            --info: #3b82f6;
            --info-bg: #dbeafe;
            --info-border: #93c5fd;
            --error: #ef4444;
            --error-bg: #fee2e2;
            --error-border: #fca5a5;
            
            /* Borders and shadows */
            --border-light: #e8e6e3;
            --border-medium: #d5d2cd;
            --shadow-sm: 0 1px 2px rgba(44, 62, 80, 0.06);
            --shadow-md: 0 2px 8px rgba(44, 62, 80, 0.08);
            --shadow-lg: 0 4px 16px rgba(44, 62, 80, 0.1);
            
            /* Grid highlight colors - soft and friendly */
            --grid-active: #fef3c7;
            --grid-changed: #d1fae5;
            --grid-conflict: #fee2e2;
            --grid-default: #ffffff;
            --grid-given: #dbeafe;
            --grid-border: #d1d5db;
            
            /* Spacing scale */
            --space-xs: 4px;
            --space-sm: 8px;
            --space-md: 16px;
            --space-lg: 24px;
            --space-xl: 32px;
            --space-2xl: 48px;
            
            /* Border radius */
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 14px;
            --radius-full: 9999px;
        }

        /* Global app styling */
        [data-testid="stAppViewContainer"] {
            background: var(--bg-primary);
            color: var(--text-primary);
        }

        [data-testid="stHeader"] {
            background: transparent;
        }
        
        /* Smooth font rendering */
        * {
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        
        /* Typography - friendly and readable */
        h1, h2, h3, h4, h5, h6 {
            color: var(--text-primary);
            font-weight: 600;
            letter-spacing: -0.01em;
        }
        
        p {
            color: var(--text-secondary);
            line-height: 1.7;
        }
        
        /* Custom button styles - friendly and accessible (Refactoring UI principles) */
        .stButton > button {
            background: var(--bg-surface);
            color: var(--text-primary);
            border-radius: var(--radius-md);
            font-weight: 500;
            font-size: 15px;
            border: 1.5px solid var(--border-medium);
            padding: 0.65rem 1.5rem;
            transition: all 0.15s ease-out;
            box-shadow: var(--shadow-sm);
            cursor: pointer;
        }

        .stButton > button[kind="primary"] {
            background: var(--accent-primary);
            color: var(--text-inverse);
            border-color: var(--accent-primary);
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border-color: var(--accent-border);
        }
        
        .stButton > button[kind="primary"]:hover {
            background: var(--accent-hover);
            border-color: var(--accent-hover);
            box-shadow: 0 10px 15px -3px rgba(14, 165, 233, 0.3), 0 4px 6px -2px rgba(14, 165, 233, 0.2);
        }
        
        .stButton > button:active {
            transform: translateY(0);
        }
        
        /* Metric cards - clean and professional */
        [data-testid="stMetricValue"] {
            font-size: 26px;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 13px;
            font-weight: 500;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        
        /* Select boxes - modern and clean */
        [data-testid="stSelectbox"] > div > div {
            border-radius: var(--radius-md);
            border: 1.5px solid var(--border-medium);
            transition: all 0.15s ease;
        }
        
        [data-testid="stSelectbox"] > div > div:hover {
            border-color: var(--accent-primary);
        }
        
        [data-testid="stSelectbox"] > div > div:focus-within {
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px var(--accent-soft);
        }
        
        /* Checkboxes */
        [data-testid="stCheckbox"] {
            padding: var(--space-xs) 0;
        }
        
        /* Table styling - clean */
        .dataframe {
            font-size: 14px;
            border-radius: var(--radius-md);
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--border-light);
            border-radius: var(--radius-md);
            overflow: hidden;
        }

        /* Notification styling - clear and friendly (UX best practices) */
        [data-testid="stAlert"] {
            border-radius: var(--radius-md);
            border-width: 1px;
            border-style: solid;
            border-left-width: 4px;
            font-size: 15px;
        }

        div[data-baseweb="notification"] {
            border-radius: var(--radius-md);
            border-left-width: 4px;
        }

        /* Success messages - green and optimistic */
        [data-testid="stAlert"][data-baseweb-toast-kind="positive"],
        div[data-baseweb="notification"][kind="success"] {
            background: var(--success-bg);
            border-color: var(--success-border);
            border-left-color: var(--success);
            color: #065f46;
        }

        /* Warning messages - amber, not alarming */
        [data-testid="stAlert"][data-baseweb-toast-kind="warning"],
        div[data-baseweb="notification"][kind="warning"] {
            background: var(--warning-bg);
            border-color: var(--warning-border);
            border-left-color: var(--warning);
            color: #92400e;
        }

        /* Info messages - calm blue */
        [data-testid="stAlert"][data-baseweb-toast-kind="info"],
        div[data-baseweb="notification"][kind="info"] {
            background: var(--info-bg);
            border-color: var(--info-border);
            border-left-color: var(--info);
            color: #1e40af;
        }

        /* Error messages - clear but not scary */
        [data-testid="stAlert"][data-baseweb-toast-kind="negative"],
        div[data-baseweb="notification"][kind="error"] {
            background: var(--error-bg);
            border-color: var(--error-border);
            border-left-color: var(--error);
            color: #991b1b;
        }
        
        /* Expander styling */
        [data-testid="stExpander"] {
            border: 1px solid var(--border-light);
            border-radius: var(--radius-md);
            background: var(--bg-surface);
        }
        
        /* Progress bar */
        [data-testid="stProgress"] > div > div {
            background: var(--accent-soft);
            border-radius: var(--radius-full);
        }
        
        [data-testid="stProgress"] > div > div > div {
            background: var(--accent-primary);
            border-radius: var(--radius-full);
        }
        
        /* Tabs - clean and minimal */
        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: var(--space-xs);
            border-bottom: 1px solid var(--border-light);
        }
        
        [data-testid="stTabs"] [data-baseweb="tab"] {
            border-radius: var(--radius-sm) var(--radius-sm) 0 0;
            padding: var(--space-sm) var(--space-md);
            font-weight: 500;
        }
        
        /* Slider styling */
        [data-testid="stSlider"] > div > div > div {
            background: var(--accent-soft);
        }
        
        [data-testid="stSlider"] > div > div > div > div {
            background: var(--accent-primary);
        }
        
        /* Divider */
        hr {
            border: none;
            border-top: 1px solid var(--border-light);
            margin: var(--space-lg) 0;
        }
        
        /* Card components with modern elevation (Material Design inspired) */
        .edu-card {
            background: var(--bg-surface);
            border: 1px solid var(--border-light);
            border-radius: var(--radius-lg);
            padding: var(--space-lg);
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        
        .edu-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--accent-primary), var(--info));
            opacity: 0;
            transition: opacity 0.2s ease;
        }
        
        .edu-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            border-color: var(--accent-border);
        }
        
        .edu-card:hover::before {
            opacity: 1;
        }
        
        .edu-card-header {
            font-size: 18px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: var(--space-sm);
        }
        
        .edu-card-body {
            font-size: 15px;
            color: var(--text-secondary);
            line-height: 1.6;
        }
        
        /* Badge component */
        .edu-badge {
            display: inline-flex;
            align-items: center;
            background: var(--accent-primary);
            color: var(--text-inverse);
            padding: 6px 14px;
            border-radius: var(--radius-sm);
            font-weight: 500;
            font-size: 13px;
            letter-spacing: 0.02em;
        }
        
        /* Section headers */
        .section-header {
            font-size: 15px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: var(--space-md);
        }
        
        /* Placeholder/empty state */
        .empty-state {
            text-align: center;
            padding: var(--space-2xl) var(--space-lg);
            background: var(--bg-muted);
            border: 1px dashed var(--border-medium);
            border-radius: var(--radius-lg);
            color: var(--text-muted);
        }
        
        .empty-state h3 {
            color: var(--text-secondary);
            font-weight: 500;
            margin-bottom: var(--space-sm);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
                              
    init_session_state()
    
                                 
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
