"""Error analysis (component 5): three successes, three failures, and why.

A portfolio project is credible when it shows its failures. For the out-of-time
test set we surface the three best predictions (small residual, high
confidence) and the three worst, explain the likely cause from the feature
context, and state which data would have improved the failure cases.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _explain(row: pd.Series, resid: float, kind: str) -> str:
    direction = "under-predicted" if resid > 0 else "over-predicted"
    state = row.get("tactical_state", "unknown")
    if direction == "under-predicted":
        if row.get("max_shot_xg", 0) >= 0.15:
            return (
                f"Model expected a routine possession but a {row['max_shot_xg']:.2f}-xG chance "
                f"arrived from a {state.replace('_', ' ')} scenario - high-variance outcomes "
                "from sparse rare events."
            )
        return (
            f"Model under-predicted value in {state.replace('_', ' ')}: the possession created a "
            "dangerous action (shot assist / box entry) that the ex-ante features could not foresee."
        )
    if row.get("n_passes", 0) >= 6:
        return (
            f"Model over-predicted value in {state.replace('_', ' ')}: long, patient possession "
            "with no final-third entry - possession without penetration inflates ex-ante value."
        )
    return (
        f"Model over-predicted value in {state.replace('_', ' ')}: possession was lost early "
        "despite an advantageous start position - opponent pressure in the specific sequence "
        "was higher than the aggregate context suggested."
    )


def error_analysis(test: pd.DataFrame, preds: np.ndarray) -> dict:
    """Return the three best and three worst test-set predictions with explanations."""
    df = test.copy()
    df["pred_epv"] = preds
    df["resid"] = df["epv"] - df["pred_epv"]
    df["abs_resid"] = df["resid"].abs()
    df = df.sort_values("abs_resid", ascending=True).reset_index(drop=True)

    def row_to_dict(r: pd.Series) -> dict:
        return {
            "match_id": int(r["match_id"]),
            "possession": int(r["possession"]),
            "team": r["possession_team"],
            "opponent": r["opponent_team"],
            "state": r.get("tactical_state", "unknown"),
            "minute": int(r["minute"]),
            "actual_epv": float(r["epv"]),
            "pred_epv": float(r["pred_epv"]),
            "residual": float(r["resid"]),
            "outcome_level": int(r["outcome_level"]),
            "explanation": _explain(r, float(r["resid"]), "best"),
        }

    best = [row_to_dict(df.iloc[i]) for i in range(min(3, len(df))) if df["abs_resid"].iloc[i] == df["abs_resid"].iloc[i]]
    worst = df.sort_values("abs_resid", ascending=False)
    worst = [row_to_dict(worst.iloc[i]) for i in range(min(3, len(worst)))]

    failure_modes = []
    for r in worst:
        cause = "rare high-variance event (shot) not captured ex-ante" if r["actual_epv"] > r["pred_epv"] and r["outcome_level"] >= 4 else (
            "sterile possession over-valued" if r["actual_epv"] < r["pred_epv"] else "context mismatch")
        missing_data = (
            "opponent pressure intensity at each action (pressure events are partially captured)" 
            if cause.startswith("rare") else
            "xT-style pitch control maps / tracking data for actual space opened"
        )
        r["failure_cause"] = cause
        r["data_that_would_improve"] = missing_data
        failure_modes.append(r)

    return {
        "successes": best,
        "failures": failure_modes,
        "n_test": int(len(df)),
        "median_abs_resid": float(df["abs_resid"].median()),
        "p90_abs_resid": float(df["abs_resid"].quantile(0.9)),
    }
