"""Calibration utilities: isotonic correction + calibration metrics.

A model with slightly lower accuracy but excellent calibration is more useful
to a coaching staff than an opaque model with impressive headline accuracy.
"""

from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression


def calibrate_isotonic(raw: np.ndarray, y: np.ndarray) -> object:
    """Fit an isotonic regression from raw predictions to observed targets."""
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=max(1.0, float(np.max(y))))
    iso.fit(np.asarray(raw, dtype=float), np.asarray(y, dtype=float))
    return iso


def calibration_metrics(y_true: np.ndarray, y_pred: np.ndarray, n_bins: int = 10) -> dict:
    """Expected calibration error + Brier-style mean squared error on deciles."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    order = np.argsort(y_pred)
    y_true_s, y_pred_s = y_true[order], y_pred[order]

    edges = np.linspace(0, len(y_pred_s), n_bins + 1, dtype=int)
    ece, mse = 0.0, 0.0
    bin_rows = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        if hi <= lo:
            continue
        seg_t = y_true_s[lo:hi]
        seg_p = y_pred_s[lo:hi]
        m = float(np.mean(seg_t))
        p = float(np.mean(seg_p))
        w = len(seg_t) / len(y_pred_s)
        ece += w * abs(p - m)
        mse += w * float(np.mean((seg_t - seg_p) ** 2))
        bin_rows.append({"bin": i, "pred_mean": p, "actual_mean": m, "n": int(len(seg_t))})
    return {
        "ece": float(ece),
        "mse": float(mse),
        "n": int(len(y_pred)),
        "bins": bin_rows,
        "mean_actual": float(np.mean(y_true)),
        "mean_pred": float(np.mean(y_pred)),
    }
