"""Possession value model (Phase 2).

Estimates the expected value of a possession state. The target is the
``epv`` column (expected possession value in goal-probability units, see
``src/features/possessions.py`` and ``docs/methodology.md``).

Design notes
------------
- Features are **ex-ante**: everything is known at the moment the possession
  starts (location, recovery type, context, team strength). This avoids
  look-ahead leakage into the value estimate itself.
- Baselines are always reported alongside the main model (league average,
  linear regression, Elo-only) - required by the "baseline" component.
- Calibration is applied out-of-time so coaching staff get honest numbers.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBRegressor

from src.config import DEFAULT_RANDOM_STATE
from src.models.calibration import calibrate_isotonic

# Ex-ante feature set: observable at possession start.
FEATURE_COLS = [
    "start_x",
    "start_y",
    "recovery_type",
    "play_pattern",
    "minute",
    "period",
    "is_home",
    "score_diff",
    "team_formation",
    "opponent_formation",
    "team_elo",
    "opp_elo",
    "elo_diff",
    "first_pressure",
]

_CAT_COLS = ["recovery_type", "play_pattern", "team_formation", "opponent_formation"]
_NUM_COLS = [c for c in FEATURE_COLS if c not in _CAT_COLS]


@dataclass
class BaselineModels:
    """Baselines required by the evaluation contract."""

    league_average_epv: float
    dummy: object
    linear: object
    elo_only: object


def _prep_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df[FEATURE_COLS].copy()
    out["team_formation"] = out["team_formation"].fillna("unknown").astype(str)
    out["opponent_formation"] = out["opponent_formation"].fillna("unknown").astype(str)
    out["recovery_type"] = out["recovery_type"].fillna("unknown").astype(str)
    out["play_pattern"] = out["play_pattern"].fillna("unknown").astype(str)
    return out


def _build_pipeline(kind: str) -> Pipeline:
    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), _NUM_COLS),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), _CAT_COLS),
        ]
    )
    if kind == "linear":
        return Pipeline([("pre", pre), ("model", LinearRegression())])
    if kind == "elo_only":
        return Pipeline(
            [
                (
                    "pre",
                    ColumnTransformer(
                        transformers=[
                            ("elo", StandardScaler(), ["team_elo", "opp_elo", "elo_diff"])
                        ]
                    ),
                ),
                ("model", LinearRegression()),
            ]
        )
    return Pipeline([("pre", pre), ("model", DummyRegressor(strategy="mean"))])


def fit_value_models(
    train: pd.DataFrame,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> tuple[object, object, BaselineModels]:
    """Fit the calibrated XGBoost value model + baselines on a train frame.

    Returns ``(model, calibrator, baselines)``.
    """
    X = _prep_features(train)
    y = train["epv"].astype(float).values

    xgb = Pipeline(
        [
            (
                "pre",
                ColumnTransformer(
                    transformers=[
                        ("num", StandardScaler(), _NUM_COLS),
                        (
                            "cat",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                            _CAT_COLS,
                        ),
                    ]
                ),
            ),
            (
                "model",
                XGBRegressor(
                    n_estimators=300,
                    max_depth=4,
                    learning_rate=0.05,
                    subsample=0.9,
                    colsample_bytree=0.8,
                    reg_lambda=1.0,
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    xgb.fit(X, y)
    dummy = _build_pipeline("dummy").fit(X, y)
    linear = _build_pipeline("linear").fit(X, y)
    elo_only = _build_pipeline("elo_only").fit(X, y)

    baselines = BaselineModels(
        league_average_epv=float(np.mean(y)),
        dummy=dummy,
        linear=linear,
        elo_only=elo_only,
    )
    # calibrator is fit later on out-of-time data (see pipeline)
    return xgb, None, baselines


def fit_calibrator(xgb: object, val: pd.DataFrame) -> object:
    """Fit isotonic calibration on an out-of-time validation frame."""
    raw = xgb.predict(_prep_features(val))
    return calibrate_isotonic(raw, val["epv"].astype(float).values)


def predict_epv(model: object, df: pd.DataFrame, calibrator: object | None = None) -> np.ndarray:
    """Predict EPV for a possession frame (optionally calibrated)."""
    raw = model.predict(_prep_features(df))
    if calibrator is not None:
        return calibrator.predict(np.asarray(raw, dtype=float))
    return np.asarray(raw, dtype=float)
