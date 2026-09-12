"""Architecture diagram renderer (matplotlib boxes - no external tooling)."""

from __future__ import annotations

from pathlib import Path

from matplotlib import pyplot as plt
from matplotlib.patches import FancyBboxPatch

NODES = [
    ("Raw event data", "#1e293b", ["StatsBomb Open Data", "Synthetic fallback"]),
    ("Validation & cleaning", "#134e4a", ["duplicates / coords / ids", "timestamps / leakage"]),
    ("Event standardisation", "#134e4a", ["tidy event frame", "manifest + licence"]),
    ("Feature engineering", "#1d4ed8", ["possessions + outcome scale", "Elo, zones, pressure", "adjustment labels"]),
    ("Model training", "#7c3aed", ["EPV value model (XGBoost)", "tactical state clustering", "IPW + doubly-robust ATE"]),
    ("Model evaluation", "#b45309", ["temporal holdout", "calibration / baselines", "error analysis / ablation"]),
    ("Decision output", "#0b6e4f", ["adjustment value + CI", "confidence label", "risk + execution"]),
    ("Coach-facing product", "#0b6e4f", ["Streamlit dashboard", "auto-generated PDF reports", "example opponent report"]),
]


def render_architecture_diagram(out_path: Path, title: str = "Adaptive Game Model - pipeline architecture") -> Path:
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")
    fig.patch.set_facecolor("#0f172a")
    ax.set_title(title, color="white", fontsize=14, pad=10)

    n = len(NODES)
    for i, (label, color, subs) in enumerate(NODES):
        x = i * (12 / n) + 0.1
        w = 12 / n - 0.3
        y_top = 5.6
        box = FancyBboxPatch(
            (x, y_top), w, 1.6, boxstyle="round,pad=0.08",
            facecolor=color, edgecolor="#334155", linewidth=1.2,
        )
        ax.add_patch(box)
        ax.text(x + w / 2, y_top + 1.15, label, ha="center", va="center",
                color="white", fontsize=8.5, weight="bold", wrap=True)
        for j, sub in enumerate(subs):
            ax.text(x + w / 2, y_top + 0.62 - j * 0.42, sub, ha="center", va="center",
                    color="#cbd5e1", fontsize=6.8)
        if i < n - 1:
            ax.annotate(
                "", xy=(x + w + 0.12, y_top + 0.8), xytext=(x + w - 0.05, y_top + 0.8),
                arrowprops=dict(arrowstyle="->", color="#f59e0b", lw=2),
            )

    ax.text(6, 7.3, "Decision question: which tactical adjustment improves our next attacking/defensive phase?",
            ha="center", color="#fde68a", fontsize=11, weight="bold")
    ax.text(6, 0.55, "Uncertainty is carried end-to-end: CIs, sample size, calibration ECE, applicability limits",
            ha="center", color="#94a3b8", fontsize=9)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="#0f172a")
    plt.close(fig)
    return out_path
