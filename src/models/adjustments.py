"""Tactical adjustment value estimation (Phase 4).

For every detected tactical state we compare the observed outcomes of
alternative tactical responses. Teams do not choose tactics randomly, so a
naive mean comparison would be biased. We therefore estimate the value of each
adjustment with:

1. **Propensity scores** (logistic regression, stabilised IPW)
2. **Doubly robust estimation** (outcome-model plug-in + IPW residual)
3. **Bootstrap confidence intervals** (resampling whole matches, which
   respects within-match correlation)
4. **Sensitivity flags**: positivity (overlap), sample size, calibration
   quality, and out-of-time stability

Every estimate ships with: estimated value, confidence interval, sample size,
comparable situations, main risk, execution requirement, and a confidence
label - never a bare "this will work" claim.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression

from src.config import (
    ADJUSTMENT_EXECUTION,
    ADJUSTMENT_RISKS,
    DEFAULT_RANDOM_STATE,
    MIN_POSSESSIONS_PER_STRATEGY,
    POSITIVITY_MIN_PROPENSITY,
)

PROPENSITY_COVARS = ["start_x", "start_y", "minute", "score_diff", "is_home", "elo_diff"]
STRATEGY_COLS = [
    "s_build_up_shape_three_two_five",
    "s_fullback_inversion",
    "s_increase_winger_width",
    "s_attack_far_side_half_space",
    "s_third_man_combination",
    "s_reduce_risky_central_passes",
    "s_aggressive_counterpress",
    "s_mid_block_retreat",
]


def _clean_propensity_covars(sub: pd.DataFrame) -> pd.DataFrame:
    X = sub[PROPENSITY_COVARS].copy()
    for c in PROPENSITY_COVARS:
        if c not in X.columns:
            X[c] = 0.0
    return X.fillna(0.0).astype(float)


def _estimate_one(
    sub: pd.DataFrame,
    strategy: str,
    rng: np.random.Generator,
    n_boot: int,
) -> dict:
    t = (sub[strategy] == 1).astype(int).values
    y = sub["epv"].astype(float).values
    X = _clean_propensity_covars(sub)

    e_model = LogisticRegression(max_iter=1000, random_state=DEFAULT_RANDOM_STATE)
    e_model.fit(X, t)
    e = np.clip(e_model.predict_proba(X)[:, 1], POSITIVITY_MIN_PROPENSITY, 1 - POSITIVITY_MIN_PROPENSITY)
    e_mean = e.mean()

    # IPW (stabilised) - ATE
    w_t = e_mean / e
    w_c = (1 - e_mean) / (1 - e)
    ipw_ate = float((t * w_t * y).sum() / w_t[t == 1].sum() - ((1 - t) * w_c * y).sum() / w_c[t == 0].sum())

    # Doubly robust (AIPW) - ATE
    om_covs = X.copy()
    om_covs["_t"] = t
    om = LinearRegression()
    om.fit(om_covs, y)
    p1 = om.predict(om_covs.assign(_t=1))
    p0 = om.predict(om_covs.assign(_t=0))
    aipw_ate = float(
        (p1 - p0).mean()
        + (t * (y - p1) / e).mean()
        - ((1 - t) * (y - p0) / (1 - e)).mean()
    )

    # Bootstrap by match (cluster-resampling preserves within-match correlation).
    # We resample the SAME doubly-robust (AIPW) estimator the headline reports,
    # so the confidence interval is centred on the headline value.
    match_ids = sub["match_id"].values
    unique = np.unique(match_ids)
    boot_ates = []
    for _ in range(n_boot):
        picked = rng.choice(unique, size=len(unique), replace=True)
        idx = np.isin(match_ids, picked)
        if idx.sum() < 10:
            continue
        t_b, y_b = t[idx], y[idx]
        X_b = X[idx]
        if t_b.sum() == 0 or (1 - t_b).sum() == 0:
            continue
        e_b_model = LogisticRegression(max_iter=1000, random_state=DEFAULT_RANDOM_STATE)
        e_b_model.fit(X_b, t_b)
        e_b = np.clip(e_b_model.predict_proba(X_b)[:, 1], POSITIVITY_MIN_PROPENSITY, 1 - POSITIVITY_MIN_PROPENSITY)
        om_b = LinearRegression()
        om_b.fit(X_b.assign(_t=t_b), y_b)
        p1_b = om_b.predict(X_b.assign(_t=1))
        p0_b = om_b.predict(X_b.assign(_t=0))
        boot_ates.append(
            float(
                (p1_b - p0_b).mean()
                + (t_b * (y_b - p1_b) / e_b).mean()
                - ((1 - t_b) * (y_b - p0_b) / (1 - e_b)).mean()
            )
        )

    if len(boot_ates) >= 30:
        ci = np.sort(np.percentile(boot_ates, [2.5, 97.5]))
    else:
        ci = [aipw_ate, aipw_ate]

    n_treated = int(t.sum())
    n_control = int((1 - t).sum())
    overlap = float(np.mean(np.minimum(e, 1 - e)))
    positivity = float(np.min(e))

    return {
        "strategy": strategy,
        "strategy_label": ADJUSTMENT_LABELS_SAFE(strategy),
        "n_treated": n_treated,
        "n_control": n_control,
        "state_baseline_epv": float(y.mean()),
        "ipw_ate": ipw_ate,
        "aipw_ate": aipw_ate,
        "ci_low": float(ci[0]),
        "ci_high": float(ci[1]),
        "positivity_min_propensity": positivity,
        "overlap": overlap,
        "risk": ADJUSTMENT_RISKS.get(_adj_key(strategy), ""),
        "execution": ADJUSTMENT_EXECUTION.get(_adj_key(strategy), ""),
    }


def _adj_key(strategy: str) -> str:
    return strategy[2:] if strategy.startswith("s_") else strategy


def ADJUSTMENT_LABELS_SAFE(strategy: str) -> str:
    from src.config import ADJUSTMENT_LABELS

    return ADJUSTMENT_LABELS.get(_adj_key(strategy), strategy.replace("_", " "))


def confidence_label(est: dict, calibration_ece: float, temporal_gap: float) -> str:
    """Translate statistical evidence into an analyst-facing confidence label."""
    effect = abs(est["aipw_ate"])
    half_width = (est["ci_high"] - est["ci_low"]) / 2
    score = 1.0  # start at "medium-ish" then adjust
    n = est["n_treated"] + est["n_control"]
    if n < 25:
        score -= 0.6
    elif n < 100:
        score -= 0.2
    elif n >= 400:
        score += 0.1
    if est["overlap"] < 0.1 or est["positivity_min_propensity"] < POSITIVITY_MIN_PROPENSITY:
        score -= 0.3
    if half_width > max(effect, 1e-6):
        score -= 0.3
    if calibration_ece > 0.05:
        score -= 0.1
    if temporal_gap > 0.04:
        score -= 0.1
    if effect < 0.005:
        score -= 0.2
    if score >= 1.0:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def estimate_adjustment_values(
    possessions: pd.DataFrame,
    calibration_ece: float = 0.0,
    temporal_gap: float = 0.0,
    n_boot: int = 200,
    min_treated: int = MIN_POSSESSIONS_PER_STRATEGY,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> pd.DataFrame:
    """Estimate adjustment values per (tactical state x strategy)."""
    rng = np.random.default_rng(random_state)
    if "tactical_state" not in possessions.columns:
        raise ValueError("possessions must carry a 'tactical_state' column")

    rows = []
    for state, sub in possessions.groupby("tactical_state"):
        n_sub = len(sub)
        for strategy in STRATEGY_COLS:
            n_treated = int((sub[strategy] == 1).sum())
            # require a real control group (some treated AND some untreated)
            if n_treated < min_treated or n_treated >= n_sub:
                continue
            est = _estimate_one(sub, strategy, rng, n_boot)
            est["tactical_state"] = state
            est["confidence"] = confidence_label(est, calibration_ece, temporal_gap)
            rows.append(est)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.sort_values(["tactical_state", "aipw_ate"], ascending=[True, False]).reset_index(drop=True)
