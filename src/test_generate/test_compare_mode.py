"""Unit tests for compare-mode experiment visualization state transitions."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from gui.components import compare_mode  # noqa: E402


class TestCompareModeExperimentState(unittest.TestCase):
    def test_idle_to_running_transition(self) -> None:
        fake_st = MagicMock()
        fake_st.session_state = {
            "compare_experiment_running": False,
            "compare_experiment_error": "old",
            "compare_experiment_charts": ["old.png"],
        }
        with patch.object(compare_mode, "st", fake_st):
            compare_mode._set_experiment_viz_running()

        self.assertTrue(fake_st.session_state["compare_experiment_running"])
        self.assertIsNone(fake_st.session_state["compare_experiment_error"])
        self.assertEqual(fake_st.session_state["compare_experiment_charts"], ["old.png"])

    def test_running_to_success_transition(self) -> None:
        fake_st = MagicMock()
        fake_st.session_state = {
            "compare_experiment_running": True,
            "compare_experiment_error": "boom",
            "compare_experiment_charts": [],
        }
        with patch.object(compare_mode, "st", fake_st):
            compare_mode._set_experiment_viz_success([])

        self.assertFalse(fake_st.session_state["compare_experiment_running"])
        self.assertIsNone(fake_st.session_state["compare_experiment_error"])
        self.assertEqual(fake_st.session_state["compare_experiment_charts"], [])

    def test_running_to_error_transition(self) -> None:
        fake_st = MagicMock()
        fake_st.session_state = {
            "compare_experiment_running": True,
            "compare_experiment_error": None,
            "compare_experiment_charts": ["chart.png"],
        }
        with patch.object(compare_mode, "st", fake_st):
            compare_mode._set_experiment_viz_error("bad csv")

        self.assertFalse(fake_st.session_state["compare_experiment_running"])
        self.assertEqual(fake_st.session_state["compare_experiment_error"], "bad csv")
        self.assertEqual(fake_st.session_state["compare_experiment_charts"], [])


if __name__ == "__main__":
    unittest.main()
