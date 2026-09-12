# Data Dictionary

The pipeline standardises raw event data into a single **tidy event frame** with one row per event. Every downstream stage uses exactly this schema, so the system is data-source agnostic (StatsBomb Open Data, or the deterministic synthetic fallback).

## 1. Event frame (`data/processed/events.parquet`)

| Column | Type | Description |
|---|---|---|
| `match_id` | int | Match identifier (StatsBomb match id, or 1..N for synthetic). |
| `period` | int | 1 = first half, 2 = second half (3+ for extra time). |
| `minute` | int | Match minute (StatsBomb convention: >60 for second half). |
| `second` | int | Second within the minute. |
| `timestamp` | str | `"HH:MM:SS.mmm"` where HH = minute. |
| `team_id` / `team` | int / str | Possessing team for the event. |
| `player_id` / `player` | int / str | Player responsible for the event (may be null for generic events). |
| `type` | str | Normalised event type: `pass`, `shot`, `carry`, `dribble`, `duel`, `ball_recovery`, `interception`, `clearance`, `ball_receipt`, `miscontrol`, `50_50`, `block`, `foul`, ... |
| `possession` | int | StatsBomb possession sequence id. |
| `possession_team` | str | Team in possession of this sequence. |
| `play_pattern` | str | `regular_play`, `counterattack`, `from_throw_in`, `from_corner`, `from_kick_off`, `from_goal_kick`, ... |
| `x` / `y` | float | Event location (StatsBomb metres, pitch 120 x 80). |
| `end_x` / `end_y` | float | End location for passes / shots / carries. |
| `under_pressure` | bool | Whether the event happened under opponent pressure (StatsBomb tag). |
| `counterpress` | bool | Whether the team counter-pressed immediately after (tag or inferred). |
| `shot_xg` | float | StatsBomb xG for shot events. |
| `shot_outcome` | str | `Goal`, `Saved`, `Off T`, `Blocked`, `Wayward`, `Post`. |
| `pass_length` / `pass_angle` | float | Pass distance (m) and angle (rad). |
| `pass_recipient` | str | Name of pass recipient. |
| `pass_height` | str | `Ground Pass`, `High Pass`, `Low Pass`. |
| `pass_switch` | bool | Switch-of-play flag. |
| `pass_shot_assist` / `pass_goal_assist` | bool | Shot/goal assist flags. |
| `pass_assisted_shot` | int | Id of the assisted shot event (if any). |
| `duel_type` / `duel_outcome` | str | Duel metadata. |
| `formation` | int | Starting formation of the team (e.g. 433, 442). |

### Enrichment columns (added by `enrich_events`)

| Column | Description |
|---|---|
| `event_seconds` | `minute*60 + second` for chronometric ordering. |
| `home_team`, `opponent_team` | Teams in the match. |
| `team_formation`, `opponent_formation` | Starting formations of both sides. |
| `is_home` | Home/away indicator. |
| `score_diff` | Scoreline difference *before* the event (team - opponent). |
| `zone_x`, `zone_y`, `end_zone_x`, `end_zone_y` | Named zones: `defensive_third`, `middle_third`, `advanced_third`, `final_third` x; `wide`, `half_space`, `central` y. |
| `in_box` | Whether the event is inside the penalty box. |

## 2. Possession frame (`data/processed/possessions.parquet`)

One row per `(match_id, possession, possession_team)`.

| Column | Description |
|---|---|
| `start_x`, `start_y`, `end_x`, `end_y` | Start/end location of the possession. |
| `n_actions`, `n_passes`, `n_shots` | Counts. |
| `duration_seconds` | Time span between first and last event. |
| `net_progress_x` | Net x-progression (end_x - start_x). |
| `crossed_midfield`, `entered_final_third` | Progression flags. |
| `max_shot_xg` | Highest xG shot in the possession (0 if none). |
| `pressure_proxy` | Share of attacking actions taken under pressure. |
| `counterpress_flags` | Number of counterpress-tagged events. |
| `recovery_type` | How the possession started (interception, ball recovery, goal kick, ...). |
| `play_pattern`, `minute`, `period`, `is_home`, `score_diff` | Context. |
| `team`, `opponent_team`, `team_formation`, `opponent_formation` | Teams and shapes. |
| `team_elo`, `opp_elo`, `elo_diff` | Pre-match Elo features. |
| `first_pressure` | Pressure on the first event. |
| `outcome_level` | **0-5 outcome scale** (see below). |
| `epv` | **Expected Possession Value** in goal-probability units (target). |
| `switch_passes` | Switch-of-play passes count. |
| `s_<adjustment>` | Strategy labels (0/1) for each of the 8 adjustments. |
| `tactical_state` | Detected state (named, e.g. `opponent_low_block`). |

### Outcome scale (Phase 1 vocabulary)

| Level | Meaning |
|---|---|
| 0 | Possession lost before progression |
| 1 | Retained but no meaningful progression |
| 2 | Entered an advanced zone |
| 3 | Created a dangerous action |
| 4 | Created a shot |
| 5 | Created a high-value shot (xG >= 0.15) |

### Strategy labels (`s_*`)

Transparent, rule-based proxies of coaching adjustments, computed from event
geometry (documented in `docs/methodology.md`):

| Strategy | Proxy |
|---|---|
| `s_build_up_shape_three_two_five` | Deep build-up (start_x < 40), >= 6 passes, >= 35% central build-up share |
| `s_fullback_inversion` | >= 1 pass from full-back zone into central zones |
| `s_increase_winger_width` | >= 1 pass into the wide final-third band |
| `s_attack_far_side_half_space` | >= 1 long switch into the far half-space past x=62 |
| `s_third_man_combination` | >= 1 run of 3 consecutive short passes (< 18 m) |
| `s_reduce_risky_central_passes` | < 25% of central passes made under pressure |
| `s_aggressive_counterpress` | Counterpress flags, or high recoveries |
| `s_mid_block_retreat` | Deep recovery with short possession (< 3 passes, < 25 m progress) |

## 3. Matches frame (`data/processed/matches.parquet`)

Match metadata: teams, date, competition/season, score, starting formations,
stadium, referee.

## 4. Adjustment estimates (`data/processed/adjustments.csv`)

| Column | Description |
|---|---|
| `tactical_state` | Detected state. |
| `strategy` | Adjustment key. |
| `n_treated` / `n_control` | Sequences with/without the strategy in that state. |
| `state_baseline_epv` | Mean EPV in the state. |
| `ipw_ate` / `aipw_ate` | Inverse-probability-weighted / doubly-robust average treatment effect (EPV units). |
| `ci_low` / `ci_high` | 95% bootstrap CI (match-clustered resampling). |
| `positivity_min_propensity`, `overlap` | Causal diagnostics. |
| `confidence` | `high` / `medium` / `low` label. |
| `risk`, `execution` | Coach-facing text. |

## 5. Reproducibility

- `data/processed/data_manifest.json` - source, license, match/event counts, dates, generated-at.
- `data/processed/validation_report.json` - full data-quality gate.
- All randomness fixed via `DEFAULT_RANDOM_STATE = 42`; the synthetic generator is seed-deterministic.

## Data licensing

StatsBomb Open Data is published under **CC BY-NC-SA 4.0**. You must
attribute StatsBomb and may not use the data commercially. See
`LICENSE` and `data/raw/statsbomb/LICENSE.txt` for details.
