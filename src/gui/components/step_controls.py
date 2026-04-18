"""
Step Controls Component - Play/Pause/Step buttons for visualization.
"""

from typing import Callable, Optional
import streamlit as st


def render_step_controls(
    on_previous: Optional[Callable] = None,
    on_next: Optional[Callable] = None,
    on_play: Optional[Callable] = None,
    on_pause: Optional[Callable] = None,
    on_reset: Optional[Callable] = None,
    is_playing: bool = False,
    can_go_previous: bool = True,
    can_go_next: bool = True,
    current_step: int = 0,
    total_steps: Optional[int] = None,
) -> dict:
    result = {"action": None}
    
                          
    if total_steps is not None:
        st.markdown(f"**Step {current_step} of {total_steps}**")
    else:
        st.markdown(f"**Step {current_step}**")
    
                     
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("Reset", disabled=current_step == 0, use_container_width=True):
            result["action"] = "reset"
            if on_reset:
                on_reset()
    
    with col2:
        if st.button("Previous", disabled=not can_go_previous, use_container_width=True):
            result["action"] = "previous"
            if on_previous:
                on_previous()
    
    with col3:
        if is_playing:
            if st.button("Pause", use_container_width=True):
                result["action"] = "pause"
                if on_pause:
                    on_pause()
        else:
            if st.button("Play", disabled=not can_go_next, use_container_width=True):
                result["action"] = "play"
                if on_play:
                    on_play()
    
    with col4:
        if st.button("Next", disabled=not can_go_next, use_container_width=True):
            result["action"] = "next"
            if on_next:
                on_next()
    
    with col5:
                                                                      
        pass
    
    return result


def render_speed_slider(
    min_delay: int = 100,
    max_delay: int = 2000,
    default_delay: int = 500,
    key: str = "speed_slider",
) -> int:
    delay = st.slider(
        "Playback Speed (ms delay)",
        min_value=min_delay,
        max_value=max_delay,
        value=default_delay,
        step=100,
        key=key,
        help="Lower = faster playback",
    )
    return delay


__all__ = ["render_step_controls", "render_speed_slider"]
