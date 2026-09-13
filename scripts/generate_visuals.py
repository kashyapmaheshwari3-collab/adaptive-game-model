"""Generate all visual artefacts: architecture diagram, social cards, pitch plots.

Usage::

    python scripts/generate_visuals.py
"""

from __future__ import annotations

import json

import pandas as pd
from src.config import PROCESSED_DIR, VISUALS_DIR
from src.visualisation import (
    plot_calibration,
    plot_state_heatmap,
    render_architecture_diagram,
    render_social_cards,
)


def main() -> None:
    ev = json.load(open(PROCESSED_DIR / "evaluation_report.json", encoding="utf-8"))
    poss = pd.read_parquet(PROCESSED_DIR / "possessions.parquet")

    print("1/4 architecture diagram")
    render_architecture_diagram(VISUALS_DIR / "architecture_diagram.png")

    print("2/4 social cards")
    render_social_cards()

    print("3/4 calibration curve")
    plot_calibration(ev.get("calibration_test", {}), VISUALS_DIR / "calibration_curve.png")

    print("4/4 state heatmaps")
    for state in poss["tactical_state"].value_counts().head(5).index:
        plot_state_heatmap(poss, state, VISUALS_DIR / f"state_{state}.png")

    print("Visuals done.")


if __name__ == "__main__":
    main()
