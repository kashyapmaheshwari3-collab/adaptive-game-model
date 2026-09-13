# Module walkthrough

This is the order I use when explaining the project to another analyst.

## 1. Configuration

`src/config.py` is the single source of truth for paths, pitch dimensions,
zones, tactical-state names, adjustment names, the random seed, and output
locations. Keeping these definitions central prevents the ingestion, modelling,
dashboard, and reporting layers from silently disagreeing.

## 2. Ingestion

`src/ingestion/download.py` downloads the selected StatsBomb competition and
season. `src/ingestion/statsbomb_loader.py` converts nested event JSON into a
consistent tabular schema. `src/ingestion/manifest.py` records the source,
licence, counts, dates, and a checksum so a result can be traced back to the
input.

## 3. Synthetic fallback

`src/synthetic/generator.py` creates deterministic event data with the same
schema as the real loader. It exists for offline development and CI, not to
replace the real-data result. The manifest identifies which source was used.

## 4. Validation

`src/validation/checks.py` checks duplicate events, coordinates, player IDs,
timestamps, team names, competition identifiers, outliers, and train/test
leakage. `src/validation/report.py` turns those checks into a machine-readable
report used by the dashboard and generated reports.

## 5. Event features and possessions

`src/features/events.py` standardises zones, time, direction, and match
context. `src/features/possessions.py` groups events into attacking phases,
creates the 0–5 outcome scale, and calculates the possession-level target.
`src/features/elo.py` adds a time-aware team-strength feature.

## 6. Tactical behaviour labels

`src/features/strategy_labels.py` creates transparent proxies for responses
such as width, third-man combinations, direct diagonals, and counter-pressing.
These are not claims that event data can observe every coaching instruction;
they are reproducible operational definitions.

## 7. Possession-value model

`src/models/value_model.py` fits the baseline models and XGBoost regressor.
`src/models/calibration.py` fits isotonic calibration on validation data and
reports calibration error. `src/evaluation/metrics.py` evaluates RMSE, MAE,
R-squared, and calibration.

## 8. Tactical-state model

`src/models/tactical_states.py` prepares possession context, fits K-means,
assigns football-readable state names, and exposes the state profiles shown in
the dashboard.

## 9. Adjustment estimation

`src/models/adjustments.py` estimates state-by-adjustment value using propensity
weighting and a doubly robust estimator. It calculates match-clustered
bootstrap intervals and assigns confidence labels based on sample size,
calibration, and temporal evidence.

## 10. Temporal evaluation

`src/evaluation/temporal.py` keeps matches, rather than individual rows, inside
one chronological split. `src/evaluation/error_analysis.py` identifies
successes and failures. `src/evaluation/ablation.py` measures what changes when
feature groups are removed.

## 11. Decision layer

`src/decision/recommender.py` ranks adjustments and creates coach-facing
recommendations. `src/decision/coach_text.py` converts structured estimates
into plain language while retaining uplift, interval, sample size, risk, and
execution requirements.

## 12. Pipeline and reports

`src/pipeline/run_all.py` orchestrates the full run and writes the processed
artefacts. `src/reporting/pdf.py` creates technical, coach, recruitment, and
opponent reports from those artefacts. This keeps the dashboard and PDFs based
on the same versioned outputs.

## 13. Dashboard

`app/Home.py` introduces the project and displays the headline result.
`app/pages/1_Match_Explorer.py` shows match-level context and sequences.
`app/pages/2_Recommendations.py` ranks adjustment options.
`app/pages/3_Validation.py` exposes quality and evaluation evidence.
`app/pages/4_Model_Card.py` explains the model and limitations.
`app/pages/5_Human_in_the_Loop.py` records analyst and coach feedback.
`app/utils.py` provides cached artefact loading shared by the pages.

## 14. Verification

The tests in `tests/test_pipeline.py` cover the synthetic pipeline, validation,
possession construction, modelling, and temporal splitting. CI additionally
runs linting, report generation, a synthetic pipeline smoke test, and a
Docker build.

## The explanation order

When presenting this project, I start with the decision question, then explain
the ontology, data contract, temporal split, calibrated model, causal
adjustment estimate, uncertainty, dashboard, and limitations. I do not start
with a library name or a performance number because those are implementation
details of a football decision workflow.