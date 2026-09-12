"""Model Card & methodology - transparency for technical audiences."""

import json

import streamlit as st

from app.utils import load_artefacts
from src.config import PROCESSED_DIR

st.set_page_config(page_title="Model Card", page_icon="📋", layout="wide")
st.title("Model Card & Methodology")

a = load_artefacts()
mc = a["model_card"]

c1, c2 = st.columns(2)
with c1:
    st.subheader("Model")
    st.json(mc.get("value_model"))
with c2:
    st.subheader("Task")
    st.write(mc.get("task"))

st.subheader("Validation & metrics")
st.json(mc.get("metrics"))
st.json(mc.get("calibration"))

st.subheader("Known limitations")
for lim in mc.get("known_limitations", []):
    st.markdown(f"- {lim}")

st.subheader("Data provenance")
st.json(mc.get("data"))

st.subheader("Methodology & data dictionary")
md = (PROCESSED_DIR.parent / "docs").resolve()
st.markdown(
    "See the repository docs: `docs/methodology.md`, `docs/data_dictionary.md`, "
    "`docs/model_card.md`. Machine-readable model card: `data/processed/model_card.json`."
)
