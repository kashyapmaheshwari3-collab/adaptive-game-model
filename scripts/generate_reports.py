"""Generate all PDF reports from the latest pipeline artefacts.

Usage::

    python scripts/generate_reports.py
    python scripts/generate_reports.py --quick   # CI smoke (small reports)
"""

from __future__ import annotations

import argparse
import time

from src.reporting import (
    build_coach_pdf,
    build_opponent_pdf,
    build_recruitment_pdf,
    build_technical_pdf,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PDF reports")
    parser.add_argument("--quick", action="store_true", help="CI smoke mode")
    parser.parse_args()
    t0 = time.time()
    paths = [
        build_technical_pdf(),
        build_coach_pdf(),
        build_recruitment_pdf(),
        build_opponent_pdf(),
    ]
    for p in paths:
        print(f"  wrote {p} ({p.stat().st_size / 1024:.0f} KB)")
    print(f"Reports generated in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
