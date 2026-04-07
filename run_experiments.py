#!/usr/bin/env python3
"""
Simple wrapper script to run experiments from project root.

Usage:
    python run_experiments.py
    python run_experiments.py --timeout 60
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import and run the actual experiment runner
from core.experiments.run_experiments import main

if __name__ == "__main__":
    main()
