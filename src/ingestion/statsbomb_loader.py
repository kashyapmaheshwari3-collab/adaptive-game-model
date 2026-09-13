"""Load StatsBomb Open Data JSON into tidy pandas frames.

The tidy event frame uses one row per event with a stable column contract
(see ``docs/data_dictionary.md``). Both real StatsBomb data and the synthetic
generator produce exactly this schema, so the rest of the pipeline is
data-source agnostic.
"""

from __future__ import annotations

import json

import pandas as pd

from src.config import RAW_SB_DIR

_EVENT_COLUMNS = [
    "match_id",
    "period",
    "minute",
    "second",
    "timestamp",
    "team_id",
    "team",
    "player_id",
    "player",
    "type",
    "possession",
    "possession_team",
    "play_pattern",
    "x",
    "y",
    "end_x",
    "end_y",
    "under_pressure",
    "counterpress",
    "shot_xg",
    "shot_outcome",
    "shot_type",
    "pass_length",
    "pass_angle",
    "pass_recipient",
    "pass_height",
    "pass_technique",
    "pass_switch",
    "pass_assisted_shot",
    "pass_shot_assist",
    "pass_goal_assist",
    "duel_type",
    "duel_outcome",
    "ball_recovery",
    "interception",
    "clearance",
    "dribble_outcome",
    "carry_end_x",
    "carry_end_y",
    "related_events",
    "formation",
]

_TYPE_ALIASES = {
    "Ball Recovery": "ball_recovery",
    "Ball Receipt*": "ball_receipt",
    "Carry": "carry",
}


def _team_name(team_dict: dict | None) -> str | None:
    return (team_dict or {}).get("name")


def _player_name(player_dict: dict | None) -> str | None:
    return (player_dict or {}).get("name")


def _norm_type(type_dict: dict | None) -> str:
    name = (type_dict or {}).get("name", "Unknown")
    return _TYPE_ALIASES.get(name, name.lower().replace(" ", "_"))


def parse_event(ev: dict, match_id: int, formation: int | None) -> dict:
    """Flatten one StatsBomb event into the tidy row contract."""
    loc = ev.get("location") or [None, None]
    end_loc = ev.get("end_location") or [None, None]
    pass_data = ev.get("pass") or {}
    shot_data = ev.get("shot") or {}
    duel_data = ev.get("duel") or {}
    carry = ev.get("carry") or {}

    return {
        "match_id": match_id,
        "period": ev.get("period"),
        "minute": ev.get("minute"),
        "second": ev.get("second"),
        "timestamp": ev.get("timestamp"),
        "team_id": ev.get("team", {}).get("id"),
        "team": _team_name(ev.get("team")),
        "player_id": ev.get("player", {}).get("id") if ev.get("player") else None,
        "player": _player_name(ev.get("player")),
        "type": _norm_type(ev.get("type")),
        "possession": ev.get("possession"),
        "possession_team": _team_name(ev.get("possession_team")),
        "play_pattern": (ev.get("play_pattern") or {}).get("name"),
        "x": loc[0],
        "y": loc[1],
        "end_x": end_loc[0] if end_loc else None,
        "end_y": end_loc[1] if end_loc else None,
        "under_pressure": bool(ev.get("under_pressure", False)),
        "counterpress": bool(ev.get("counterpress", False)),
        "shot_xg": shot_data.get("statsbomb_xg"),
        "shot_outcome": (shot_data.get("outcome") or {}).get("name"),
        "shot_type": (shot_data.get("body_part") or {}).get("name"),
        "pass_length": pass_data.get("length"),
        "pass_angle": pass_data.get("angle"),
        "pass_recipient": _player_name(pass_data.get("recipient")),
        "pass_height": (pass_data.get("height") or {}).get("name"),
        "pass_technique": (pass_data.get("technique") or {}).get("name"),
        "pass_switch": bool(pass_data.get("switch", False)),
        "pass_assisted_shot": pass_data.get("assisted_shot_id"),
        "pass_shot_assist": bool(pass_data.get("shot_assist", False)),
        "pass_goal_assist": bool(pass_data.get("goal_assist", False)),
        "duel_type": (duel_data.get("type") or {}).get("name"),
        "duel_outcome": (duel_data.get("outcome") or {}).get("name"),
        "ball_recovery": bool(ev.get("ball_recovery", False)),
        "interception": ev.get("type", {}).get("name") == "Interception",
        "clearance": ev.get("type", {}).get("name") == "Clearance",
        "dribble_outcome": (ev.get("dribble") or {}).get("outcome", {}).get("name"),
        "carry_end_x": (carry.get("end_location") or [None, None])[0],
        "carry_end_y": (carry.get("end_location") or [None, None])[1],
        "related_events": ev.get("related_events"),
        "formation": formation,
    }


def load_matches_frame(competition: int, season: int) -> pd.DataFrame:
    """Load the matches manifest as a frame with teams, dates, results, lineups."""
    path = RAW_SB_DIR / str(competition) / str(season) / "matches.json"
    if not path.exists():
        raise FileNotFoundError(
            f"matches manifest not found: {path}. Run `python -m src.ingestion.download` first."
        )
    matches = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for m in matches:
        home = m.get("home_team", {})
        away = m.get("away_team", {})
        lineup_home = next(
            (lineup for lineup in m.get("lineups", []) if lineup.get("team_id") == home.get("id")),
            {},
        )
        lineup_away = next(
            (lineup for lineup in m.get("lineups", []) if lineup.get("team_id") == away.get("id")),
            {},
        )
        rows.append(
            {
                "match_id": m["match_id"],
                "match_date": m.get("match_date"),
                "competition": m.get("competition", {}).get("name"),
                "season": m.get("season", {}).get("season_name"),
                "home_team_id": home.get("id"),
                "home_team": home.get("home_team_name"),
                "away_team_id": away.get("id"),
                "away_team": away.get("away_team_name"),
                "home_score": m.get("home_score"),
                "away_score": m.get("away_score"),
                "home_formation": lineup_home.get("formation"),
                "away_formation": lineup_away.get("formation"),
                "stadium": (m.get("stadium") or {}).get("name"),
                "referee": (m.get("referee") or {}).get("name"),
            }
        )
    return pd.DataFrame(rows)


def load_events_frame(competition: int, season: int) -> pd.DataFrame:
    """Load all downloaded event files for a competition/season into one frame."""
    events_dir = RAW_SB_DIR / str(competition) / str(season) / "events"
    files = sorted(events_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(
            f"no event files in {events_dir}. Run `python -m src.ingestion.download` first."
        )
    # formations come from the matches manifest
    matches = load_matches_frame(competition, season)
    formation_by_team = {}
    for _, row in matches.iterrows():
        formation_by_team[(row["match_id"], row["home_team_id"])] = row["home_formation"]
        formation_by_team[(row["match_id"], row["away_team_id"])] = row["away_formation"]

    frames = []
    for f in files:
        match_id = int(f.stem)
        events = json.loads(f.read_text(encoding="utf-8"))
        rows = [parse_event(ev, match_id, None) for ev in events]
        df = pd.DataFrame(rows, columns=_EVENT_COLUMNS)
        df["formation"] = df.apply(
            lambda r: formation_by_team.get((r["match_id"], r["team_id"])), axis=1
        )
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=_EVENT_COLUMNS)
