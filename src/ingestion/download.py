"""Download StatsBomb Open Data into ``data/raw/statsbomb``.

StatsBomb Open Data is published on GitHub under CC BY-NC-SA 4.0:
https://github.com/statsbomb/open-data

This script fetches the *matches.json* manifest for a competition/season and the
per-match *events.json* files for a configurable subset of matches, so a
portfolio project stays lean while remaining fully reproducible.

Usage::

    python -m src.ingestion.download --competition 11 --season 27 \\
        --max-matches 40 --only-teams "Barcelona,Real Madrid,Atlético Madrid"

The ``--only-teams`` filter selects matches where either side matches a fuzzy
team name, which is how the demo dataset (La Liga 2015/16, elite clubs) is
built.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests

from src.config import RAW_SB_DIR

BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
MATCHES_URL = f"{BASE}/matches/{{competition}}/{{season}}.json"
EVENTS_URL = f"{BASE}/events/{{match_id}}.json"
THREE60_URL = f"{BASE}/three-sixty/{{match_id}}.json"

TIMEOUT = 60


def _fetch(url: str) -> dict | list:
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def download_match_events(match_id: int, out_dir: Path, with_three60: bool = False) -> list[Path]:
    """Download events (and optionally 360 frames) for one match."""
    written: list[Path] = []
    events = _fetch(EVENTS_URL.format(match_id=match_id))
    ev_file = out_dir / "events" / f"{match_id}.json"
    ev_file.write_text(json.dumps(events), encoding="utf-8")
    written.append(ev_file)
    if with_three60:
        try:
            frames = _fetch(THREE60_URL.format(match_id=match_id))
            t60 = out_dir / "three-sixty" / f"{match_id}.json"
            t60.write_text(json.dumps(frames), encoding="utf-8")
            written.append(t60)
        except requests.HTTPError:
            pass  # not every match has 360 data; skip silently
    return written


def select_matches(matches: list[dict], max_matches: int | None, only_teams: list[str]) -> list[dict]:
    """Filter matches by team names (fuzzy) and cap the total count."""
    if only_teams:
        hits: list[dict] = []
        for m in matches:
            home = m.get("home_team", {}).get("home_team_name", "")
            away = m.get("away_team", {}).get("away_team_name", "")
            if any(t.lower() in home.lower() or t.lower() in away.lower() for t in only_teams):
                hits.append(m)
        matches = hits
    matches = sorted(matches, key=lambda m: (m.get("match_date", ""), m.get("match_id", 0)))
    if max_matches:
        matches = matches[:max_matches]
    return matches


def download(
    competition: int,
    season: int,
    max_matches: int | None = None,
    only_teams: list[str] | None = None,
    with_three60: bool = False,
    quiet: bool = False,
) -> dict:
    """Download a StatsBomb competition subset and write a manifest."""
    out_dir = RAW_SB_DIR / str(competition) / str(season)
    (out_dir / "events").mkdir(parents=True, exist_ok=True)
    if with_three60:
        (out_dir / "three-sixty").mkdir(parents=True, exist_ok=True)

    matches = _fetch(MATCHES_URL.format(competition=competition, season=season))
    (out_dir / "matches.json").write_text(json.dumps(matches), encoding="utf-8")
    selected = select_matches(matches, max_matches, only_teams or [])

    manifest: dict = {
        "competition_id": competition,
        "season_id": season,
        "source": "https://github.com/statsbomb/open-data",
        "license": "CC BY-NC-SA 4.0",
        "total_matches_available": len(matches),
        "matches_downloaded": len(selected),
        "matches": [],
    }
    for i, m in enumerate(selected, start=1):
        match_id = m["match_id"]
        try:
            files = download_match_events(match_id, out_dir, with_three60)
        except requests.HTTPError as exc:
            if not quiet:
                print(f"  [skip] match {match_id}: {exc}")
            continue
        manifest["matches"].append(
            {
                "match_id": match_id,
                "home_team": m.get("home_team", {}).get("home_team_name"),
                "away_team": m.get("away_team", {}).get("away_team_name"),
                "match_date": m.get("match_date"),
                "files": [str(p.relative_to(out_dir)) for p in files],
            }
        )
        if not quiet:
            print(f"  [{i}/{len(selected)}] {match_id} downloaded")
        time.sleep(0.15)  # be polite to the public mirror

    manifest_file = out_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if not quiet:
        print(f"Wrote {manifest_file} ({len(manifest['matches'])} matches)")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Download StatsBomb Open Data subset")
    parser.add_argument("--competition", type=int, default=11)
    parser.add_argument("--season", type=int, default=27)
    parser.add_argument("--max-matches", type=int, default=None)
    parser.add_argument("--only-teams", type=str, default="")
    parser.add_argument("--with-three60", action="store_true")
    args = parser.parse_args()
    only_teams = [t.strip() for t in args.only_teams.split(",") if t.strip()] or None
    download(args.competition, args.season, args.max_matches, only_teams, args.with_three60)


if __name__ == "__main__":
    main()
