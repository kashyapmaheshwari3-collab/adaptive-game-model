"""Data ingestion package.

- ``statsbomb_loader``: turns StatsBomb Open Data JSON into a tidy event frame.
- ``download``: fetches StatsBomb Open Data from the public GitHub repository.
- ``manifest``: records exactly which matches were used (reproducibility).
"""

from .manifest import build_manifest, write_manifest
from .statsbomb_loader import load_events_frame, load_matches_frame

__all__ = [
    "load_events_frame",
    "load_matches_frame",
    "build_manifest",
    "write_manifest",
]
