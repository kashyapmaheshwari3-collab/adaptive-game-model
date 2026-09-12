"""Reproducibility manifest helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from src.config import PROCESSED_DIR


def file_sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def build_manifest(
    competition: int,
    season: int,
    matches: pd.DataFrame,
    events: pd.DataFrame,
    provenance: dict | None = None,
) -> dict:
    """Build a reproducibility manifest for the dataset."""
    return {
        "competition_id": competition,
        "season_id": season,
        "source": "https://github.com/statsbomb/open-data",
        "license": "CC BY-NC-SA 4.0 (StatsBomb Open Data)",
        "n_matches": int(matches["match_id"].nunique()),
        "n_events": int(len(events)),
        "n_teams": int(matches["home_team_id"].nunique()),
        "match_date_range": [
            str(matches["match_date"].min()),
            str(matches["match_date"].max()),
        ],
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "provenance": provenance or {},
    }


def write_manifest(manifest: dict) -> Path:
    out = PROCESSED_DIR / "data_manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out
