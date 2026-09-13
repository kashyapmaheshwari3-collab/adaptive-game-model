"""Model metrics: regression quality + calibration, with baselines."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.models.calibration import calibration_metrics
from src.models.value_model import predict_epv


def evaluate_epv(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    resid = y_true - y_pred
    rmse = float(np.sqrt(np.mean(resid**2)))
    mae = float(np.mean(np.abs(resid)))
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0
    return {"rmse": rmse, "mae": mae, "r2": r2, "n": int(len(y_true))}


def evaluate_all_models(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    xgb: object,
    calibrator: object | None,
    baselines,
) -> dict:
    """Compare main model vs baselines on the out-of-time test set."""
    y_test = test["epv"].astype(float).values

    def score(preds: np.ndarray) -> dict:
        return evaluate_epv(y_test, preds)

    results = {
        "xgboost_calibrated": score(predict_epv(xgb, test, calibrator)),
        "xgboost_raw": score(predict_epv(xgb, test)),
        "linear": _score_sklearn(baselines.linear, test),
        "elo_only": _score_sklearn(baselines.elo_only, test),
        "league_average": score(np.full(len(y_test), baselines.league_average_epv)),
    }
    return results


def _score_sklearn(model, test: pd.DataFrame) -> dict:
    from src.models.value_model import _prep_features

    preds = model.predict(_prep_features(test))
    return evaluate_epv(test["epv"].astype(float).values, preds)


def calibration_on_test(test: pd.DataFrame, xgb: object, calibrator: object | None) -> dict:
    preds = predict_epv(xgb, test, calibrator)
    return calibration_metrics(test["epv"].astype(float).values, preds)
