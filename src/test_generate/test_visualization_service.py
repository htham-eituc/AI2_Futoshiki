"""Unit tests for GUI experiment-visualization service flow."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from gui.service.visualization_service import (  # noqa: E402
    ExperimentVisualizationError,
    VisualizationService,
)


class TestVisualizationService(unittest.TestCase):
    def test_get_experiment_algorithms_returns_sorted_unique(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            input_csv = temp_dir / "experiment.csv"
            input_csv.write_text("dummy\n", encoding="utf-8")

            df = pd.DataFrame(
                [
                    {"algorithm": "Backtracking", "solution_found": True},
                    {"algorithm": "A*", "solution_found": True},
                    {"algorithm": "Backtracking", "solution_found": False},
                ]
            )
            df_solved = pd.DataFrame(
                [
                    {"algorithm": "Backtracking", "solution_found": True},
                    {"algorithm": "A*", "solution_found": True},
                ]
            )
            fake_module = SimpleNamespace(load_data=lambda _path: (df, df_solved))

            with patch.object(
                VisualizationService,
                "_load_experiment_visualizer_module",
                return_value=fake_module,
            ):
                algorithms = VisualizationService.get_experiment_algorithms(csv_path=input_csv)

            self.assertEqual(algorithms, ["A*", "Backtracking"])

    def test_generate_experiment_visualizations_success_returns_ordered_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            input_csv = temp_dir / "experiment.csv"
            output_dir = temp_dir / "charts"
            input_csv.write_text("dummy\n", encoding="utf-8")

            df = pd.DataFrame([{"algorithm": "A*", "solution_found": True, "time_ms": 1.0}])
            df_solved = pd.DataFrame([{"algorithm": "A*", "solution_found": True, "time_ms": 1.0}])

            def _load_data(_path: Path):
                return df, df_solved

            def _plot_factory(filename: str):
                def _plot(_df: pd.DataFrame, out_dir: Path):
                    out_dir.mkdir(parents=True, exist_ok=True)
                    (out_dir / filename).write_bytes(b"png")

                return _plot

            fake_module = SimpleNamespace(
                load_data=_load_data,
                plot_summary_dashboard=_plot_factory("summary_dashboard.png"),
                plot_time_comparison=_plot_factory("time_comparison.png"),
                plot_nodes_comparison=_plot_factory("nodes_comparison.png"),
                plot_difficulty_analysis=_plot_factory("difficulty_analysis.png"),
                plot_size_analysis=_plot_factory("size_analysis.png"),
                plot_detailed_metrics=_plot_factory("detailed_metrics.png"),
            )

            with patch.object(
                VisualizationService,
                "_load_experiment_visualizer_module",
                return_value=fake_module,
            ):
                chart_paths = VisualizationService.generate_experiment_visualizations(
                    csv_path=input_csv,
                    output_dir=output_dir,
                )

            self.assertGreater(len(chart_paths), 0)
            self.assertEqual(
                [path.name for path in chart_paths],
                VisualizationService.EXPERIMENT_CHART_FILENAMES,
            )
            self.assertTrue(all(path.exists() for path in chart_paths))

    def test_stream_experiment_visualizations_emits_stepwise_ordered_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            input_csv = temp_dir / "experiment.csv"
            output_dir = temp_dir / "charts"
            input_csv.write_text("dummy\n", encoding="utf-8")

            df = pd.DataFrame([{"algorithm": "A*", "solution_found": True, "time_ms": 1.0}])
            df_solved = pd.DataFrame([{"algorithm": "A*", "solution_found": True, "time_ms": 1.0}])

            def _load_data(_path: Path):
                return df, df_solved

            def _plot_factory(filename: str):
                def _plot(_df: pd.DataFrame, out_dir: Path):
                    out_dir.mkdir(parents=True, exist_ok=True)
                    (out_dir / filename).write_bytes(b"png")

                return _plot

            fake_module = SimpleNamespace(
                load_data=_load_data,
                plot_summary_dashboard=_plot_factory("summary_dashboard.png"),
                plot_time_comparison=_plot_factory("time_comparison.png"),
                plot_nodes_comparison=_plot_factory("nodes_comparison.png"),
                plot_difficulty_analysis=_plot_factory("difficulty_analysis.png"),
                plot_size_analysis=_plot_factory("size_analysis.png"),
                plot_detailed_metrics=_plot_factory("detailed_metrics.png"),
            )

            with patch.object(
                VisualizationService,
                "_load_experiment_visualizer_module",
                return_value=fake_module,
            ):
                events = list(
                    VisualizationService.stream_experiment_visualizations(
                        csv_path=input_csv,
                        output_dir=output_dir,
                    )
                )

            self.assertEqual(len(events), len(VisualizationService.EXPERIMENT_CHART_FILENAMES))
            self.assertEqual(
                [event.step for event in events],
                list(range(1, len(events) + 1)),
            )
            self.assertEqual(
                [event.chart_path.name for event in events],
                VisualizationService.EXPERIMENT_CHART_FILENAMES,
            )
            self.assertTrue(all(event.chart_path.exists() for event in events))

    def test_stream_experiment_visualizations_applies_algorithm_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            input_csv = temp_dir / "experiment.csv"
            output_dir = temp_dir / "charts"
            input_csv.write_text("dummy\n", encoding="utf-8")

            df = pd.DataFrame(
                [
                    {"algorithm": "A*", "solution_found": True, "time_ms": 1.0},
                    {"algorithm": "Backtracking", "solution_found": True, "time_ms": 2.0},
                ]
            )
            df_solved = df.copy()

            def _load_data(_path: Path):
                return df, df_solved

            def _plot_factory(filename: str):
                def _plot(filtered_df: pd.DataFrame, out_dir: Path):
                    self.assertEqual(
                        sorted(filtered_df["algorithm"].unique().tolist()),
                        ["A*"],
                    )
                    out_dir.mkdir(parents=True, exist_ok=True)
                    (out_dir / filename).write_bytes(b"png")

                return _plot

            fake_module = SimpleNamespace(
                load_data=_load_data,
                plot_summary_dashboard=_plot_factory("summary_dashboard.png"),
                plot_time_comparison=_plot_factory("time_comparison.png"),
                plot_nodes_comparison=_plot_factory("nodes_comparison.png"),
                plot_difficulty_analysis=_plot_factory("difficulty_analysis.png"),
                plot_size_analysis=_plot_factory("size_analysis.png"),
                plot_detailed_metrics=_plot_factory("detailed_metrics.png"),
            )

            with patch.object(
                VisualizationService,
                "_load_experiment_visualizer_module",
                return_value=fake_module,
            ):
                events = list(
                    VisualizationService.stream_experiment_visualizations(
                        csv_path=input_csv,
                        output_dir=output_dir,
                        selected_algorithms=["A*"],
                    )
                )

            self.assertEqual(len(events), 6)

    def test_stream_experiment_visualizations_failure_keeps_partial_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            input_csv = temp_dir / "experiment.csv"
            output_dir = temp_dir / "charts"
            input_csv.write_text("dummy\n", encoding="utf-8")

            df = pd.DataFrame([{"algorithm": "A*", "solution_found": True, "time_ms": 1.0}])
            df_solved = pd.DataFrame([{"algorithm": "A*", "solution_found": True, "time_ms": 1.0}])

            def _load_data(_path: Path):
                return df, df_solved

            def _plot_factory(filename: str):
                def _plot(_df: pd.DataFrame, out_dir: Path):
                    out_dir.mkdir(parents=True, exist_ok=True)
                    (out_dir / filename).write_bytes(b"png")

                return _plot

            def _boom(_df: pd.DataFrame, _out_dir: Path):
                raise RuntimeError("plot crash")

            fake_module = SimpleNamespace(
                load_data=_load_data,
                plot_summary_dashboard=_plot_factory("summary_dashboard.png"),
                plot_time_comparison=_plot_factory("time_comparison.png"),
                plot_nodes_comparison=_boom,
                plot_difficulty_analysis=_plot_factory("difficulty_analysis.png"),
                plot_size_analysis=_plot_factory("size_analysis.png"),
                plot_detailed_metrics=_plot_factory("detailed_metrics.png"),
            )

            emitted = []
            with patch.object(
                VisualizationService,
                "_load_experiment_visualizer_module",
                return_value=fake_module,
            ):
                with self.assertRaises(ExperimentVisualizationError) as exc_info:
                    for progress in VisualizationService.stream_experiment_visualizations(
                        csv_path=input_csv,
                        output_dir=output_dir,
                    ):
                        emitted.append(progress)

            self.assertEqual(len(emitted), 2)
            self.assertIn("step 3/6", str(exc_info.exception))

    def test_stream_experiment_visualizations_empty_selection_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            input_csv = temp_dir / "experiment.csv"
            input_csv.write_text("dummy\n", encoding="utf-8")

            df = pd.DataFrame([{"algorithm": "A*", "solution_found": True}])
            df_solved = pd.DataFrame([{"algorithm": "A*", "solution_found": True}])
            fake_module = SimpleNamespace(
                load_data=lambda _path: (df, df_solved),
                plot_summary_dashboard=lambda _df, _out_dir: None,
                plot_time_comparison=lambda _df, _out_dir: None,
                plot_nodes_comparison=lambda _df, _out_dir: None,
                plot_difficulty_analysis=lambda _df, _out_dir: None,
                plot_size_analysis=lambda _df, _out_dir: None,
                plot_detailed_metrics=lambda _df, _out_dir: None,
            )

            with patch.object(
                VisualizationService,
                "_load_experiment_visualizer_module",
                return_value=fake_module,
            ):
                with self.assertRaises(ExperimentVisualizationError) as exc_info:
                    list(
                        VisualizationService.stream_experiment_visualizations(
                            csv_path=input_csv,
                            selected_algorithms=[],
                        )
                    )
            self.assertIn("Please select at least one algorithm", str(exc_info.exception))

    def test_stream_experiment_visualizations_unknown_algorithm_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            input_csv = temp_dir / "experiment.csv"
            input_csv.write_text("dummy\n", encoding="utf-8")

            df = pd.DataFrame([{"algorithm": "A*", "solution_found": True}])
            df_solved = pd.DataFrame([{"algorithm": "A*", "solution_found": True}])
            fake_module = SimpleNamespace(
                load_data=lambda _path: (df, df_solved),
                plot_summary_dashboard=lambda _df, _out_dir: None,
                plot_time_comparison=lambda _df, _out_dir: None,
                plot_nodes_comparison=lambda _df, _out_dir: None,
                plot_difficulty_analysis=lambda _df, _out_dir: None,
                plot_size_analysis=lambda _df, _out_dir: None,
                plot_detailed_metrics=lambda _df, _out_dir: None,
            )

            with patch.object(
                VisualizationService,
                "_load_experiment_visualizer_module",
                return_value=fake_module,
            ):
                with self.assertRaises(ExperimentVisualizationError) as exc_info:
                    list(
                        VisualizationService.stream_experiment_visualizations(
                            csv_path=input_csv,
                            selected_algorithms=["ForwardChaining"],
                        )
                    )
            self.assertIn("not found in CSV", str(exc_info.exception))

    def test_generate_experiment_visualizations_missing_csv_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_csv = Path(tmpdir) / "missing.csv"
            with self.assertRaises(ExperimentVisualizationError) as exc_info:
                VisualizationService.generate_experiment_visualizations(csv_path=missing_csv)
            self.assertIn("Input CSV not found", str(exc_info.exception))

    def test_generate_experiment_visualizations_plot_failure_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            input_csv = temp_dir / "experiment.csv"
            input_csv.write_text("dummy\n", encoding="utf-8")

            df = pd.DataFrame([{"algorithm": "A*", "solution_found": True, "time_ms": 1.0}])
            df_solved = pd.DataFrame([{"algorithm": "A*", "solution_found": True, "time_ms": 1.0}])

            def _load_data(_path: Path):
                return df, df_solved

            def _boom(_df: pd.DataFrame, _out_dir: Path):
                raise RuntimeError("plot crash")

            def _noop(_df: pd.DataFrame, _out_dir: Path):
                return None

            fake_module = SimpleNamespace(
                load_data=_load_data,
                plot_summary_dashboard=_boom,
                plot_time_comparison=_noop,
                plot_nodes_comparison=_noop,
                plot_difficulty_analysis=_noop,
                plot_size_analysis=_noop,
                plot_detailed_metrics=_noop,
            )

            with patch.object(
                VisualizationService,
                "_load_experiment_visualizer_module",
                return_value=fake_module,
            ):
                with self.assertRaises(ExperimentVisualizationError) as exc_info:
                    VisualizationService.generate_experiment_visualizations(csv_path=input_csv)

            self.assertIn("Failed to generate chart", str(exc_info.exception))


if __name__ == "__main__":
    unittest.main()
