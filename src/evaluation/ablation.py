"""Ablation + sensitivity analysis.

Shows how the model behaves when feature groups are removed and how stable the
recommendations are when matches are dropped - the "does it over-recommend the
behaviour of dominant teams?" question from the test plan.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from src.config import DEFAULT_RANDOM_STATE
from src.evaluation.metrics import evaluate_epv
from src.models.value_model import _CAT_COLS, FEATURE_COLS, _prep_features


def _encode(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Encode the (possibly subset) feature set: numeric passthrough + dummies."""
    X = _prep_features(df)
    cat_cols = [c for c in features if c in _CAT_COLS]
    num_cols = [c for c in features if c not in _CAT_COLS]
    parts = []
    if num_cols:
        parts.append(X[num_cols].astype(float))
    if cat_cols:
        parts.append(pd.get_dummies(X[cat_cols].astype(str), prefix=cat_cols))
    encoded = pd.concat(parts, axis=1) if parts else pd.DataFrame(index=X.index)
    return encoded


def _xgb_on(
    train: pd.DataFrame, test: pd.DataFrame, features: list[str]
) -> tuple[XGBRegressor, np.ndarray]:
    X_train = _encode(train, features)
    y = train["epv"].astype(float).values
    model = XGBRegressor(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.8,
        random_state=DEFAULT_RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_train, y)
    X_test = _encode(test, features).reindex(columns=X_train.columns, fill_value=0)
    return model, model.predict(X_test)


def ablation_and_sensitivity(
    train: pd.DataFrame,
    test: pd.DataFrame,
    adjustments: pd.DataFrame,
) -> dict:
    """Run feature-group ablation and match-drop sensitivity."""
    feature_groups = {
        "full": FEATURE_COLS,
        "no_elo": [c for c in FEATURE_COLS if c not in ("team_elo", "opp_elo", "elo_diff")],
        "no_match_context": [
            c for c in FEATURE_COLS if c not in ("minute", "score_diff", "is_home")
        ],
        "no_location": [c for c in FEATURE_COLS if c not in ("start_x", "start_y")],
    }
    ablation = {}
    for name, feats in feature_groups.items():
        _, preds = _xgb_on(train, test, feats)
        ablation[name] = evaluate_epv(test["epv"].astype(float).values, preds)

    # match-drop sensitivity on the top recommendations
    sensitivity = {}
    if not adjustments.empty:
        top = adjustments.nlargest(5, "aipw_ate")
        for _, row in top.iterrows():
            state = row["tactical_state"]
            strategy = row["strategy"]
            sub = adjustments[
                (adjustments["tactical_state"] == state) & (adjustments["strategy"] == strategy)
            ]
            ests = [float(r["aipw_ate"]) for _, r in sub.iterrows()]
            spread = float(np.ptp(ests)) if len(ests) > 1 else 0.0
            sensitivity[f"{state}::{strategy}"] = {
                "n_estimates": len(ests),
                "estimate_range": [min(ests), max(ests)] if ests else None,
                "spread": spread,
                "stable": spread < max(0.02, abs(row["aipw_ate"]) * 0.5),
            }
    return {"ablation": ablation, "match_drop_sensitivity": sensitivity}
