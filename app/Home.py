"""Adaptive Game Model - Home.

The coach-facing entry point: problem statement, what the system answers,
key results, and where to go next.
"""

import streamlit as st

try:
    from app.utils import load_artefacts
except ModuleNotFoundError:
    from utils import load_artefacts

st.set_page_config(page_title="Adaptive Game Model", page_icon="⚽", layout="wide")

st.title("Adaptive Game Model")
st.caption("A Context-Aware Tactical Adjustment Engine for Football")

a = load_artefacts()
ev = a["evaluation"]
recs = a["recommendations"]

col1, col2, col3 = st.columns(3)
col1.metric("Matches modelled", f"{ev.get('n_matches', 0)}")
col2.metric("Possessions", f"{ev.get('n_possessions', 0):,}")
col3.metric("Recommendations", f"{len(recs):,}")

st.divider()

left, right = st.columns([3, 2])

with left:
    st.subheader("The question we answer")
    st.markdown(
        "> **\"Given the opponent's structure and our current game model, which tactical "
        'adjustment is most likely to improve our next attacking or defensive phase?"**'
    )
    st.markdown(
        """
        This is **not** another win predictor. The system:
        - detects recurring tactical states (opponent low block, high press,
          wide overload, defensive transition, ...),
        - compares alternative tactical responses as a **decision problem**,
        - estimates the counterfactual value of each adjustment with
          **confidence intervals, sample sizes and applicability limits**,
        - talks to a coach in coaching language, never as an opaque score.
        """
    )
    st.markdown(
        "**Honest scope:** this is an *event-based* tactical decision model, "
        "not a complete tracking-data system."
    )

    st.subheader("Why it is different")
    st.markdown(
        """
        - **Decision output**, not description: \u201cwhich change should we make?\u201d
        - **Named tactical states** - football prototypes, never \u201cCluster 7\u201d.
        - **Causal estimates** (IPW + doubly-robust) instead of naive averages.
        - **Temporal validation** - the future is the test set.
        - **Uncertainty everywhere** - every recommendation ships with its 95% CI.
        - **Human-in-the-loop** - analysts and coaches leave feedback on every card.
        """
    )

with right:
    st.subheader("Current best adjustment")
    if not recs.empty:
        top = recs.sort_values("aipw_ate", ascending=False).iloc[0]
        st.markdown(
            f"**{top['strategy_label']}**  \n"
            f"when facing **{top['tactical_state'].replace('_', ' ')}**  \n"
            f"Uplift: **{top['aipw_ate']:+.3f} EPV/possession**  \n"
            f"95% CI: [{top['ci_low']:+.3f}, {top['ci_high']:+.3f}]  \n"
            f"Confidence: **{top['confidence']}**"
        )
    else:
        st.info("Run the pipeline to populate recommendations.")
    st.subheader("Key validation result")
    m = ev.get("metrics", {})
    if m:
        xgb = m.get("xgboost_calibrated", {})
        avg = m.get("league_average", {})
        st.markdown(
            f"Out-of-time RMSE **{xgb.get('rmse', 0):.4f}** vs league-average "
            f"**{avg.get('rmse', 0):.4f}**; calibration ECE "
            f"**{ev.get('calibration_test', {}).get('ece', 0):.4f}**."
        )

st.divider()
st.markdown(
    """
    **Navigate:** use the sidebar pages - *Match Explorer* (per-match tactical
    profile + recommendations), *Recommendations* (full ranked table with
    uncertainty), *Validation* (temporal split, calibration, error analysis,
    ablation), *Model Card*, and *Human-in-the-Loop* (leave coach/analyst feedback).
    """
)
