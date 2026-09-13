"""Decision package - the "what should we change?" answer."""

from .coach_text import (
    example_opponent_report,
    recommendation_card_text,
    state_distribution_summary,
)
from .recommender import build_recommendations, overall_recommendation, recommendation_text

__all__ = [
    "build_recommendations",
    "recommendation_text",
    "overall_recommendation",
    "state_distribution_summary",
    "recommendation_card_text",
    "example_opponent_report",
]
