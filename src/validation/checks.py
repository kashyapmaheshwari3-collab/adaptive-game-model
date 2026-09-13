"""Automated data-quality checks.

Every check returns a list of ``dict`` issues with keys:
``check``, ``severity`` ("error" | "warning"), ``count``, ``message``.
"""

from __future__ import annotations

import pandas as pd

from src.config import PITCH_LENGTH, PITCH_WIDTH


def _issue(check: str, severity: str, count: int, message: str) -> dict:
    return {"check": check, "severity": severity, "count": int(count), "message": message}


def check_duplicate_events(events: pd.DataFrame) -> list[dict]:
    """Exact duplicate event rows (every field identical) should not exist."""
    cols = [
        c
        for c in events.columns
        if events[c].map(lambda v: isinstance(v, (list, dict))).any() is False
    ]
    dup = events[cols].duplicated(keep=False)
    n = int(dup.sum())
    if n:
        return [_issue("duplicate_events", "error", n, f"{n} exact duplicate event rows detected")]
    return [_issue("duplicate_events", "info", 0, "No duplicate events")]


def check_impossible_coordinates(events: pd.DataFrame) -> list[dict]:
    """Coordinates must lie within the pitch (with small tolerance)."""
    issues = []
    for col_x, col_y in [("x", "y"), ("end_x", "end_y")]:
        if col_x not in events.columns:
            continue
        bad = events[
            (events[col_x].notna())
            & (
                (events[col_x] < -1)
                | (events[col_x] > PITCH_LENGTH + 1)
                | (events[col_y] < -1)
                | (events[col_y] > PITCH_WIDTH + 1)
            )
        ]
        if len(bad):
            issues.append(
                _issue(
                    "impossible_coordinates",
                    "error",
                    len(bad),
                    f"{len(bad)} events with coordinates outside pitch ({col_x},{col_y})",
                )
            )
    if not issues:
        issues.append(_issue("impossible_coordinates", "info", 0, "All coordinates within pitch"))
    return issues


def check_missing_player_ids(events: pd.DataFrame) -> list[dict]:
    """Actions with on-ball events should carry player identifiers."""
    on_ball = events[
        events["type"].isin(
            [
                "pass",
                "shot",
                "carry",
                "dribble",
                "ball_recovery",
                "interception",
                "clearance",
                "duel",
            ]
        )
    ]
    if not len(on_ball):
        return [_issue("missing_player_ids", "info", 0, "No on-ball events to check")]
    missing = on_ball["player_id"].isna().sum()
    ratio = missing / len(on_ball)
    sev = "error" if ratio > 0.10 else ("warning" if ratio > 0.05 else "info")
    return [
        _issue(
            "missing_player_ids",
            sev,
            missing,
            f"{missing}/{len(on_ball)} on-ball events lack player_id ({ratio:.1%})",
        )
    ]


def check_invalid_timestamps(events: pd.DataFrame) -> list[dict]:
    """Minutes must be in [0, 130] and seconds in [0, 60)."""
    issues = []
    bad_min = int(((events["minute"] < 0) | (events["minute"] > 130)).sum())
    bad_sec = int(((events["second"] < 0) | (events["second"] >= 60)).sum())
    if bad_min:
        issues.append(
            _issue(
                "invalid_timestamps", "error", bad_min, f"{bad_min} events with out-of-range minute"
            )
        )
    if bad_sec:
        issues.append(
            _issue(
                "invalid_timestamps", "error", bad_sec, f"{bad_sec} events with out-of-range second"
            )
        )
    if not issues:
        issues.append(_issue("invalid_timestamps", "info", 0, "All timestamps valid"))
    return issues


def check_team_name_consistency(events: pd.DataFrame, matches: pd.DataFrame) -> list[dict]:
    """Event team names must appear in the match manifest."""
    known = set(matches["home_team"]).union(set(matches["away_team"]))
    unknown = set(events["team"].dropna().unique()) - known
    if unknown:
        return [
            _issue(
                "team_name_consistency",
                "error",
                len(unknown),
                f"Event teams not in manifest: {sorted(unknown)[:5]}",
            )
        ]
    return [_issue("team_name_consistency", "info", 0, "Team names consistent with manifest")]


def check_competition_match(events: pd.DataFrame, matches: pd.DataFrame) -> list[dict]:
    """Every event must belong to a match present in the manifest."""
    missing = set(events["match_id"].unique()) - set(matches["match_id"].unique())
    if missing:
        return [
            _issue(
                "competition_mismatch",
                "error",
                len(missing),
                f"Events reference unknown matches: {sorted(missing)[:5]}",
            )
        ]
    return [_issue("competition_mismatch", "info", 0, "All events map to manifest matches")]


def check_outliers(events: pd.DataFrame) -> list[dict]:
    """Flag physical outliers (pass length > 90m, xG outside [0, 1])."""
    issues = []
    if "pass_length" in events.columns:
        long = int((events["pass_length"] > 90).sum())
        if long:
            issues.append(_issue("outliers", "warning", long, f"{long} passes longer than 90m"))
    if "shot_xg" in events.columns:
        bad_xg = int(((events["shot_xg"] < 0) | (events["shot_xg"] > 1)).sum())
        if bad_xg:
            issues.append(
                _issue("outliers", "error", bad_xg, f"{bad_xg} shots with xG outside [0,1]")
            )
    if not issues:
        issues.append(_issue("outliers", "info", 0, "No outlier values flagged"))
    return issues


def check_leakage(train: pd.DataFrame, test: pd.DataFrame) -> list[dict]:
    """No match (and therefore no action) may appear in both train and test."""
    train_matches = set(train["match_id"].unique()) if "match_id" in train.columns else set()
    test_matches = set(test["match_id"].unique()) if "match_id" in test.columns else set()
    overlap = train_matches & test_matches
    if overlap:
        return [
            _issue(
                "leakage",
                "error",
                len(overlap),
                f"{len(overlap)} matches appear in both train and test: {sorted(overlap)[:5]}",
            )
        ]
    return [_issue("leakage", "info", 0, "No match-level leakage between train and test")]


def run_all_checks(
    events: pd.DataFrame,
    matches: pd.DataFrame,
    train: pd.DataFrame | None = None,
    test: pd.DataFrame | None = None,
) -> list[dict]:
    """Run the full validation battery and return all issues."""
    issues: list[dict] = []
    issues += check_duplicate_events(events)
    issues += check_impossible_coordinates(events)
    issues += check_missing_player_ids(events)
    issues += check_invalid_timestamps(events)
    issues += check_team_name_consistency(events, matches)
    issues += check_competition_match(events, matches)
    issues += check_outliers(events)
    if train is not None and test is not None:
        issues += check_leakage(train, test)
    return issues
