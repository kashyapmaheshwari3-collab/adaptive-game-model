# Model Card - Adaptive Game Model v1.0

Generated from the latest pipeline run (see `data/processed/model_card.json` for the machine-readable version).

## Summary

| Field | Value |
|---|---|
| Model | Adaptive Game Model v1.0 |
| Task | Context-aware tactical adjustment value estimation (event-based) |
| Output | Expected Possession Value (EPV) in goal-probability units per possession; per-adjustment counterfactual ATE with 95% CI |
| Value model | XGBoost regressor + isotonic calibration |
| State model | KMeans clustering (k=8) + rule-based football-prototype naming |
| Adjustment estimator | Stabilised IPW + doubly-robust (AIPW), match-clustered bootstrap CIs |
| Random seed | 42 (deterministic) |

## Intended use

- Pre-match and in-match tactical decision support for coaching/analysis staff.
- Opponent-specific identification of which build-up/defensive adjustments
  historically improved possession value.
- Portfolio / research demonstration of a complete, reproducible football
  decision-intelligence pipeline.

## Data

- StatsBomb Open Data (CC BY-NC-SA 4.0) - La Liga 2015/16, 40 matches from
  Barcelona / Real Madrid / Atlético Madrid fixtures (elite club level).
- Offline/CI fallback: deterministic synthetic generator with identical schema.
- Data manifest with provenance: `data/processed/data_manifest.json`.

## Model evaluation

- Strictly chronological train/val/test split at match level.
- Metrics vs baselines: league average, linear regression, Elo-only, dummy.
- Calibration: ECE on deciles, out-of-time.
- Ablation: full features vs no-Elo / no-match-context / no-location.
- Error analysis: 3 best and 3 worst predictions with explanations.
- Match-drop sensitivity: recommendation stability.

## Known limitations

1. Event-based only - no tracking data (space/timing/off-ball movement absent).
2. Strategy labels are transparent, rule-based proxies of coaching concepts.
3. Estimates are historical expectations with explicit uncertainty - not guarantees.
4. Applicability limited to opponents/leagues represented in the training data.
5. Small samples produce low-confidence recommendations by design.

## Fairness / bias considerations

- Team-strength features (Elo) are conditioned explicitly so the model can
  distinguish "good team" effects from "good adjustment" effects.
- The validation protocol (future matches, never random splits) reduces
  optimistic evaluation that inflates claims.
- Dominant-team over-recommendation is monitored via Elo-conditioning and
  per-opponent validation.

## Reproduction

```bash
python -m pip install -r requirements.txt
python scripts/download_data.py      # optional: real StatsBomb data
python -m src.pipeline.run_all       # full pipeline -> data/processed
python scripts/generate_reports.py   # PDFs in reports/
python scripts/generate_visuals.py   # PNGs in visuals/
streamlit run app/Home.py            # dashboard
```

## Contact

Analyst: [your name] - [your email] - github.com/your-handle/adaptive-game-model
