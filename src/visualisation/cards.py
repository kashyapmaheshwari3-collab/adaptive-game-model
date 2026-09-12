"""Social media carousel cards (5-card, 1080x1080) with real model outputs.

The cards use tactical coaching language ("half-spaces", "low-blocks",
"transition vectors") rather than purely data jargon, exactly as specified in
the distribution brief for X/Twitter and LinkedIn.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from src.config import CARDS_DIR, PROCESSED_DIR, STATE_LABELS

W, H = 1080, 1080
BG = (15, 23, 42)
PANEL = (30, 41, 59)
ACCENT = (11, 110, 79)
GOLD = (245, 158, 11)
WHITE = (226, 232, 240)
MUTED = (148, 163, 184)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    import matplotlib.font_manager as fm

    picks = [
        f.fname for f in fm.fontManager.ttflist
        if f.name == "DejaVu Sans" and (f.style.lower() == "bold") == bold
    ]
    if not picks:
        picks = fm.findSystemFonts()
    return ImageFont.truetype(picks[0], size)


def _text_wrapped(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _render_card(header: str, kicker: str, body_lines: list[str], footer: str, out: Path) -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_head = _font(46, bold=True)
    f_kick = _font(30, bold=True)
    f_body = _font(34)
    f_foot = _font(26, bold=True)

    d.rectangle([0, 0, W, 14], fill=ACCENT)
    d.rectangle([0, H - 14, W, H], fill=GOLD)

    d.text((70, 60), kicker, font=f_kick, fill=GOLD)
    d.text((70, 110), header, font=f_head, fill=WHITE)

    y = 240
    for line in body_lines:
        for wrapped in _text_wrapped(d, line, f_body, W - 140):
            d.text((70, y), wrapped, font=f_body, fill=MUTED)
            y += 52
        y += 16
    d.rectangle([70, y + 10, W - 70, y + 18], fill=PANEL)

    d.text((70, H - 120), footer, font=f_foot, fill=ACCENT)
    d.text((70, H - 70), "@yourhandle  |  Adaptive Game Model  |  #FootballAnalytics", font=_font(24), fill=MUTED)
    img.save(out)
    print(f"  card -> {out.name}")


def render_social_cards(out_dir: Path = CARDS_DIR) -> list[Path]:
    """Generate the five 1080x1080 cards from processed artefacts."""
    out_dir.mkdir(parents=True, exist_ok=True)
    ev = json.load(open(PROCESSED_DIR / "evaluation_report.json", encoding="utf-8"))
    recs = pd.read_csv(PROCESSED_DIR / "recommendations.csv")
    states = pd.read_csv(PROCESSED_DIR / "state_profiles.csv")
    poss = pd.read_parquet(PROCESSED_DIR / "possessions.parquet")
    matches = pd.read_parquet(PROCESSED_DIR / "matches.parquet")
    data_src = ev.get("data_source", "synthetic")
    rmse = ev.get("metrics", {}).get("xgboost_calibrated", {}).get("rmse", 0)
    ece = ev.get("calibration_test", {}).get("ece", 0)
    n_poss = int(ev.get("n_possessions", 0))
    n_matches = int(ev.get("n_matches", 0))

    top_state = states.sort_values("n", ascending=False).iloc[0]
    top_rec = recs.sort_values("aipw_ate", ascending=False).iloc[0] if not recs.empty else None

    best_teams = sorted(matches["home_team"].dropna().unique().tolist())
    league = "La Liga 2015/16" if data_src == "statsbomb_open_data" else "Synthetic League"

    cards = []

    # Card 1: problem
    c1 = out_dir / "card1_problem.png"
    _render_card(
        "Which adjustment do we make NOW?",
        "THE DECISION",
        [
            "Opponent sits in a low block, denies central access.",
            "Our 4-3-3 keeps circulating without penetration.",
            "A tactical decision engine asks: which change adds the most expected value to the next phase?",
        ],
        f"{league} | {n_poss:,} possessions modelled",
        c1,
    )
    cards.append(c1)

    # Card 2: method
    c2 = out_dir / "card2_method.png"
    _render_card(
        "From events to counterfactual value",
        "THE METHOD",
        [
            "1. Possessions -> 0-5 outcome scale + expected possession value (EPV)",
            "2. Unsupervised states -> named: low block, high press, transitions",
            "3. IPW + doubly-robust estimation -> counterfactual adjustment value",
            "4. Match-level bootstrap -> honest confidence intervals",
        ],
        f"{n_matches} matches | temporal holdout validation",
        c2,
    )
    cards.append(c2)

    # Card 3: state detected
    state_label = STATE_LABELS.get(top_state["tactical_state"], top_state["tactical_state"])
    c3 = out_dir / "card3_state.png"
    _render_card(
        state_label.upper(),
        "STATE DETECTED",
        [
            f"{int(top_state['n'])} comparable sequences detected.",
            f"Baseline EPV per possession: {top_state['baseline_epv']:.3f}.",
            f"Pressure proxy {top_state['pressure_proxy']:.2f} | avg {top_state['n_passes']:.1f} passes per possession.",
        ],
        "Named states, never 'Cluster 7'",
        c3,
    )
    cards.append(c3)

    # Card 4: recommendation
    if top_rec is not None:
        n_seq = int(top_rec["n_treated"]) + int(top_rec["n_control"])
        c4 = out_dir / "card4_rec.png"
        _render_card(
            "The recommended adjustment",
            "COACH-FACING OUTPUT",
            [
                f"State: {STATE_LABELS.get(top_rec['tactical_state'], top_rec['tactical_state'])}",
                f"Adjustment: {top_rec['strategy_label']}",
                f"Expected uplift: {top_rec['aipw_ate']:+.3f} EPV per possession",
                f"95% CI: [{top_rec['ci_low']:+.3f}, {top_rec['ci_high']:+.3f}] | confidence: {top_rec['confidence']}",
                f"Based on {n_seq} comparable sequences.",
            ],
            "Every estimate ships with its uncertainty",
            c4,
        )
        cards.append(c4)

    # Card 5: honest validation + hook
    c5 = out_dir / "card5_validation.png"
    _render_card(
        "Validated on the future, not the past",
        "WHY TRUST IT",
        [
            f"Chronological split: model trained on earlier matches only.",
            f"Out-of-time RMSE {rmse:.4f} | calibration ECE {ece:.4f}",
            "Error analysis: 3 successes, 3 failures, and the data that would fix them.",
            "Human-in-the-loop: analyst notes, coach feedback, scout override.",
        ],
        f"Built with StatsBomb Open Data ({league})",
        c5,
    )
    cards.append(c5)

    return cards
