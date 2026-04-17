import argparse
import subprocess
import sys
from pathlib import Path


def _run_gui() -> int:
    app_path = Path(__file__).parent / "gui" / "app.py"
    command = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    return subprocess.call(command)


def _run_experiments(args: argparse.Namespace) -> int:
    from experiments import run_experiments

    previous_argv = sys.argv
    try:
        sys.argv = ["run_experiments.py", *args.extra]
        run_experiments.main()
        return 0
    finally:
        sys.argv = previous_argv


def _run_visualization(args: argparse.Namespace) -> int:
    from experiments import visualize_experiments

    previous_argv = sys.argv
    try:
        sys.argv = ["visualize_experiments.py", *args.extra]
        visualize_experiments.main()
        return 0
    finally:
        sys.argv = previous_argv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Canonical project CLI for GUI and experiment workflows.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    gui_parser = subparsers.add_parser("gui", help="Run Streamlit GUI.")
    gui_parser.set_defaults(handler=lambda _: _run_gui())

    experiments_parser = subparsers.add_parser(
        "experiments",
        help="Run experiment-related commands.",
    )
    experiment_subparsers = experiments_parser.add_subparsers(
        dest="experiment_command",
        required=True,
    )

    run_parser = experiment_subparsers.add_parser(
        "run",
        help="Run solver benchmark experiments.",
    )
    run_parser.add_argument("extra", nargs=argparse.REMAINDER)
    run_parser.set_defaults(handler=_run_experiments)

    visualize_parser = experiment_subparsers.add_parser(
        "visualize",
        help="Generate experiment charts from CSV.",
    )
    visualize_parser.add_argument("extra", nargs=argparse.REMAINDER)
    visualize_parser.set_defaults(handler=_run_visualization)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
