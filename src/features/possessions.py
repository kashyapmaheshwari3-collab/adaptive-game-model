"""Possession building: aggregate events into possessions with outcome labels.

Phase 1 vocabulary - possession outcome scale (0-5):

    0 = possession lost before progression
    1 = retained but no meaningful progression
    2 = entered an advanced zone
    3 = created a dangerous action
    4 = created a shot
    5 = created a high-value shot

Expected possession value (EPV) is defined in goal-probability units:

    EPV = E[goal contribution from this possession]
          - expected transition exposure after losing the ball

It is documented in ``docs/methodology.md`` and is the target the value model
learns to predict.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import (
    DANGEROUS_ACTION_XG,
    FINAL_THIRD_LINE,
    HIGH_VALUE_SHOT_XG,
    MIDFIELD_LINE,
)

_ACTION_TYPES = [
    "pass",
    "shot",
    "carry",
    "dribble",
    "clearance",
    "duel",
    "interception",
    "ball_recovery",
    "miscontrol",
    "50_50",
    "block",
]

_TURNOVER_TYPES = ["duel", "miscontrol", "interception", "clearance", "50_50"]


def _possession_seconds(grp: pd.DataFrame) -> float:
    secs = grp["event_seconds"].dropna()
    if len(secs) >= 2:
        return float(max(secs.max() - secs.min(), 1.0))
    return float(len(grp)) * 6.0  # fallback proxy


def possession_outcome(
    n_passes: int,
    net_progress: float,
    end_x: float,
    has_shot: bool,
    max_shot_xg: float,
    has_dangerous_action: bool,
) -> int:
    """Map possession facts to the 0-5 outcome scale."""
    if has_shot and max_shot_xg >= HIGH_VALUE_SHOT_XG:
        return 5
    if has_shot:
        return 4
    if has_dangerous_action:
        return 3
    if end_x >= FINAL_THIRD_LINE:
        return 2
    if n_passes <= 3 and net_progress < 20:
        return 0
    return 1


def expected_possession_value(row: pd.Series) -> float:
    """EPV proxy in goal-probability units per possession."""
    level = int(row["outcome_level"])
    if level >= 4:
        value = float(row["max_shot_xg"] or 0.0)
    elif level == 3:
        value = DANGEROUS_ACTION_XG + 0.04 * max(
            0.0, (float(row["end_x"]) - FINAL_THIRD_LINE) / 40.0
        )
    elif level == 2:
        value = 0.03
    elif level == 1:
        value = 0.005
    else:
        value = 0.0
    # expected transition exposure: losing the ball in advanced areas costs goals
    exposure = 0.0
    if level <= 1 and not np.isnan(row.get("end_x", np.nan)):
        end_x = float(row["end_x"])
        if end_x > MIDFIELD_LINE:
            exposure = 0.02 * (end_x - MIDFIELD_LINE) / 60.0
    return round(max(0.0, value - exposure), 5)


def build_possessions(events: pd.DataFrame) -> pd.DataFrame:
    """Build one row per (match_id, possession, possession_team)."""
    df = events[events["type"].isin(_ACTION_TYPES) | (events["type"] == "ball_recovery")].copy()
    if df.empty:
        return pd.DataFrame()

    rows = []
    for (match_id, possession, team), grp in df.groupby(
        ["match_id", "possession", "possession_team"], sort=False
    ):
        first = grp.iloc[0]
        last = grp.iloc[-1]
        passes = grp[grp["type"] == "pass"]
        shots = grp[grp["type"] == "shot"]
        in_box_col = grp["in_box"] if "in_box" in grp.columns else pd.Series(False, index=grp.index)
        dangerous = grp[
            (grp["pass_shot_assist"] == True) | grp["pass_assisted_shot"].notna() | in_box_col  # noqa: E712
        ]
        end_x = last["end_x"] if pd.notna(last["end_x"]) else last["x"]
        end_y = last["end_y"] if pd.notna(last["end_y"]) else last["y"]
        max_shot_xg = shots["shot_xg"].max() if len(shots) else 0.0
        n_passes = len(passes)
        net_progress = float(end_x) - float(first["x"])
        has_shot = len(shots) > 0
        has_dangerous = len(dangerous) > 0
        sd = first.get("score_diff", 0)
        score_diff = int(sd) if pd.notna(sd) else 0

        level = possession_outcome(
            n_passes,
            net_progress,
            float(end_x),
            has_shot,
            float(max_shot_xg or 0.0),
            has_dangerous,
        )

        # pressure proxy: fraction of attacking actions taken under pressure
        pressured = grp["under_pressure"].sum() if "under_pressure" in grp else 0
        opp_press_events = int(grp["counterpress"].sum() if "counterpress" in grp else 0)
        row = {
            "match_id": match_id,
            "possession": possession,
            "possession_team": team,
            "start_x": float(first["x"]),
            "start_y": float(first["y"]),
            "end_x": float(end_x),
            "end_y": float(end_y),
            "n_actions": int(len(grp)),
            "n_passes": int(n_passes),
            "n_shots": int(len(shots)),
            "duration_seconds": _possession_seconds(grp),
            "net_progress_x": net_progress,
            "crossed_midfield": bool(end_x >= MIDFIELD_LINE),
            "entered_final_third": bool(end_x >= FINAL_THIRD_LINE),
            "max_shot_xg": float(max_shot_xg or 0.0),
            "pressure_proxy": float(pressured / max(len(grp), 1)),
            "counterpress_flags": opp_press_events,
            "play_pattern": first.get("play_pattern"),
            "recovery_type": first["type"],
            "first_pressure": int(bool(first.get("under_pressure", False))),
            "minute": int(first["minute"]),
            "period": int(first["period"]),
            "is_home": bool(first.get("is_home", False)),
            "score_diff": score_diff,
            "opponent_formation": first.get("opponent_formation"),
            "team_formation": first.get("team_formation"),
            "team": first["team"],
            "opponent_team": first.get("opponent_team"),
            "outcome_level": level,
        }
        row["epv"] = expected_possession_value(pd.Series(row))
        row["switch_passes"] = int(passes["pass_switch"].sum()) if "pass_switch" in passes else 0
        rows.append(row)

    poss = pd.DataFrame(rows)
    if poss.empty:
        return poss
    poss = poss.sort_values(["match_id", "possession"]).reset_index(drop=True)
    # drop opponent-team duplicates (possession id is unique per team sequence)
    poss = poss.drop_duplicates(subset=["match_id", "possession"])
    return poss
