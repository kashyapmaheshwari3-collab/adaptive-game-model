"""Central configuration: paths, constants and the formal tactical vocabulary.

The tactical vocabulary (Phase 1 of the build plan) lives here so that every
downstream module - features, models, decision engine, dashboard, reports -
references exactly the same ontology.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_SB_DIR = RAW_DIR / "statsbomb"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"

REPORTS_DIR = ROOT / "reports"
VISUALS_DIR = ROOT / "visuals"
DOCS_DIR = ROOT / "docs"
SOCIAL_DIR = DOCS_DIR / "social"
CARDS_DIR = VISUALS_DIR / "cards"
NOTEBOOKS_DIR = ROOT / "notebooks"

HITL_LOG = PROCESSED_DIR / "hitl_log.json"

# --------------------------------------------------------------------------- #
# Pitch (StatsBomb convention, metres)
# --------------------------------------------------------------------------- #
PITCH_LENGTH = 120.0
PITCH_WIDTH = 80.0

MIDFIELD_LINE = 60.0
FINAL_THIRD_LINE = 80.0
DEFENSIVE_THIRD_LINE = 40.0

CENTRAL_BAND = (28.0, 52.0)  # y band considered "central" (StatsBomb y: 0..80)
HALF_SPACE_LEFT = (18.0, 28.0)
HALF_SPACE_RIGHT = (52.0, 62.0)
TOUCHLINE_BAND = 18.0  # within this distance of either touchline = "wide"

# --------------------------------------------------------------------------- #
# Tactical states (Phase 1 vocabulary)
# --------------------------------------------------------------------------- #
TACTICAL_STATES = [
    "opponent_low_block",
    "opponent_high_press",
    "narrow_front_two_buildup",
    "defensive_transition_after_loss",
    "wide_overload",
    "central_progression",
    "final_third_vs_compact_defence",
    "neutral_buildup",
]

STATE_LABELS = {
    "opponent_low_block": "Opponent low block",
    "opponent_high_press": "Opponent high press",
    "narrow_front_two_buildup": "Build-up vs narrow front two",
    "defensive_transition_after_loss": "Defensive transition after loss",
    "wide_overload": "Wide overload",
    "central_progression": "Central progression",
    "final_third_vs_compact_defence": "Final-third attack vs compact defence",
    "neutral_buildup": "Neutral build-up / rest state",
}

STATE_DESCRIPTIONS = {
    "opponent_low_block": "Opponent retreats into a deep block, denies central access, "
    "invites wide circulation before the final line.",
    "opponent_high_press": "Opponent presses high and aggressively; central access is "
    "denied and turnovers occur high up the pitch.",
    "narrow_front_two_buildup": "Opponent's front two stay narrow, cutting central "
    "build-up lanes; full-backs gain space.",
    "defensive_transition_after_loss": "Ball just lost; opponent is transitioning, our "
    "structure is unsettled and numbers around the ball are in flux.",
    "wide_overload": "Our possession is concentrated on one flank; opponent shifts, "
    "creating space on the far side.",
    "central_progression": "Possession is advancing through central channels between "
    "opponent lines.",
    "final_third_vs_compact_defence": "Ball is in the final third against a compact "
    "defensive block; half-spaces are the key zones.",
    "neutral_buildup": "Routine build-up with neither team committing aggressively.",
}

# --------------------------------------------------------------------------- #
# Tactical adjustments (the candidate decisions)
# --------------------------------------------------------------------------- #
ADJUSTMENTS = [
    "build_up_shape_three_two_five",
    "fullback_inversion",
    "increase_winger_width",
    "attack_far_side_half_space",
    "third_man_combination",
    "reduce_risky_central_passes",
    "aggressive_counterpress",
    "mid_block_retreat",
]

ADJUSTMENT_LABELS = {
    "build_up_shape_three_two_five": "Change build-up shape (4-3-3 -> 3-2-5)",
    "fullback_inversion": "Invert the full-back",
    "increase_winger_width": "Increase winger width",
    "attack_far_side_half_space": "Attack the far-side half-space",
    "third_man_combination": "Use a third-man combination",
    "reduce_risky_central_passes": "Reduce risky central passes",
    "aggressive_counterpress": "Trigger a more aggressive counter-press",
    "mid_block_retreat": "Retreat into a mid-block after loss",
}

ADJUSTMENT_RISKS = {
    "build_up_shape_three_two_five": "Higher execution requirement; if the press wins "
    "the ball, the back three is exposed in wide areas.",
    "fullback_inversion": "Exposes the wide channel behind the inverted full-back on transition.",
    "increase_winger_width": "Wingers can become isolated from central support if the "
    "opponent tracks with the full-back.",
    "attack_far_side_half_space": "Longer diagonals increase turnover risk if "
    "under-hit; requires accurate switches.",
    "third_man_combination": "Medium execution risk; combinations fail under intense "
    "pressure without strong first touches.",
    "reduce_risky_central_passes": "Can slow progression and invite the block to "
    "settle; risk of over-safety.",
    "aggressive_counterpress": "High exposure if the first press is bypassed; leaves "
    "space in behind.",
    "mid_block_retreat": "Concedes territorial control and gives the opponent "
    "uncontested build-up.",
}

ADJUSTMENT_EXECUTION = {
    "build_up_shape_three_two_five": "Structural - needs positional reps and a "
    "comfortable ball-playing back line.",
    "fullback_inversion": "Individual - one player change in positioning rules.",
    "increase_winger_width": "Individual - width references for wingers.",
    "attack_far_side_half_space": "Pattern - scripted switch of play + far-side runners.",
    "third_man_combination": "Pattern - rehearsed combinations between three players.",
    "reduce_risky_central_passes": "Decision rule - pass map restrictions in central zones.",
    "aggressive_counterpress": "Trigger - immediate pressure on the first pass after loss.",
    "mid_block_retreat": "Structural - repositioning below the ball at the moment of loss.",
}

# --------------------------------------------------------------------------- #
# Possession outcome scale (Phase 1 vocabulary)
# --------------------------------------------------------------------------- #
OUTCOME_LEVELS = {
    0: "Possession lost before progression",
    1: "Retained but no meaningful progression",
    2: "Entered an advanced zone",
    3: "Created a dangerous action",
    4: "Created a shot",
    5: "Created a high-value shot",
}

DANGEROUS_ACTION_XG = 0.10  # key-pass / assist-quality threshold for level 3
HIGH_VALUE_SHOT_XG = 0.15  # xG threshold for level 5

# --------------------------------------------------------------------------- #
# Data / modelling constants
# --------------------------------------------------------------------------- #
DEFAULT_RANDOM_STATE = 42
VAL_FRACTION = 0.25  # temporal holdout fraction (last matches of season)
N_BOOTSTRAP = 500  # bootstrap resamples for confidence intervals
MIN_POSSESSIONS_PER_STRATEGY = 25
POSITIVITY_MIN_PROPENSITY = 0.02  # positivity / overlap floor for IPW
PRESSURE_RADIUS = 5.0  # metres - proxy for "near-ball" density

# Default StatsBomb source (La Liga 2015/16 - elite club level)
DEFAULT_COMPETITION = 11
DEFAULT_SEASON = 27
