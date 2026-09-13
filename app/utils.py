"""Shared helpers for the Streamlit app: cached loading of pipeline artefacts."""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import PROCESSED_DIR  # noqa: E402


@lru_cache(maxsize=8)
def _read_json(name: str) -> dict:
    return json.loads((PROCESSED_DIR / name).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_possessions() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "possessions.parquet")


@st.cache_data(show_spinner=False)
def load_matches() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "matches.parquet")


@st.cache_data(show_spinner=False)
def load_events() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "events.parquet")


@st.cache_data(show_spinner=False)
def load_recommendations() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / "recommendations.csv")


@st.cache_data(show_spinner=False)
def load_state_profiles() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / "state_profiles.csv")


def load_evaluation() -> dict:
    return _read_json("evaluation_report.json")


def load_error_analysis() -> dict:
    return _read_json("error_analysis.json")


def load_ablation() -> dict:
    return _read_json("ablation_report.json")


def load_model_card() -> dict:
    return _read_json("model_card.json")


def load_validation() -> dict:
    return _read_json("validation_report.json")


def load_decisions() -> dict:
    return _read_json("decision_outputs.json")


def load_artefacts() -> dict:
    """Convenience loader returning every artefact."""
    return {
        "possessions": load_possessions(),
        "matches": load_matches(),
        "events": load_events(),
        "recommendations": load_recommendations(),
        "state_profiles": load_state_profiles(),
        "evaluation": load_evaluation(),
        "error_analysis": load_error_analysis(),
        "ablation": load_ablation(),
        "model_card": load_model_card(),
        "validation": load_validation(),
        "decisions": load_decisions(),
    }
