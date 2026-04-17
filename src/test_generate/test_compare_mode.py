"""Unit tests for compare-mode experiment visualization state transitions."""

import os
import sys
import inspect
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from gui.components import compare_mode              


class TestCompareModeExperimentState(unittest.TestCase):
    def test_compare_mode_has_single_csv_trigger_and_no_legacy_controls(self) -> None:
        source = inspect.getsource(compare_mode.render_compare_mode)
        self.assertIn("Visualize experiment.csv", source)
        self.assertIn("st.multiselect", source)
        self.assertIn("selected_algorithms=selected_algorithms", source)
        self.assertIn("stream_experiment_visualizations", source)
        self.assertIn("Please select at least one algorithm to visualize.", source)
        self.assertNotIn("Run Comparison", source)
        self.assertNotIn("Select Algorithms to Compare", source)

    def test_init_session_state_adds_algorithm_selection_defaults(self) -> None:
        fake_st = MagicMock()
        fake_st.session_state = {}
        with patch.object(compare_mode, "st", fake_st):
            compare_mode._init_session_state()

        self.assertEqual(fake_st.session_state["compare_experiment_available_algorithms"], [])
        self.assertEqual(fake_st.session_state["compare_experiment_selected_algorithms"], [])
        self.assertIsNone(fake_st.session_state["compare_experiment_options_error"])

    def test_idle_to_running_transition(self) -> None:
        fake_st = MagicMock()
        fake_st.session_state = {
            "compare_experiment_available_algorithms": ["A*", "Backtracking"],
            "compare_experiment_selected_algorithms": ["A*"],
            "compare_experiment_options_error": None,
            "compare_experiment_running": False,
            "compare_experiment_error": "old",
            "compare_experiment_charts": ["old.png"],
            "compare_experiment_step": 7,
            "compare_experiment_total": 9,
        }
        with patch.object(compare_mode, "st", fake_st):
            compare_mode._set_experiment_viz_running()

        self.assertTrue(fake_st.session_state["compare_experiment_running"])
        self.assertIsNone(fake_st.session_state["compare_experiment_error"])
        self.assertEqual(fake_st.session_state["compare_experiment_charts"], [])
        self.assertEqual(fake_st.session_state["compare_experiment_step"], 0)
        self.assertEqual(fake_st.session_state["compare_experiment_total"], 0)
        self.assertEqual(
            fake_st.session_state["compare_experiment_selected_algorithms"],
            ["A*"],
        )

    def test_progress_event_records_incremental_state(self) -> None:
        fake_st = MagicMock()
        fake_st.session_state = {
            "compare_experiment_running": True,
            "compare_experiment_error": None,
            "compare_experiment_charts": [],
            "compare_experiment_step": 0,
            "compare_experiment_total": 0,
        }
        progress = compare_mode.ExperimentVisualizationProgress(
            step=1,
            total=6,
            chart_name="summary_dashboard",
            chart_path=Path("charts/summary_dashboard.png"),
        )
        with patch.object(compare_mode, "st", fake_st):
            compare_mode._record_experiment_viz_progress(progress)

        self.assertEqual(
            fake_st.session_state["compare_experiment_charts"],
            ["charts/summary_dashboard.png"],
        )
        self.assertEqual(fake_st.session_state["compare_experiment_step"], 1)
        self.assertEqual(fake_st.session_state["compare_experiment_total"], 6)

    def test_running_to_success_transition(self) -> None:
        fake_st = MagicMock()
        fake_st.session_state = {
            "compare_experiment_running": True,
            "compare_experiment_error": "boom",
            "compare_experiment_charts": ["charts/summary_dashboard.png"],
            "compare_experiment_step": 1,
            "compare_experiment_total": 6,
        }
        with patch.object(compare_mode, "st", fake_st):
            compare_mode._set_experiment_viz_success()

        self.assertFalse(fake_st.session_state["compare_experiment_running"])
        self.assertIsNone(fake_st.session_state["compare_experiment_error"])
        self.assertEqual(
            fake_st.session_state["compare_experiment_charts"],
            ["charts/summary_dashboard.png"],
        )
        self.assertEqual(fake_st.session_state["compare_experiment_step"], 1)
        self.assertEqual(fake_st.session_state["compare_experiment_total"], 6)

    def test_running_to_error_transition_keeps_partial_charts(self) -> None:
        fake_st = MagicMock()
        fake_st.session_state = {
            "compare_experiment_running": True,
            "compare_experiment_error": None,
            "compare_experiment_charts": ["chart.png"],
            "compare_experiment_step": 2,
            "compare_experiment_total": 6,
        }
        with patch.object(compare_mode, "st", fake_st):
            compare_mode._set_experiment_viz_error("bad csv")

        self.assertFalse(fake_st.session_state["compare_experiment_running"])
        self.assertEqual(fake_st.session_state["compare_experiment_error"], "bad csv")
        self.assertEqual(fake_st.session_state["compare_experiment_charts"], ["chart.png"])
        self.assertEqual(fake_st.session_state["compare_experiment_step"], 2)
        self.assertEqual(fake_st.session_state["compare_experiment_total"], 6)


if __name__ == "__main__":
    unittest.main()
