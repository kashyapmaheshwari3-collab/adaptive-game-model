"""Validation package - automated data-quality checks (Phase: validation).

Elite clubs need systems that remain trustworthy when data sources change.
These checks run on every pipeline execution and gate the downstream stages:

- duplicate events
- impossible coordinates
- missing player identifiers
- invalid timestamps / negative durations
- team-name inconsistencies
- competition mismatches
- outlier values (pass lengths, xG)
- leakage between train and test sets
"""

from .checks import (
    check_competition_match,
    check_duplicate_events,
    check_impossible_coordinates,
    check_invalid_timestamps,
    check_leakage,
    check_missing_player_ids,
    check_outliers,
    check_team_name_consistency,
    run_all_checks,
)
from .report import save_validation_report, validation_report

__all__ = [
    "run_all_checks",
    "check_duplicate_events",
    "check_impossible_coordinates",
    "check_missing_player_ids",
    "check_invalid_timestamps",
    "check_team_name_consistency",
    "check_competition_match",
    "check_outliers",
    "check_leakage",
    "validation_report",
    "save_validation_report",
]
