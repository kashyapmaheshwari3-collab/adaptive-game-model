"""Tactical state detection (Phase 3).

Unsupervised clustering discovers repeated tactical patterns; football logic
names them. Clusters are never presented as "Cluster 7" - each cluster is
mapped to a named state from the tactical vocabulary with a human-readable
description.

The clustering uses phase descriptors (features that characterise the
possession as it evolves, e.g. pressure proxy, progression, strategy flags).
This is documented as such: the states describe what is happening *during*
the phase, which is the conditioning context for the adjustment estimation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.config import DEFAULT_RANDOM_STATE, TACTICAL_STATES

CLUSTER_FEATURES = [
    "start_x",
    "end_x",
    "net_progress_x",
    "n_passes",
    "duration_seconds",
    "pressure_proxy",
    "counterpress_flags",
    "max_shot_xg",
    "entered_final_third",
    "crossed_midfield",
    "score_diff",
    "minute",
    "is_home",
    "s_fullback_inversion",
    "s_increase_winger_width",
    "s_attack_far_side_half_space",
    "s_third_man_combination",
    "two_striker_front",
]

# Default "neutral" prototype used when a cluster cannot be confidently named.
_DEFAULT_STATE = "neutral_buildup"

# Hand-built canonical prototypes (raw feature units) for each tactical state.
# Cluster centroids are matched to the nearest prototype; the "neutral_buildup"
# prototype acts as the fallback, so every cluster gets a football name.
PROTOTYPES: dict[str, dict[str, float]] = {
    "opponent_low_block": {
        "n_passes": 12.0,
        "pressure_proxy": 0.18,
        "end_x": 40.0,
        "entered_final_third": 0.20,
        "net_progress_x": 10.0,
        "start_x": 30.0,
        "counterpress_flags": 0.30,
    },
    "opponent_high_press": {
        "pressure_proxy": 0.42,
        "start_x": 32.0,
        "n_passes": 3.0,
        "net_progress_x": 14.0,
        "entered_final_third": 0.1,
        "counterpress_flags": 0.1,
    },
    "narrow_front_two_buildup": {
        "two_striker_front": 0.8,
        "start_x": 30.0,
        "pressure_proxy": 0.10,
        "n_passes": 5.0,
        "net_progress_x": 18.0,
        "entered_final_third": 0.25,
    },
    "defensive_transition_after_loss": {
        "counterpress_flags": 0.8,
        "start_x": 65.0,
        "n_passes": 2.0,
        "net_progress_x": -15.0,
        "pressure_proxy": 0.15,
        "entered_final_third": 0.2,
        "end_x": 40.0,
    },
    "wide_overload": {
        "s_increase_winger_width": 0.8,
        "end_x": 66.0,
        "entered_final_third": 0.5,
        "net_progress_x": 22.0,
        "n_passes": 4.0,
        "pressure_proxy": 0.15,
    },
    "central_progression": {
        "net_progress_x": 38.0,
        "n_passes": 6.0,
        "pressure_proxy": 0.12,
        "entered_final_third": 0.3,
        "end_x": 66.0,
        "start_x": 30.0,
    },
    "final_third_vs_compact_defence": {
        "entered_final_third": 0.85,
        "n_passes": 7.0,
        "pressure_proxy": 0.10,
        "end_x": 90.0,
        "net_progress_x": 45.0,
        "start_x": 45.0,
    },
    "neutral_buildup": {
        "start_x": 8.0,
        "pressure_proxy": 0.12,
        "n_passes": 3.5,
        "net_progress_x": 16.0,
        "counterpress_flags": 0.0,
        "end_x": 30.0,
        "entered_final_third": 0.10,
    },
}

# Per-feature typical scale and weight used in the prototype distance.
_SCALES = {
    "start_x": 20.0,
    "end_x": 25.0,
    "net_progress_x": 20.0,
    "n_passes": 3.5,
    "duration_seconds": 30.0,
    "pressure_proxy": 0.15,
    "counterpress_flags": 0.5,
    "max_shot_xg": 0.1,
    "entered_final_third": 0.4,
    "crossed_midfield": 0.4,
    "score_diff": 1.5,
    "minute": 25.0,
    "is_home": 0.5,
    "s_fullback_inversion": 0.5,
    "s_increase_winger_width": 0.5,
    "s_attack_far_side_half_space": 0.5,
    "s_third_man_combination": 0.5,
    "two_striker_front": 0.5,
}
_WEIGHTS = {
    "pressure_proxy": 2.5,
    "counterpress_flags": 2.0,
    "entered_final_third": 2.4,
    "net_progress_x": 2.0,
    "n_passes": 2.0,
    "two_striker_front": 1.4,
    "s_increase_winger_width": 1.6,
    "start_x": 1.2,
    "end_x": 1.2,
    "minute": 0.2,
    "score_diff": 0.4,
    "is_home": 0.2,
    "max_shot_xg": 0.8,
    "s_fullback_inversion": 0.6,
    "s_attack_far_side_half_space": 0.8,
    "s_third_man_combination": 0.8,
    "duration_seconds": 0.3,
    "crossed_midfield": 0.3,
}


def _two_striker_front(formation) -> int:
    """Opponent lines up with a narrow front two (4-4-2 / 3-5-2)."""
    try:
        f = int(formation)
    except (TypeError, ValueError):
        return 0
    return 1 if f in (442, 352, 424) else 0


def _prepare(possessions: pd.DataFrame) -> pd.DataFrame:
    df = possessions.copy()
    df["two_striker_front"] = df["opponent_formation"].map(_two_striker_front)
    for col in CLUSTER_FEATURES:
        if col not in df.columns:
            df[col] = 0.0
    df = df[CLUSTER_FEATURES].fillna(0.0).astype(float)
    return df


def state_name(centroid: pd.Series) -> str:
    """Name a cluster centroid: nearest football prototype (weighted distance)."""
    best_state = _DEFAULT_STATE
    best_score = float("inf")
    for state, proto in PROTOTYPES.items():
        score = 0.0
        for feature, target in proto.items():
            v = float(centroid.get(feature, 0.0))
            scale = _SCALES.get(feature, 10.0)
            weight = _WEIGHTS.get(feature, 1.0)
            score += weight * ((v - target) / scale) ** 2
        if score < best_score:
            best_score = score
            best_state = state
    return best_state


def fit_tactical_states(
    possessions: pd.DataFrame,
    n_clusters: int = 8,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> tuple[pd.Series, dict[int, str], object, pd.DataFrame]:
    """Cluster possessions, name clusters, return (state_assignment, cluster_map, kmeans, prepared)."""
    prepared = _prepare(possessions)
    scaler = StandardScaler()
    Z = scaler.fit_transform(prepared)
    kmeans = KMeans(
        n_clusters=min(n_clusters, max(2, len(possessions))), n_init=10, random_state=random_state
    )
    labels = kmeans.fit_predict(Z)

    # name clusters from RAW means (thresholds are in raw feature units)
    named = prepared.copy()
    named["_cluster"] = labels
    raw_centroids = named.groupby("_cluster")[CLUSTER_FEATURES].mean()
    cluster_map = {int(k): state_name(row) for k, row in raw_centroids.iterrows()}

    assignment = pd.Series(labels, index=possessions.index, name="cluster")
    states = assignment.map(cluster_map).rename("tactical_state").astype("category")
    states = states.cat.set_categories(TACTICAL_STATES)
    return states, cluster_map, kmeans, prepared


def predict_states(kmeans: object, prepared: pd.DataFrame) -> np.ndarray:
    """Apply a fitted KMeans to new possession features (returns cluster labels)."""
    return kmeans.predict(prepared.values)
