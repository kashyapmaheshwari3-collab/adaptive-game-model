"""Test suite for the Adaptive Game Model.

Fast tests use the deterministic synthetic generator (no network). Slow tests
(marked ``slow``) use real StatsBomb data when available.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.config import (
    ADJUSTMENTS,
    DEFAULT_RANDOM_STATE,
    PITCH_LENGTH,
    PITCH_WIDTH,
    TACTICAL_STATES,
)
from src.evaluation import split_possessions, temporal_split
from src.features import (
    build_possessions,
    elo_features,
    enrich_events,
    label_strategies,
)
from src.models.adjustments import STRATEGY_COLS, estimate_adjustment_values
from src.models.tactical_states import fit_tactical_states
from src.models.value_model import fit_value_models, predict_epv
from src.synthetic import generate_synthetic_dataset
from src.validation import run_all_checks


@pytest.fixture(scope="module")
def dataset():
    """Deterministic synthetic dataset (offline, fast)."""
    matches, events = generate_synthetic_dataset(n_matches=12, seed=DEFAULT_RANDOM_STATE)
    return matches, events


@pytest.fixture(scope="module")
def possession_frame(dataset):
    matches, events = dataset
    events = enrich_events(events, matches)
    poss = build_possessions(events)
    poss = elo_features(poss, matches)
    poss = label_strategies(poss, events)
    return poss, matches


# --------------------------------------------------------------------------- #
# Synthetic data
# --------------------------------------------------------------------------- #
class TestSyntheticData:
    def test_columns_match_schema(self, dataset):
        _, events = dataset
        required = ["match_id", "team", "type", "x", "y", "possession", "possession_team"]
        for col in required:
            assert col in events.columns, f"missing column {col}"
        assert len(events) > 1000

    def test_deterministic(self):
        a = generate_synthetic_dataset(n_matches=6, seed=7)
        b = generate_synthetic_dataset(n_matches=6, seed=7)
        pd.testing.assert_frame_equal(a[0], b[0])
        pd.testing.assert_frame_equal(a[1], b[1])

    def test_coordinates_in_pitch(self, dataset):
        _, events = dataset
        assert events["x"].between(-1, PITCH_LENGTH + 1).all()
        assert events["y"].between(-1, PITCH_WIDTH + 1).all()

    def test_player_ids_present(self, dataset):
        _, events = dataset
        on_ball = events[events["type"].isin(["pass", "shot", "carry"])]
        assert on_ball["player_id"].notna().mean() > 0.9


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
class TestValidation:
    def test_run_all_checks_passes_on_synthetic(self, dataset, possession_frame):
        matches, events = dataset
        issues = run_all_checks(events, matches)
        errors = [i for i in issues if i["severity"] == "error"]
        assert not errors, f"validation errors: {errors}"

    def test_leakage_detected(self, dataset):
        matches, events = dataset
        train = pd.DataFrame({"match_id": [matches.iloc[0]["match_id"]]})
        test = pd.DataFrame({"match_id": [matches.iloc[0]["match_id"]]})
        issues = run_all_checks(events, matches, train, test)
        leaks = [i for i in issues if i["check"] == "leakage" and i["severity"] == "error"]
        assert leaks


# --------------------------------------------------------------------------- #
# Features
# --------------------------------------------------------------------------- #
class TestPossessions:
    def test_outcome_scale_bounds(self, possession_frame):
        poss, _ = possession_frame
        assert poss["outcome_level"].between(0, 5).all()

    def test_epv_non_negative(self, possession_frame):
        poss, _ = possession_frame
        assert (poss["epv"] >= 0).all()

    def test_shot_possessions_have_high_level(self, possession_frame):
        poss, _ = possession_frame
        if (poss["n_shots"] > 0).any():
            assert (poss.loc[poss["n_shots"] > 0, "outcome_level"] >= 4).all()

    def test_strategy_columns_present(self, possession_frame):
        poss, _ = possession_frame
        for s in STRATEGY_COLS:
            assert s in poss.columns
        assert poss[STRATEGY_COLS].isin([0, 1]).all().all()


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class TestModels:
    def test_value_model_predicts(self, possession_frame):
        poss, matches = possession_frame
        train, val, test, _ = split_possessions(poss, matches, val_frac=0.25, test_frac=0.25)
        xgb, _, baselines = fit_value_models(train, random_state=DEFAULT_RANDOM_STATE)
        preds = predict_epv(xgb, test)
        assert preds.shape[0] == len(test)
        assert np.isfinite(preds).all()

    def test_tactical_states_named(self, possession_frame):
        poss, _ = possession_frame
        states, cluster_map, _, _ = fit_tactical_states(poss, n_clusters=6, random_state=DEFAULT_RANDOM_STATE)
        assert set(states.cat.categories) == set(TACTICAL_STATES)
        # every cluster maps to a *named* state from the vocabulary
        assert set(cluster_map.values()).issubset(set(TACTICAL_STATES))
        assert states.notna().all()

    def test_adjustment_estimates_have_ci(self, possession_frame):
        poss, _ = possession_frame
        poss["tactical_state"] = "opponent_low_block"
        est = estimate_adjustment_values(
            poss, n_boot=20, min_treated=3, random_state=DEFAULT_RANDOM_STATE
        )
        if not est.empty:
            assert "ci_low" in est.columns and "ci_high" in est.columns
            assert (est["ci_high"] >= est["ci_low"]).all()


# --------------------------------------------------------------------------- #
# Temporal validation
# --------------------------------------------------------------------------- #
class TestTemporal:
    def test_no_overlap(self, dataset, possession_frame):
        matches, _ = dataset
        split = temporal_split(matches, val_frac=0.2, test_frac=0.2)
        assert set(split["train"]).isdisjoint(split["val"])
        assert set(split["train"]).isdisjoint(split["test"])
        assert set(split["val"]).isdisjoint(split["test"])
