"""Human-in-the-loop - analyst comments, scout override, coach feedback."""

import time

import pandas as pd
import streamlit as st

try:
    from app.utils import load_artefacts
except ModuleNotFoundError:
    from utils import load_artefacts
try:
    from app.hitl_storage import load_feedback, save_feedback
except ModuleNotFoundError:
    from hitl_storage import load_feedback, save_feedback
from src.config import HITL_LOG

st.set_page_config(page_title="Human-in-the-Loop", page_icon="🧠", layout="wide")
st.title("Human-in-the-Loop")
st.caption("The engine is a decision aid - analysts and coaches own the decision.")

a = load_artefacts()
recs = a["recommendations"]

HITL_LOG.parent.mkdir(parents=True, exist_ok=True)


st.subheader("Add feedback to a recommendation")
if recs.empty:
    st.info("No recommendations yet - run the pipeline first.")
    st.stop()

options = [
    f"{r['tactical_state']} | {r['strategy']} | uplift {r['aipw_ate']:+.3f}"
    for _, r in recs.iterrows()
]
pick = st.selectbox("Recommendation", options)
role = st.selectbox("Your role", ["Analyst", "Coach", "Scout", "Sporting Director"])
feedback_type = st.selectbox(
    "Type",
    ["Comment", "Override", "Confidence adjustment", "Tactical assumption", "Video evidence"],
)
text = st.text_area(
    "Feedback",
    placeholder="e.g. 'In our system this adjustment works only with a left-footed CB - see clip 4:12'",
)

if st.button("Save feedback", type="primary"):
    try:
        storage = save_feedback(
            {
                "ts": time.time(),
                "iso": pd.Timestamp.now(tz="UTC").isoformat(),
                "recommendation": pick,
                "role": role,
                "type": feedback_type,
                "text": text,
            },
            HITL_LOG,
        )
        st.success(f"Feedback saved to {storage}.")
    except Exception as exc:
        st.error(f"Feedback could not be saved: {exc}")

st.subheader("Existing feedback")
try:
    entries = load_feedback(HITL_LOG)
except Exception as exc:
    entries = []
    st.error(f"Feedback could not be loaded: {exc}")
if entries:
    st.dataframe(pd.DataFrame(entries), use_container_width=True)
else:
    st.info("No feedback recorded yet.")
