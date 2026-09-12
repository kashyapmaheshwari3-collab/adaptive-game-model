"""Pitch visualisations (mplsoccer)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from mplsoccer import Pitch

from src.config import STATE_DESCRIPTIONS, STATE_LABELS, VISUALS_DIR


def plot_sequence(events: pd.DataFrame, title: str, out_path) -> None:
    """Plot one possession's event sequence on a StatsBomb pitch."""
    pitch = Pitch(pitch_type="statsbomb", pitch_color="grass", line_color="white", stripe=True)
    fig, ax = pitch.draw(figsize=(12, 8))
    ax.set_title(title, fontsize=14, color="white", pad=15)

    passes = events[events["type"] == "pass"]
    shots = events[events["type"] == "shot"]
    for _, p in passes.iterrows():
        pitch.arrows(
            p["x"], p["y"], p["end_x"], p["end_y"],
            width=2.5, headwidth=6, headlength=6, color="#94a3b8",
            ax=ax, alpha=0.9, zorder=3,
        )
    for _, s in shots.iterrows():
        pitch.scatter(s["x"], s["y"], s=150, color="#f59e0b", edgecolors="black", ax=ax, zorder=5)
    if not shots.empty:
        ax.text(
            shots.iloc[0]["x"], shots.iloc[0]["y"] + 4, f"xG {shots.iloc[0]['shot_xg']:.2f}",
            color="#fde68a", fontsize=10, ha="center", zorder=6,
        )
    first = events.iloc[0]
    pitch.scatter(first["x"], first["y"], s=220, color="#f8fafc", edgecolors="#0f172a", marker="o", ax=ax, zorder=5)
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="#0f172a")
    plt.close(fig)


def plot_state_heatmap(possessions: pd.DataFrame, state: str, out_path) -> None:
    """Hexbin heatmap of possession END locations for a tactical state."""
    sub = possessions[possessions["tactical_state"] == state]
    pitch = Pitch(pitch_type="statsbomb", pitch_color="grass", line_color="white")
    fig, ax = pitch.draw(figsize=(12, 8))
    if len(sub):
        pitch.hexbin(sub["end_x"], sub["end_y"], gridsize=(12, 8), cmap="Greens", ax=ax)
    ax.set_title(
        f"{STATE_LABELS.get(state, state)}  (n={len(sub)})",
        fontsize=13, color="white", pad=15,
    )
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="#0f172a")
    plt.close(fig)


def plot_calibration(calib: dict, out_path) -> None:
    """Calibration curve from calibration_metrics output."""
    bins = calib.get("bins", [])
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot([0, 1], [0, 1], "--", color="#94a3b8", label="Perfect calibration")
    pred = [b["pred_mean"] for b in bins]
    actual = [b["actual_mean"] for b in bins]
    ax.plot(pred, actual, "o-", color="#0b6e4f", lw=2, label="Model (deciles)")
    ax.fill_between(pred, actual, pred, alpha=0.15, color="#f59e0b", label="Gap")
    ax.set_xlabel("Mean predicted EPV")
    ax.set_ylabel("Mean actual EPV")
    ax.set_title(f"Calibration curve - ECE {calib.get('ece', 0):.4f}")
    ax.legend()
    ax.set_facecolor("#0f172a")
    fig.patch.set_facecolor("#0f172a")
    ax.tick_params(colors="white")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    ax.title.set_color("white")
    for spine in ax.spines.values():
        spine.set_color("#334155")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
