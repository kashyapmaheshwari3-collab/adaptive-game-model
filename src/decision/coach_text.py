"""Coach-facing text generation (component 7: executive communication).

Produces the plain-language artefacts: state distribution summaries,
recommendation cards, and a full example opponent report in markdown.
"""

from __future__ import annotations

import pandas as pd

from src.config import ADJUSTMENT_LABELS, STATE_DESCRIPTIONS, STATE_LABELS


def state_distribution_summary(possessions: pd.DataFrame) -> str:
    """Human-readable distribution of tactical states for a match/team."""
    if possessions.empty:
        return "No possession data available."
    dist = possessions["tactical_state"].value_counts()
    total = len(possessions)
    lines = ["**Tactical state distribution** (share of possessions):"]
    for state, count in dist.items():
        label = STATE_LABELS.get(state, state.replace("_", " "))
        lines.append(f"- {label}: {count} possessions ({count / total:.0%})")
    return "\n".join(lines)


def recommendation_card_text(row: pd.Series, extra: dict | None = None) -> str:
    """A recommendation card like the one in the project brief."""
    state = row["tactical_state"]
    strategy = row["strategy"]
    state_label = STATE_LABELS.get(state, state.replace("_", " "))
    adj_label = ADJUSTMENT_LABELS.get(strategy, strategy.replace("_", " "))
    n = int(row["n_treated"]) + int(row["n_control"])
    lines = [
        f"### {state_label}",
        f"**Recommendation:** {adj_label}",
        f"- **Expected benefit:** {row['aipw_ate']:+.3f} additional expected possession value per possession "
        f"(95% CI [{row['ci_low']:+.3f}, {row['ci_high']:+.3f}])",
        f"- **Confidence:** {row['confidence']} (based on {n} comparable sequences, "
        f"{int(row['n_treated'])} treated / {int(row['n_control'])} control)",
        f"- **Main risk:** {row['risk']}",
        f"- **Execution requirement:** {row['execution']}",
    ]
    if extra:
        lines.append(f"- **Applicability limits:** {extra.get('applicability', '')}")
    return "\n".join(lines)


def example_opponent_report(
    team_name: str,
    opponent_name: str,
    state_dist: pd.Series,
    recs: pd.DataFrame,
    overall: dict | None,
) -> str:
    """Generate the example opponent report (markdown) deliverable."""
    lines = [
        f"# Example Opponent Report: {team_name} vs {opponent_name}",
        "",
        "**Prepared by the Adaptive Game Model** - event-based tactical decision intelligence.",
        "",
        "## 1. How we read the opponent",
        "",
        STATE_DESCRIPTIONS.get("opponent_low_block", ""),
        "",
        "## 2. Tactical states we expect to face",
        "",
    ]
    if not state_dist.empty:
        for state, count in state_dist.head(6).items():
            label = STATE_LABELS.get(state, state.replace("_", " "))
            desc = STATE_DESCRIPTIONS.get(state, "")
            lines.append(f"- **{label}** ({int(count)} comparable sequences): {desc}")
    lines += [
        "",
        "## 3. Recommended adjustments (with uncertainty)",
        "",
    ]
    if recs is not None and not recs.empty:
        for _, row in recs.head(4).iterrows():
            lines.append(recommendation_card_text(row))
            lines.append("")
    else:
        lines.append("No adjustment reached the minimum sample threshold yet - more data needed.")
    if overall:
        lines += [
            "## 4. The one action",
            "",
            f"{overall['text']}",
            "",
            f"**Risk:** {overall['risk']}",
            "",
            f"**Execution:** {overall['execution']}",
            "",
            "## 5. Uncertainty & limits",
            "",
            "- Every estimate is a historical expectation, not a guarantee.",
            "- Estimates are event-based; no tracking data was used.",
            "- Applicability is limited to opponents and leagues represented in the training set.",
        ]
    return "\n".join(lines)
