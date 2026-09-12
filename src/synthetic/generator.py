"""Deterministic synthetic event-data generator (same schema as StatsBomb)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import PITCH_LENGTH, PITCH_WIDTH

_EVENT_COLUMNS = [
    "match_id", "period", "minute", "second", "timestamp", "team_id", "team",
    "player_id", "player", "type", "possession", "possession_team", "play_pattern",
    "x", "y", "end_x", "end_y", "under_pressure", "counterpress", "shot_xg",
    "shot_outcome", "shot_type", "pass_length", "pass_angle", "pass_recipient",
    "pass_height", "pass_technique", "pass_switch", "pass_assisted_shot",
    "pass_shot_assist", "pass_goal_assist", "duel_type", "duel_outcome",
    "ball_recovery", "interception", "clearance", "dribble_outcome",
    "carry_end_x", "carry_end_y", "related_events", "formation",
]

TEAMS = [
    ("CF Real Blanco", 1750, 433), ("Atletico Verde", 1730, 442),
    ("FC Azul Marino", 1710, 433), ("Sevilla Roja", 1690, 4231),
    ("Valencia Naranja", 1660, 433), ("Betis Verdiblanco", 1630, 442),
    ("Villarreal Amarillo", 1600, 352), ("Sociedad Txuri", 1570, 433),
    ("Celta Celeste", 1540, 4231), ("Getafe Azulon", 1510, 442),
]

RECOVERY_TYPES = ["interception", "ball_recovery", "clearance", "goal_kick", "throw_in", "kick_off"]
PLAY_PATTERNS = ["regular_play", "counterattack", "from_throw_in", "from_corner", "from_kick_off", "from_goal_kick"]
SHOT_BODY = ["Right Foot", "Left Foot", "Head", "Other"]
SHOT_OUTCOMES = ["Goal", "Saved", "Off T", "Blocked", "Wayward", "Post"]


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _schedule(team_ids: list[int], n_matches: int) -> list[tuple[int, int, int]]:
    """Round-robin first half of a season -> list of (match_id, home_id, away_id)."""
    n = len(team_ids)
    pairs = [(team_ids[i], team_ids[j]) for i in range(n) for j in range(i + 1, n)]
    out = [(mid, h, a) for mid, (h, a) in enumerate(pairs[:n_matches], start=1)]
    return out


def _press_level(rng, opp_rating, ball_x, rating_diff):
    """Opponent press intensity proxy for a possession (0=low,1=mid,2=high)."""
    p_high = 0.15 + 0.15 * ((opp_rating - 1500) / 250) - 0.1 * (rating_diff / 250)
    p_mid = 0.45
    roll = rng.random()
    if roll < np.clip(p_high, 0.03, 0.6):
        return 2
    if roll < p_mid:
        return 1
    return 0


def _start_location(rng, is_goal_kick, is_kick_off):
    if is_goal_kick:
        return rng.uniform(2, 8), rng.uniform(20, 60)
    if is_kick_off:
        return 50.0, 40.0
    x = rng.uniform(18, 48)
    y = rng.uniform(8, 72)
    return x, y


def _xgs(rng, x):
    """Rough xG curve for a shot from x (metres from own goal)."""
    if x < 5.5:
        return 0.6
    if x < 11:
        return 0.32
    if x < 16.5:
        return 0.18
    if x < 20:
        return 0.10
    return 0.05


def simulate_match(match_id: int, home_id: int, away_id: int, rng: np.random.Generator) -> list[dict]:
    """Simulate one match, returning a list of tidy event dicts."""
    home_name, home_elo, home_form = TEAMS[home_id]
    away_name, away_elo, away_form = TEAMS[away_id]
    events: list[dict] = []
    score = {home_id: 0, away_id: 0}
    possession_counter = 0
    minute = 0
    n_possessions = int(rng.integers(80, 110))

    for _ in range(n_possessions):
        attacking_side = home_id if rng.random() < 0.5 else away_id
        defending_side = away_id if attacking_side == home_id else home_id
        att_elo = home_elo if attacking_side == home_id else away_elo
        def_elo = home_elo if defending_side == home_id else away_elo
        att_name = home_name if attacking_side == home_id else away_name
        def_name = home_name if defending_side == home_id else away_name
        att_form = home_form if attacking_side == home_id else away_form
        rating_diff = att_elo - def_elo

        possession_counter += 1
        minute += int(rng.integers(0, 3))  # some possessions end at the same minute
        if minute > 92:
            break
        period = 1 if minute <= 45 else 2

        recovery = RECOVERY_TYPES[int(rng.integers(len(RECOVERY_TYPES)))]
        # turnovers and interceptions can happen higher up the pitch
        if recovery in ("interception", "ball_recovery"):
            x0 = rng.uniform(30, 68)
        else:
            x0, y0 = _start_location(rng, recovery == "goal_kick", recovery == "kick_off")
        y0 = rng.uniform(8, 72) if recovery in ("interception", "ball_recovery") else y0
        play_pattern = "from_kick_off" if recovery == "kick_off" else (
            "from_goal_kick" if recovery == "goal_kick" else "regular_play"
        )
        press = _press_level(rng, def_elo, x0, rating_diff)
        counterattack = recovery in ("interception", "ball_recovery") and x0 > 40

        n_actions = int(rng.integers(1, 11))
        x, y = x0, y0
        shot_taken = False
        goal = False
        shot_xg = 0.0
        first = True

        # opening recovery event
        events.append(_event(
            match_id, minute, period, att_name, att_form, possession_counter,
            att_name, play_pattern, recovery, x, y, None, None, False,
            counterpress=counterattack and press > 0, rng=rng, team_id=attacking_side,
        ))

        for _ in range(n_actions):
            if rng.random() < 0.10 + 0.08 * press - 0.05 * (rating_diff / 250):
                # turnover before any shot
                break
            # advance the ball
            length = float(rng.lognormal(1.95, 0.5) if rng.random() < 0.75 else rng.lognormal(2.7, 0.35))
            length = min(length, 50.0)
            angle = float(rng.normal(0, 0.35))  # radians deviation from forward
            end_x = float(np.clip(x + length * np.cos(angle), 0, PITCH_LENGTH))
            end_y = float(np.clip(y + length * np.sin(angle) * 0.8, 0, PITCH_WIDTH))
            under_press = rng.random() < (0.15 + 0.25 * press)
            switch = bool(end_x > 0 and abs(end_y - y) > 22 and end_x > 60)

            if end_x >= 72 and rng.random() < 0.22 + 0.10 * (end_x - 72) / 48:
                # shot
                shot_xg = _xgs(rng, end_x)
                shot_taken = True
                outcome = SHOT_OUTCOMES[0] if rng.random() < shot_xg else SHOT_OUTCOMES[int(rng.integers(1, len(SHOT_OUTCOMES)))]
                if outcome == "Goal":
                    goal = True
                    score[attacking_side] += 1
                events.append(_event(
                    match_id, minute, period, att_name, att_form, possession_counter,
                    att_name, play_pattern, "shot", x, y, end_x, end_y, under_press,
                    shot_xg=shot_xg, shot_outcome=outcome,
                    shot_type=SHOT_BODY[int(rng.integers(len(SHOT_BODY)))],
                    rng=rng, team_id=attacking_side,
                ))
                break

            events.append(_event(
                match_id, minute, period, att_name, att_form, possession_counter,
                att_name, play_pattern, "pass", x, y, end_x, end_y, under_press,
                pass_length=length, pass_angle=angle, pass_switch=switch,
                pass_height="Ground Pass" if rng.random() < 0.8 else "High Pass",
                pass_shot_assist=bool(end_x > 68 and rng.random() < 0.06),
                pass_assisted_shot=(end_x > 68 and rng.random() < 0.06) or None,
                rng=rng, team_id=attacking_side, recipient=attacking_side * 100 + 9,
            ))
            x, y = end_x, end_y
            if first and counterattack:
                events[-1]["counterpress"] = press > 0
            first = False

        # possession end marker for features (computed downstream, not an event)
        _ = shot_taken, goal, shot_xg
    return events


def _player(rng, team_id: int) -> tuple[int | None, str | None]:
    """Deterministic pseudo-player per team (id = team_id*100 + shirt)."""
    if team_id is None:
        return None, None
    shirt = int(rng.integers(1, 15))
    return team_id * 100 + shirt, f"P{team_id}-{shirt}"


def _event(
    match_id, minute, period, team, formation, possession, possession_team,
    play_pattern, etype, x, y, end_x, end_y, under_pressure, counterpress=False,
    shot_xg=None, shot_outcome=None, shot_type=None, pass_length=None,
    pass_angle=None, pass_switch=None, pass_height=None, pass_shot_assist=False,
    pass_assisted_shot=None, rng=None, team_id=None, recipient=None,
) -> dict:
    rng = rng or np.random.default_rng(0)
    second = int(rng.integers(0, 60))
    player_id, player_name = _player(rng, team_id)
    if etype == "pass" and recipient is not None:
        recipient_name = f"P{recipient // 100}-{recipient % 100}"
    else:
        recipient_name = None
    row = {c: None for c in _EVENT_COLUMNS}
    row.update(
        match_id=match_id, period=period, minute=minute,
        second=second,
        timestamp=f"{minute:02d}:{second:02d}",
        team=team, team_id=team_id, player_id=player_id, player=player_name,
        type=etype,
        possession=possession, possession_team=possession_team,
        play_pattern=play_pattern, x=x, y=y, end_x=end_x, end_y=end_y,
        under_pressure=under_pressure, counterpress=counterpress,
        shot_xg=shot_xg, shot_outcome=shot_outcome, shot_type=shot_type,
        pass_length=pass_length, pass_angle=pass_angle, pass_switch=pass_switch,
        pass_height=pass_height, pass_shot_assist=pass_shot_assist,
        pass_assisted_shot=pass_assisted_shot,
        pass_recipient=recipient_name,
        ball_recovery=etype == "ball_recovery",
        interception=etype == "interception",
        clearance=etype == "clearance",
        formation=formation,
    )
    return row


def generate_synthetic_dataset(n_matches: int = 24, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate a deterministic synthetic dataset: (matches, events)."""
    rng = _rng(seed)
    team_ids = list(range(len(TEAMS)))
    schedule = _schedule(team_ids, n_matches)
    matches = []
    all_events: list[dict] = []
    for match_id, home_id, away_id in schedule:
        home_name, _, home_form = TEAMS[home_id]
        away_name, _, away_form = TEAMS[away_id]
        home_score = 0
        away_score = 0
        evs = simulate_match(match_id, home_id, away_id, rng)
        for ev in evs:
            if ev["type"] == "shot" and ev["shot_outcome"] == "Goal":
                if ev["team"] == home_name:
                    home_score += 1
                else:
                    away_score += 1
        all_events.extend(evs)
        matches.append(
            {
                "match_id": match_id,
                "match_date": pd.Timestamp("2026-01-01") + pd.Timedelta(days=match_id),
                "competition": "Synthetic League",
                "season": "2025/26",
                "home_team_id": home_id,
                "home_team": home_name,
                "away_team_id": away_id,
                "away_team": away_name,
                "home_score": home_score,
                "away_score": away_score,
                "home_formation": home_form,
                "away_formation": away_form,
                "stadium": f"{home_name} Stadium",
                "referee": "S. Referee",
            }
        )
    return pd.DataFrame(matches), pd.DataFrame(all_events, columns=_EVENT_COLUMNS)
