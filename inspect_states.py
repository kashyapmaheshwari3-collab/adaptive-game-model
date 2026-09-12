import json

import joblib
import pandas as pd

from src.models.tactical_states import _prepare

poss = pd.read_parquet("data/processed/possessions.parquet")
cm = json.load(open("data/processed/cluster_map.json", encoding="utf-8"))
print("cluster -> state:", json.dumps(cm))

km = joblib.load("data/processed/state_model.joblib")
prep = _prepare(poss)
labels = km.predict(prep.values)
prep["_cluster"] = labels
feats = [
    "start_x", "end_x", "net_progress_x", "n_passes", "duration_seconds",
    "pressure_proxy", "counterpress_flags", "entered_final_third",
    "s_increase_winger_width", "two_striker_front", "max_shot_xg",
]
print(prep.groupby("_cluster")[feats].mean().round(2).to_string())
print(prep["_cluster"].value_counts().sort_index().to_string())

# also print the distance of each centroid to each prototype
from src.models.tactical_states import PROTOTYPES, _SCALES, _WEIGHTS

cent = prep.groupby("_cluster")[feats].mean()
for c in cent.index:
    scores = {}
    for state, proto in PROTOTYPES.items():
        s = 0.0
        for f, t in proto.items():
            v = cent.loc[c, f]
            s += _WEIGHTS.get(f, 1.0) * ((v - t) / _SCALES.get(f, 10.0)) ** 2
        scores[state] = round(s, 2)
    print(c, "->", json.dumps(scores))
