"""Lightweight Elo ratings for team-strength features (a baseline component).

Elo is computed sequentially over match dates from match results and is used
only as a feature ("team strength") - never as the headline model. It makes the
scoreline- and opponent-conditioning explicit and serves as one of the
baselines in the evaluation suite.
"""

from __future__ import annotations

import pandas as pd

INIT = 1500.0
K = 32.0
HOME_ADV = 65.0


def _expected(a: float, b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((b - a) / 400.0))


def elo_ratings(matches: pd.DataFrame) -> pd.DataFrame:
    """Return one row per (match, team) with elo_before (pre-match rating)."""
    df = matches.copy()
    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
    df = df.sort_values(["match_date", "match_id"]).reset_index(drop=True)

    ratings: dict[int, float] = {}
    rows: list[dict] = []
    for _, m in df.iterrows():
        h, a = m["home_team_id"], m["away_team_id"]
        r_h = ratings.get(h, INIT)
        r_a = ratings.get(a, INIT)
        rows.append(
            {"match_id": m["match_id"], "team_id": h, "elo_before": r_h, "opponent_elo": r_a}
        )
        rows.append(
            {"match_id": m["match_id"], "team_id": a, "elo_before": r_a, "opponent_elo": r_h}
        )

        e_h = _expected(r_h + HOME_ADV, r_a)
        e_a = 1.0 - e_h
        if m["home_score"] > m["away_score"]:
            s_h, s_a = 1.0, 0.0
        elif m["home_score"] < m["away_score"]:
            s_h, s_a = 0.0, 1.0
        else:
            s_h, s_a = 0.5, 0.5
        ratings[h] = r_h + K * (s_h - e_h)
        ratings[a] = r_a + K * (s_a - e_a)
    return pd.DataFrame(rows)


def elo_features(possessions: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """Join Elo ratings (pre-match) onto possession rows."""
    elo = elo_ratings(matches)
    by_team = elo.set_index(["match_id", "team_id"])["elo_before"].to_dict()
    by_opp = elo.set_index(["match_id", "team_id"])["opponent_elo"].to_dict()

    df = possessions.copy()
    # possession_team is a name; map back to team_id via matches
    name_to_id = {}
    for _, m in matches.iterrows():
        name_to_id[(m["match_id"], m["home_team"])] = m["home_team_id"]
        name_to_id[(m["match_id"], m["away_team"])] = m["away_team_id"]
        name_to_id[(m["match_id"], m["home_team_id"])] = m["home_team_id"]

    df["team_id"] = df.apply(
        lambda r: name_to_id.get((r["match_id"], r["possession_team"])), axis=1
    )
    df["opponent_id"] = df.apply(
        lambda r: name_to_id.get((r["match_id"], r["opponent_team"])), axis=1
    )
    df["team_elo"] = df.apply(lambda r: by_team.get((r["match_id"], r["team_id"]), INIT), axis=1)
    df["opp_elo"] = df.apply(lambda r: by_opp.get((r["match_id"], r["opponent_id"]), INIT), axis=1)
    df["elo_diff"] = df["team_elo"] - df["opp_elo"]
    return df
