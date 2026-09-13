"""Human-in-the-loop - analyst comments, scout override, coach feedback."""

import json
import time

import pandas as pd
import streamlit as st

try:
    from app.utils import load_artefacts
except ModuleNotFoundError:
    from utils import load_artefacts
from src.config import HITL_LOG

st.set_page_config(page_title="Human-in-the-Loop", page_icon="🧠", layout="wide")
st.title("Human-in-the-Loop")
st.caption("The engine is a decision aid - analysts and coaches own the decision.")

a = load_artefacts()
recs = a["recommendations"]

HITL_LOG.parent.mkdir(parents=True, exist_ok=True)


def _load_hitl() -> list[dict]:
    if HITL_LOG.exists():
        return json.loads(HITL_LOG.read_text(encoding="utf-8"))
    return []


def _save_hitl(entries: list[dict]) -> None:
    HITL_LOG.write_text(json.dumps(entries, indent=2), encoding="utf-8")


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
    entries = _load_hitl()
    entries.append(
        {
            "ts": time.time(),
            "iso": pd.Timestamp.now(tz="UTC").isoformat(),
            "recommendation": pick,
            "role": role,
            "type": feedback_type,
            "text": text,
        }
    )
    _save_hitl(entries)
    st.success("Feedback saved to data/processed/hitl_log.json")

st.subheader("Existing feedback")
entries = _load_hitl()
if entries:
    st.dataframe(pd.DataFrame(entries), use_container_width=True)
else:
    st.info("No feedback recorded yet.")
