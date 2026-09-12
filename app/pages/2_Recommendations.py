"""Recommendations - full ranked table with uncertainty, risks and execution."""

import streamlit as st

try:
    from app.utils import load_artefacts
except ModuleNotFoundError:
    from utils import load_artefacts
from src.config import ADJUSTMENT_LABELS, STATE_LABELS

st.set_page_config(page_title="Recommendations", page_icon="🎯", layout="wide")
st.title("Tactical Adjustment Recommendations")
st.caption("Every estimate carries its confidence interval, sample size, risk and execution requirement.")

a = load_artefacts()
recs = a["recommendations"]
poss = a["possessions"]

if recs.empty:
    st.warning("No recommendations yet - run `python -m src.pipeline.run_all` first.")
    st.stop()

st.dataframe(
    recs[
        [
            "tactical_state", "strategy", "strategy_label", "aipw_ate",
            "ci_low", "ci_high", "confidence", "n_treated", "n_control",
            "overlap", "risk", "execution",
        ]
    ].rename(
        columns={
            "tactical_state": "State", "strategy_label": "Adjustment",
            "aipw_ate": "Uplift (EPV/possession)", "ci_low": "CI low",
            "ci_high": "CI high", "confidence": "Confidence",
            "n_treated": "Treated", "n_control": "Control",
            "overlap": "Overlap", "risk": "Risk", "execution": "Execution",
        }
    ),
    use_container_width=True,
    height=500,
)

st.subheader("How to read these numbers")
st.markdown(
    """
    - **Uplift** = doubly-robust average treatment effect in expected possession
      value units per possession (goal-probability terms).
    - **CI** = 95% match-clustered bootstrap interval. If it excludes zero, the
      signal is statistically non-trivial.
    - **Confidence** = combined label from sample size, overlap, CI width,
      calibration ECE and temporal stability.
    - **Risk / Execution** = coach-facing context for the human decision.
    """
)

st.subheader("Recommendation cards")
state_filter = st.multiselect(
    "Filter by state", sorted(recs["tactical_state"].unique()),
    default=sorted(recs["tactical_state"].unique())[:3],
)
for _, r in recs[recs["tactical_state"].isin(state_filter)].sort_values("aipw_ate", ascending=False).iterrows():
    with st.container(border=True):
        st.markdown(
            f"### {STATE_LABELS.get(r['tactical_state'], r['tactical_state'])}"
        )
        st.markdown(
            f"**Recommendation:** {ADJUSTMENT_LABELS.get(r['strategy'], r['strategy'])}  \n"
            f"- Expected benefit: **{r['aipw_ate']:+.3f} EPV per possession** "
            f"(95% CI [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}])  \n"
            f"- Confidence: **{r['confidence']}** based on "
            f"{int(r['n_treated']) + int(r['n_control'])} comparable sequences "
            f"({int(r['n_treated'])} treated / {int(r['n_control'])} control)  \n"
            f"- Main risk: {r['risk']}  \n"
            f"- Execution requirement: {r['execution']}"
        )
