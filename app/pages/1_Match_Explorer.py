"""Match Explorer - per-match tactical profile and recommendations."""

import streamlit as st

try:
    from app.utils import load_artefacts
except ModuleNotFoundError:
    from utils import load_artefacts
from src.config import ADJUSTMENT_LABELS, STATE_LABELS

st.set_page_config(page_title="Match Explorer", page_icon="📊", layout="wide")
st.title("Match Explorer")
st.caption("Pick a match, see its tactical-state mix and what the engine would adjust.")

a = load_artefacts()
poss = a["possessions"]
matches = a["matches"]
recs = a["recommendations"]
decisions = a["decisions"]

match_ids = sorted(matches["match_id"].unique().tolist())
labels = {}
for _, m in matches.iterrows():
    labels[m["match_id"]] = (
        f"{m['match_date']} | {m['home_team']} {m['home_score']}-{m['away_score']} {m['away_team']}"
    )

sel = st.selectbox("Match", match_ids, format_func=lambda i: labels.get(i, str(i)))
sub = poss[poss["match_id"] == sel]

c1, c2 = st.columns([2, 3])

with c1:
    st.subheader("Tactical state mix")
    if not sub.empty:
        dist = sub["tactical_state"].value_counts()
        st.bar_chart(dist)
        for state, n in dist.items():
            st.write(f"- {STATE_LABELS.get(state, state)}: {n}")
    else:
        st.info("No possessions for this match.")

with c2:
    st.subheader("Recommended adjustments for this match")
    if not sub.empty:
        states_in_match = set(sub["tactical_state"].unique())
        match_recs = recs[recs["tactical_state"].isin(states_in_match)] if not recs.empty else recs
        if not match_recs.empty:
            for _, r in match_recs.sort_values("aipw_ate", ascending=False).head(5).iterrows():
                st.markdown(
                    f"**{ADJUSTMENT_LABELS.get(r['strategy'], r['strategy'])}**  \n"
                    f"_in {STATE_LABELS.get(r['tactical_state'], r['tactical_state'])}_  \n"
                    f"Uplift {r['aipw_ate']:+.3f} (CI [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}]), "
                    f"confidence {r['confidence']}"
                )
                st.divider()
        else:
            st.info("No adjustment estimates above sample threshold for this match's states yet.")

st.subheader("Possession detail (outcome >= 4: shots)")
if not sub.empty:
    shots = sub[sub["outcome_level"] >= 4]
    if not shots.empty:
        st.dataframe(
            shots[
                [
                    "possession",
                    "possession_team",
                    "opponent_team",
                    "minute",
                    "tactical_state",
                    "outcome_level",
                    "max_shot_xg",
                    "epv",
                    "start_x",
                    "end_x",
                ]
            ]
            .sort_values("max_shot_xg", ascending=False)
            .head(20),
            use_container_width=True,
        )
    else:
        st.info("No shot-level possessions in this match.")
