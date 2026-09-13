"""Recommendation engine (the coach-facing decision).

Turns the adjustment-value table into ranked, uncertainty-quantified
recommendations per tactical state, plus an overall recommendation for a match.

The output deliberately does NOT say "this tactic will definitely work". It
says: "against this opponent structure, this adjustment historically created
+X expected possession value per possession (95% CI [a, b]), with
{low|medium|high} confidence, based on N comparable sequences."
"""

from __future__ import annotations

import pandas as pd

from src.config import ADJUSTMENT_LABELS, STATE_LABELS

MIN_UPHILL_FOR_RECOMMENDATION = 0.005


def build_recommendations(adjustments: pd.DataFrame) -> pd.DataFrame:
    """Rank adjustment estimates; keep those with positive signal per state."""
    if adjustments.empty:
        return adjustments
    recs = adjustments.copy()
    recs["ci_excludes_zero"] = (recs["ci_low"] > 0) | (recs["ci_high"] < 0)
    recs["uplift_ci"] = recs.apply(lambda r: f"[{r['ci_low']:+.3f}, {r['ci_high']:+.3f}]", axis=1)
    # rank: prefer bigger uplift, penalise wide CIs and low confidence
    recs["ci_halfwidth"] = (recs["ci_high"] - recs["ci_low"]) / 2
    recs["quality_score"] = recs["aipw_ate"] - recs["ci_halfwidth"]
    recs = recs.sort_values(
        ["tactical_state", "quality_score"], ascending=[True, False]
    ).reset_index(drop=True)
    return recs


def recommendation_text(row: pd.Series) -> str:
    state = STATE_LABELS.get(row["tactical_state"], row["tactical_state"].replace("_", " "))
    adj = ADJUSTMENT_LABELS.get(row["strategy"], row["strategy"].replace("_", " "))
    n = int(row["n_treated"]) + int(row["n_control"])
    return (
        f"Against **{state}**, adopting **{adj}** historically created "
        f"**{row['aipw_ate']:+.3f} expected possession value per possession** "
        f"(95% CI [{row['ci_low']:+.3f}, {row['ci_high']:+.3f}]) with "
        f"**{row['confidence']} confidence**, based on {n} comparable sequences."
    )


def overall_recommendation(recs: pd.DataFrame) -> dict | None:
    """Pick the single highest-value, adequately-supported recommendation."""
    if recs.empty:
        return None
    cand = recs[recs["aipw_ate"] > MIN_UPHILL_FOR_RECOMMENDATION]
    if cand.empty:
        return None
    cand = cand.sort_values("quality_score", ascending=False)
    top = cand.iloc[0]
    return {
        "tactical_state": top["tactical_state"],
        "strategy": top["strategy"],
        "uplift": float(top["aipw_ate"]),
        "ci": [float(top["ci_low"]), float(top["ci_high"])],
        "confidence": top["confidence"],
        "n_sequences": int(top["n_treated"]) + int(top["n_control"]),
        "risk": top["risk"],
        "execution": top["execution"],
        "text": recommendation_text(top),
    }
