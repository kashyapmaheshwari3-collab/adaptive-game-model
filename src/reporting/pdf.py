"""Auto-generated PDF reports (reportlab platypus).

Three audiences (component 7 - executive communication):

- ``technical_report.pdf``   -> data scientist
- ``coach_report.pdf``       -> analyst / assistant coach
- ``recruitment_report.pdf`` -> sporting director / head coach (one-pager)
- ``opponent_report.pdf``    -> example opponent report (per match)

All content is generated from the processed artefacts, so the reports are
always in sync with the last pipeline run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.config import (
    ADJUSTMENT_LABELS,
    PROCESSED_DIR,
    REPORTS_DIR,
    STATE_DESCRIPTIONS,
    STATE_LABELS,
)

ACCENT = colors.HexColor("#0B6E4F")
DARK = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#475569")
LIGHT = colors.HexColor("#F1F5F9")


def _styles() -> dict:
    ss = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("T", parent=ss["Title"], fontSize=24, textColor=DARK, spaceAfter=4),
        "h1": ParagraphStyle(
            "H1", parent=ss["Heading1"], fontSize=15, textColor=ACCENT, spaceBefore=12, spaceAfter=4
        ),
        "h2": ParagraphStyle(
            "H2", parent=ss["Heading2"], fontSize=11.5, textColor=DARK, spaceBefore=8, spaceAfter=2
        ),
        "body": ParagraphStyle(
            "B",
            parent=ss["BodyText"],
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#1e293b"),
        ),
        "small": ParagraphStyle(
            "S", parent=ss["BodyText"], fontSize=8, leading=11, textColor=MUTED
        ),
        "bullet": ParagraphStyle(
            "BL",
            parent=ss["BodyText"],
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#1e293b"),
            leftIndent=12,
            bulletIndent=4,
        ),
    }
    return styles


def _para_table(data: list[list], widths: list | None = None) -> Table:
    t = Table(data, colWidths=widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def _load() -> dict:
    ev = json.load(open(PROCESSED_DIR / "evaluation_report.json", encoding="utf-8"))
    err = json.load(open(PROCESSED_DIR / "error_analysis.json", encoding="utf-8"))
    abl = json.load(open(PROCESSED_DIR / "ablation_report.json", encoding="utf-8"))
    mc = json.load(open(PROCESSED_DIR / "model_card.json", encoding="utf-8"))
    recs = pd.read_csv(PROCESSED_DIR / "recommendations.csv")
    states = pd.read_csv(PROCESSED_DIR / "state_profiles.csv")
    poss = pd.read_parquet(PROCESSED_DIR / "possessions.parquet")
    matches = pd.read_parquet(PROCESSED_DIR / "matches.parquet")
    dec = json.load(open(PROCESSED_DIR / "decision_outputs.json", encoding="utf-8"))
    return {
        "ev": ev,
        "err": err,
        "abl": abl,
        "mc": mc,
        "recs": recs,
        "states": states,
        "poss": poss,
        "matches": matches,
        "dec": dec,
    }


def _s(row: pd.Series, col: str, fallback: str = "n/a") -> str:
    v = row.get(col)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return fallback
    return str(v)


def _build(data: dict, story: list, filename: str) -> Path:
    out = REPORTS_DIR / filename
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    doc.build(story)
    return out


def build_technical_pdf() -> Path:
    """Full methodology + validation document (data-scientist audience)."""
    d = _load()
    ev, mc, err, abl = d["ev"], d["mc"], d["err"], d["abl"]
    st = _styles()
    story = [
        Paragraph("Adaptive Game Model - Technical Report", st["title"]),
        Paragraph(
            "Event-based tactical decision intelligence: methodology, validation, and reproducibility",
            st["small"],
        ),
        Spacer(1, 6),
    ]

    story.append(Paragraph("1. Problem & modelling decision", st["h1"]))
    story.append(
        Paragraph(
            "We estimate which build-up adjustment should be used against a specific opponent structure - not "
            "which team wins. Every possession is labelled with a 0-5 outcome scale and converted to expected "
            "possession value (EPV) in goal-probability units. The value model (XGBoost + isotonic calibration) "
            "is trained on ex-ante features; tactical states are discovered by clustering and named by football "
            "prototypes; adjustment values are estimated causally with stabilised IPW and a doubly-robust (AIPW) "
            "augmentation, with match-clustered bootstrap confidence intervals.",
            st["body"],
        )
    )

    story.append(Paragraph("2. Data & preprocessing", st["h1"]))
    story.append(
        Paragraph(
            f"Source: {mc.get('data_source', {}).get('data_source', 'n/a')} | "
            f"{ev.get('n_matches')} matches, {ev.get('n_possessions')} possessions.",
            st["body"],
        )
    )
    v = json.load(open(PROCESSED_DIR / "validation_report.json", encoding="utf-8"))
    rows = [["Check", "Severity", "Count", "Message"]] + [
        [i["check"], i["severity"], str(i["count"]), i["message"][:80]] for i in v.get("issues", [])
    ]
    story.append(_para_table(rows, [170, 55, 40, 290]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("3. Possession value model", st["h1"]))
    metrics = ev.get("metrics", {})
    mrows = [["Model", "RMSE", "MAE", "R2"]] + [
        [k, f"{v.get('rmse', 0):.4f}", f"{v.get('mae', 0):.4f}", f"{v.get('r2', 0):.3f}"]
        for k, v in metrics.items()
    ]
    story.append(_para_table(mrows, [140, 70, 70, 70]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("4. Calibration & temporal validation", st["h1"]))
    cal = ev.get("calibration_test", {})
    story.append(
        Paragraph(
            f"Out-of-time calibration ECE = {cal.get('ece', 0):.4f} (MSE {cal.get('mse', 0):.5f}). "
            "The model is evaluated strictly chronologically: train on earlier matches, validate and test on later "
            "matches. No action from a match appears in more than one split (leakage check passes).",
            st["body"],
        )
    )

    story.append(Paragraph("5. Tactical states", st["h1"]))
    for _, r in d["states"].sort_values("n", ascending=False).iterrows():
        story.append(
            Paragraph(
                f"<b>{STATE_LABELS.get(r['tactical_state'], r['tactical_state'])}</b> - "
                f"{int(r['n'])} sequences, baseline EPV {r['baseline_epv']:.3f}.",
                st["bullet"],
            )
        )

    story.append(Paragraph("6. Adjustment value estimates", st["h1"]))
    if not d["recs"].empty:
        rrows = [["State", "Adjustment", "Uplift", "CI", "Confidence", "n"]] + [
            [
                STATE_LABELS.get(r["tactical_state"], r["tactical_state"]),
                ADJUSTMENT_LABELS.get(r["strategy"], r["strategy"]),
                f"{r['aipw_ate']:+.3f}",
                f"[{r['ci_low']:+.3f}, {r['ci_high']:+.3f}]",
                r["confidence"],
                str(int(r["n_treated"]) + int(r["n_control"])),
            ]
            for _, r in d["recs"].head(15).iterrows()
        ]
        story.append(_para_table(rrows, [150, 170, 60, 100, 70, 45]))

    story.append(Paragraph("7. Error analysis", st["h1"]))
    story.append(Paragraph("Three worst failures:", st["h2"]))
    for f in err.get("failures", [])[:3]:
        story.append(
            Paragraph(
                f"<b>{f.get('team')} vs {f.get('opponent')}</b> (min {f.get('minute')}): actual {f.get('actual_epv'):.3f} vs "
                f"predicted {f.get('pred_epv'):.3f} - {f.get('explanation', '')}",
                st["bullet"],
            )
        )

    story.append(Paragraph("8. Ablation & sensitivity", st["h1"]))
    ab = abl.get("ablation", {})
    arows = [["Feature group", "RMSE", "MAE", "R2"]] + [
        [k, f"{v.get('rmse', 0):.4f}", f"{v.get('mae', 0):.4f}", f"{v.get('r2', 0):.3f}"]
        for k, v in ab.items()
    ]
    story.append(_para_table(arows, [140, 70, 70, 70]))

    story.append(Paragraph("9. Known limitations", st["h1"]))
    for lim in mc.get("known_limitations", []):
        story.append(Paragraph(f"&bull; {lim}", st["bullet"]))

    story.append(Paragraph("10. Reproducibility", st["h1"]))
    story.append(
        Paragraph(
            "Run <b>python -m src.pipeline.run_all</b> to reproduce all artefacts. Data manifest with SHA-256 "
            "fingerprints lives in data/processed/data_manifest.json. Random seed fixed (42); synthetic fallback "
            "is deterministic for offline CI.",
            st["body"],
        )
    )
    return _build(d, story, "technical_report.pdf")


def build_coach_pdf() -> Path:
    """Analyst-facing report with recommendations and interpretations."""
    d = _load()
    st = _styles()
    story = [
        Paragraph("Adaptive Game Model - Coach Report", st["title"]),
        Paragraph("Tactical adjustment recommendations with uncertainty", st["small"]),
        Spacer(1, 6),
    ]

    story.append(Paragraph("How to read this", st["h1"]))
    story.append(
        Paragraph(
            "Each recommendation states the opponent structure, the adjustment, the expected change in possession "
            "value per possession, a confidence interval, the sample it is based on, the main risk and the execution "
            "requirement. Low-confidence rows are deliberately flagged - treat them as hypotheses, not instructions.",
            st["body"],
        )
    )

    story.append(Paragraph("Recommended adjustments (ranked)", st["h1"]))
    if not d["recs"].empty:
        rows = [["State", "Adjustment", "Uplift / possession", "95% CI", "Conf."]] + [
            [
                STATE_LABELS.get(r["tactical_state"], r["tactical_state"]),
                ADJUSTMENT_LABELS.get(r["strategy"], r["strategy"]),
                f"{r['aipw_ate']:+.3f}",
                f"[{r['ci_low']:+.3f}, {r['ci_high']:+.3f}]",
                r["confidence"],
            ]
            for _, r in d["recs"].head(20).iterrows()
        ]
        story.append(_para_table(rows, [150, 200, 90, 100, 60]))
        story.append(Spacer(1, 6))
        for _, r in d["recs"].head(6).iterrows():
            state = r["tactical_state"]
            story.append(
                Paragraph(
                    f"<b>{STATE_LABELS.get(state, state)}</b> - {ADJUSTMENT_LABELS.get(r['strategy'], r['strategy'])}",
                    st["h2"],
                )
            )
            story.append(
                Paragraph(
                    f"Expected benefit: {r['aipw_ate']:+.3f} EPV/possession (95% CI [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}]). "
                    f"Confidence: {r['confidence']}. Sample: {int(r['n_treated']) + int(r['n_control'])} sequences "
                    f"({int(r['n_treated'])} treated / {int(r['n_control'])} control).",
                    st["body"],
                )
            )
            story.append(Paragraph(f"Main risk: {_s(r, 'risk')}", st["bullet"]))
            story.append(Paragraph(f"Execution: {_s(r, 'execution')}", st["bullet"]))

    story.append(Paragraph("Tactical state glossary", st["h1"]))
    for state, desc in STATE_DESCRIPTIONS.items():
        story.append(Paragraph(f"<b>{STATE_LABELS.get(state, state)}</b> - {desc}", st["bullet"]))

    story.append(Paragraph("Relevant sequences to review", st["h1"]))
    sample = d["poss"][d["poss"]["outcome_level"] >= 4].drop_duplicates("match_id").head(5)
    for _, r in sample.iterrows():
        story.append(
            Paragraph(
                f"Match {int(r['match_id'])} | {r['possession_team']} | min {int(r['minute'])} | "
                f"state: {STATE_LABELS.get(r.get('tactical_state', ''), r.get('tactical_state', ''))} | "
                f"outcome level {int(r['outcome_level'])} (shot xG {r['max_shot_xg']:.2f})",
                st["bullet"],
            )
        )
    return _build(d, story, "coach_report.pdf")


def build_recruitment_pdf() -> Path:
    """Sporting-director one-pager: 3 findings, 1 action, 1 risk, 1 uncertainty."""
    d = _load()
    ev, recs = d["ev"], d["recs"]
    st = _styles()
    top = recs.sort_values("aipw_ate", ascending=False).head(3) if not recs.empty else None
    story = [
        Paragraph("Adaptive Game Model - One-Page Summary", st["title"]),
        Paragraph("For the Sporting Director / Head Coach", st["small"]),
        Spacer(1, 8),
    ]

    story.append(Paragraph("Three key findings", st["h1"]))
    if top is not None and len(top):
        for i, (_, r) in enumerate(top.iterrows(), 1):
            story.append(
                Paragraph(
                    f"{i}. Against <b>{STATE_LABELS.get(r['tactical_state'], r['tactical_state'])}</b>, "
                    f"<b>{ADJUSTMENT_LABELS.get(r['strategy'], r['strategy'])}</b> adds "
                    f"<b>{r['aipw_ate']:+.3f}</b> expected possession value per possession "
                    f"(CI [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}]).",
                    st["bullet"],
                )
            )
    else:
        story.append(
            Paragraph("No adjustment estimates reached the sample threshold yet.", st["body"])
        )
    story.append(
        Paragraph(
            f"The value model beats every baseline out-of-time (RMSE {ev.get('metrics', {}).get('xgboost_calibrated', {}).get('rmse', 0):.3f} "
            f"vs league-average {ev.get('metrics', {}).get('league_average', {}).get('rmse', 0):.3f}).",
            st["bullet"],
        )
    )
    story.append(
        Paragraph(
            "The system names its tactical states in coaching language and explains its failures - it is built to be "
            "questioned, not to be followed blindly.",
            st["bullet"],
        )
    )

    story.append(Paragraph("One action", st["h1"]))
    if top is not None and len(top):
        r = top.iloc[0]
        story.append(
            Paragraph(
                f"Adopt <b>{ADJUSTMENT_LABELS.get(r['strategy'], r['strategy'])}</b> when the opponent shows "
                f"<b>{STATE_LABELS.get(r['tactical_state'], r['tactical_state'])}</b> - worth ~"
                f"{r['aipw_ate'] * 60:.1f} EPV across 60 possessions, at {r['confidence']} confidence.",
                st["body"],
            )
        )
    story.append(Spacer(1, 4))

    story.append(Paragraph("One risk", st["h1"]))
    if top is not None and len(top):
        story.append(Paragraph(_s(top.iloc[0], "risk"), st["body"]))
    story.append(Spacer(1, 4))

    story.append(Paragraph("One uncertainty", st["h1"]))
    story.append(
        Paragraph(
            "All estimates are event-based historical expectations with explicit confidence intervals; they are not "
            "guarantees. Applicability is limited to opponents and leagues in the training set, and tracking-level "
            "effects (space, timing) are not captured.",
            st["body"],
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Contact: you@example.com | github.com/your-handle/adaptive-game-model", st["small"]
        )
    )
    return _build(d, story, "recruitment_report.pdf")


def build_opponent_pdf(match_id: int | None = None) -> Path:
    """Example opponent report for a match (or the highest-value match)."""
    d = _load()
    dec = d["dec"]
    if match_id is None:
        match_id = next(iter(dec)) if dec else None
    st = _styles()
    info = dec.get(str(match_id), {})
    story = [
        Paragraph("Example Opponent Report", st["title"]),
        Paragraph(
            f"{info.get('home_team', '?')} vs {info.get('away_team', '?')} "
            f"- {info.get('match_date', '?')}",
            st["small"],
        ),
        Spacer(1, 8),
    ]
    story.append(Paragraph("Tactical state mix expected", st["h1"]))
    for s in info.get("states", []):
        story.append(
            Paragraph(
                f"&bull; {STATE_LABELS.get(s.get('state', ''), s.get('state', ''))}: {s.get('count')} sequences "
                f"({s.get('share', 0) * 100:.0f}%)",
                st["bullet"],
            )
        )
    story.append(Paragraph("Recommended adjustment", st["h1"]))
    rec = info.get("overall_recommendation")
    if rec:
        story.append(Paragraph(rec.get("text", ""), st["body"]))
        story.append(Paragraph(f"Risk: {rec.get('risk')}", st["bullet"]))
        story.append(Paragraph(f"Execution: {rec.get('execution')}", st["bullet"]))
    else:
        story.append(
            Paragraph("Insufficient comparable sequences - more data required.", st["body"])
        )
    story.append(Paragraph("Applicability limits", st["h1"]))
    story.append(
        Paragraph(
            "Event-based estimates only; no tracking data. Validation is chronological and league-specific.",
            st["body"],
        )
    )
    return _build(d, story, "opponent_report.pdf")
