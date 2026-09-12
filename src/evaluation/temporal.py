"""Temporal validation (component 4).

Future matches are the test set. Random train/test splits produce misleadingly
good football models because actions from the same teams, seasons and matches
are highly correlated - so the split is done at match level, chronologically,
and the leakage check re-asserts that no match appears in two splits.
"""

from __future__ import annotations

import pandas as pd


def temporal_split(
    matches: pd.DataFrame,
    val_frac: float = 0.2,
    test_frac: float = 0.2,
) -> dict[str, list[int]]:
    """Chronological match-level split -> {'train': [...], 'val': [...], 'test': [...]}."""
    df = matches.copy()
    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
    df = df.sort_values(["match_date", "match_id"]).reset_index(drop=True)
    n = len(df)
    n_test = int(round(n * test_frac))
    n_val = int(round(n * val_frac))
    n_train = n - n_val - n_test
    if n_train <= 0:
        raise ValueError("Not enough matches for a temporal split (train set empty)")
    train = df.iloc[:n_train]["match_id"].tolist()
    val = df.iloc[n_train : n_train + n_val]["match_id"].tolist()
    test = df.iloc[n_train + n_val :]["match_id"].tolist()
    return {"train": train, "val": val, "test": test}


def split_possessions(
    possessions: pd.DataFrame,
    matches: pd.DataFrame,
    val_frac: float = 0.2,
    test_frac: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Split possessions by chronological match groups."""
    split = temporal_split(matches, val_frac, test_frac)
    train = possessions[possessions["match_id"].isin(split["train"])].copy()
    val = possessions[possessions["match_id"].isin(split["val"])].copy()
    test = possessions[possessions["match_id"].isin(split["test"])].copy()
    report = {k: len(v) for k, v in split.items()}
    report["n_possessions"] = {
        "train": len(train), "val": len(val), "test": len(test),
    }
    return train, val, test, report
