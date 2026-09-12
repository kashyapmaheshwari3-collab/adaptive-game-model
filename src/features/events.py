"""Event-level enrichment: scoreline context, home/away, zones, opponent formation."""

from __future__ import annotations

import pandas as pd

from src.config import (
    CENTRAL_BAND,
    DEFENSIVE_THIRD_LINE,
    FINAL_THIRD_LINE,
    HALF_SPACE_LEFT,
    HALF_SPACE_RIGHT,
    MIDFIELD_LINE,
    TOUCHLINE_BAND,
)


def zone_x(x: float) -> str:
    if pd.isna(x):
        return "unknown"
    if x < DEFENSIVE_THIRD_LINE:
        return "defensive_third"
    if x < MIDFIELD_LINE:
        return "middle_third"
    if x < FINAL_THIRD_LINE:
        return "advanced_third"
    return "final_third"


def zone_y(y: float) -> str:
    if pd.isna(y):
        return "unknown"
    if y < HALF_SPACE_LEFT[0] or y > HALF_SPACE_RIGHT[1]:
        return "wide"
    if HALF_SPACE_LEFT[0] <= y < HALF_SPACE_LEFT[1] or HALF_SPACE_RIGHT[0] <= y < HALF_SPACE_RIGHT[1]:
        return "half_space"
    return "central"


def _parse_seconds(ts) -> float | None:
    if pd.isna(ts):
        return None
    parts = str(ts).split(":")
    try:
        return float(parts[0]) * 60 + float(parts[1])
    except (ValueError, IndexError):
        return None


def enrich_events(events: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """Add context columns to the tidy event frame.

    Adds: scoreline at event time, home/away, opponent team + formation,
    zone labels, possession phase flags, event seconds.
    """
    df = events.copy()
    df["event_seconds"] = df["timestamp"].map(_parse_seconds)

    team_of = {}
    for _, m in matches.iterrows():
        # (team_id) -> (home_team, opponent_team, own_form, opp_form, is_home, opponent_id)
        team_of[(m["match_id"], m["home_team_id"])] = (
            m["home_team"], m["away_team"], m["home_formation"], m["away_formation"], True, m["away_team_id"])
        team_of[(m["match_id"], m["away_team_id"])] = (
            m["away_team"], m["home_team"], m["away_formation"], m["home_formation"], False, m["home_team_id"])

    def ctx(row):
        info = team_of.get((row["match_id"], row["team_id"]))
        if info is None:
            return pd.Series(
                [row["team"], None, None, None, None, False],
                index=["home_team", "opponent_team", "team_formation", "opponent_formation", "opponent_id", "is_home"],
            )
        home_team, opp_team, team_form, opp_form, is_home, opp_id = info
        return pd.Series(
            [home_team, opp_team, team_form, opp_form, opp_id, is_home],
            index=["home_team", "opponent_team", "team_formation", "opponent_formation", "opponent_id", "is_home"],
        )

    df[["home_team", "opponent_team", "team_formation", "opponent_formation", "opponent_id", "is_home"]] = df.apply(ctx, axis=1)

    # scoreline before the event: cumulative goals per team within the match,
    # computed with vectorised group-by cumsums (chronological event order).
    df["_event_rank"] = df.groupby("match_id").cumcount()
    df = df.sort_values(["match_id", "event_seconds", "timestamp", "_event_rank"], kind="stable")
    df["_is_goal"] = ((df["type"] == "shot") & (df["shot_outcome"] == "Goal")).astype(int)
    df["team_goals_before"] = df.groupby(["match_id", "team"])["_is_goal"].cumsum() - df["_is_goal"]
    df["opp_goals_before"] = df.groupby(["match_id", "opponent_team"])["_is_goal"].cumsum() - df["_is_goal"]
    df["score_diff"] = (
        df["team_goals_before"].fillna(0) - df["opp_goals_before"].fillna(0)
    ).astype(int)

    df["zone_x"] = df["x"].map(zone_x)
    df["zone_y"] = df["y"].map(zone_y)
    df["end_zone_x"] = df["end_x"].map(zone_x)
    df["end_zone_y"] = df["end_y"].map(zone_y)
    df["is_wide_band"] = df["y"].apply(lambda y: (not pd.isna(y)) and (y < TOUCHLINE_BAND or y > 80 - TOUCHLINE_BAND))
    df["in_box"] = (df["x"] >= 102) & (df["y"].between(18, 62))
    return df
