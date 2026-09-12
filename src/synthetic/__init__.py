"""Synthetic package - deterministic event-data generator.

The synthetic generator produces event streams that respect the same tidy
schema as StatsBomb data, so every pipeline stage (validation, features,
models, decision engine, dashboard, reports) can run offline and in CI.

It is NOT a substitute for real data - it exists so the project is always
runnable end-to-end ("fully executable without a single error") and so unit
tests never depend on the network. Real StatsBomb Open Data is used whenever
``data/raw/statsbomb`` is populated (see ``scripts/download_data.py``).
"""

from .generator import generate_synthetic_dataset

__all__ = ["generate_synthetic_dataset"]
