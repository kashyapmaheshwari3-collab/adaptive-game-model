"""Reporting package - PDF generation (technical, coach, recruitment)."""

from .pdf import (
    build_technical_pdf,
    build_coach_pdf,
    build_recruitment_pdf,
    build_opponent_pdf,
)

__all__ = [
    "build_technical_pdf",
    "build_coach_pdf",
    "build_recruitment_pdf",
    "build_opponent_pdf",
]
