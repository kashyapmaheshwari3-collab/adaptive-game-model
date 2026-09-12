"""Tune prototypes: score the five real clusters against each prototype."""
import json

import joblib
import pandas as pd

from src.models.tactical_states import PROTOTYPES, _SCALES, _WEIGHTS, _prepare

poss = pd.read_parquet("data/processed/possessions.parquet")
km = joblib.load("data/processed/state_model.joblib")
prep = _prepare(poss)
labels = km.predict(prep.values)
prep["_cluster"] = labels

real_centroids = {
    "c0_quick_deep_turnover": dict(start_x=17.15, end_x=38.22, net_progress_x=21.07, n_passes=3.27,
                                   duration_seconds=1.56, pressure_proxy=0.29, counterpress_flags=0.17,
                                   entered_final_third=0.0, s_increase_winger_width=0.0,
                                   two_striker_front=0.0, max_shot_xg=0.0),
    "c1_high_recovery_retreat": dict(start_x=69.5, end_x=18.46, net_progress_x=-51.05, n_passes=6.59,
                                     duration_seconds=1.01, pressure_proxy=0.30, counterpress_flags=0.20,
                                     entered_final_third=0.0, s_increase_winger_width=0.0,
                                     two_striker_front=0.0, max_shot_xg=0.01),
    "c3_goal_kick": dict(start_x=6.09, end_x=6.09, net_progress_x=0.0, n_passes=0.96,
                         duration_seconds=6.0, pressure_proxy=0.01, counterpress_flags=0.01,
                         entered_final_third=0.0, s_increase_winger_width=0.0,
                         two_striker_front=0.0, max_shot_xg=0.0),
    "c5_final_third": dict(start_x=54.32, end_x=83.84, net_progress_x=29.52, n_passes=5.93,
                           duration_seconds=1.28, pressure_proxy=0.26, counterpress_flags=0.23,
                           entered_final_third=0.57, s_increase_winger_width=0.0,
                           two_striker_front=0.0, max_shot_xg=0.02),
    "c6_sterile_long": dict(start_x=12.13, end_x=25.21, net_progress_x=13.08, n_passes=16.17,
                            duration_seconds=1.11, pressure_proxy=0.20, counterpress_flags=0.31,
                            entered_final_third=0.02, s_increase_winger_width=0.0,
                            two_striker_front=0.0, max_shot_xg=0.01),
}

for name, cent in real_centroids.items():
    scores = {}
    for state, proto in PROTOTYPES.items():
        s = 0.0
        for f, t in proto.items():
            v = cent.get(f, 0.0)
            s += _WEIGHTS.get(f, 1.0) * ((v - t) / _SCALES.get(f, 10.0)) ** 2
        scores[state] = round(s, 2)
    best = min(scores, key=scores.get)
    print(f"{name}: best={best}  scores={json.dumps(scores)}")
