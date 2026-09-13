"""Validation report: aggregates checks into a pass/fail gate + artefacts."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.config import PROCESSED_DIR
from src.validation.checks import run_all_checks

SEVERITY_RANK = {"info": 0, "warning": 1, "error": 2}


def validation_report(
    events: pd.DataFrame,
    matches: pd.DataFrame,
    train: pd.DataFrame | None = None,
    test: pd.DataFrame | None = None,
) -> dict:
    """Run checks and return a structured report."""
    issues = run_all_checks(events, matches, train, test)
    n_errors = sum(1 for i in issues if i["severity"] == "error")
    n_warnings = sum(1 for i in issues if i["severity"] == "warning")
    return {
        "status": "PASS" if n_errors == 0 else "FAIL",
        "n_errors": n_errors,
        "n_warnings": n_warnings,
        "n_checks": len(issues),
        "issues": issues,
        "rows_in": int(len(events)),
        "matches": int(matches["match_id"].nunique()) if "match_id" in matches else 0,
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
    }


def save_validation_report(
    report: dict, out: Path = PROCESSED_DIR / "validation_report.json"
) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out
