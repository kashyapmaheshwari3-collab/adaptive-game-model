"""Decision package - the "what should we change?" answer."""

from .recommender import build_recommendations, recommendation_text, overall_recommendation
from .coach_text import (
    state_distribution_summary,
    recommendation_card_text,
    example_opponent_report,
)

__all__ = [
    "build_recommendations",
    "recommendation_text",
    "overall_recommendation",
    "state_distribution_summary",
    "recommendation_card_text",
    "example_opponent_report",
]
