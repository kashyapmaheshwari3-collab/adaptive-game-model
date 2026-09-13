"""Run the full pipeline end-to-end.

Pipeline::

    raw data -> validation -> cleaning -> event standardisation
        -> feature engineering -> model training -> model evaluation
        -> decision output -> dashboard/report

Every stage writes artefacts to ``data/processed`` so the Streamlit app and
report generator are pure consumers.

Usage::

    python -m src.pipeline.run_all                     # real data if available
    python -m src.pipeline.run_all --synthetic         # force synthetic data
    python -m src.pipeline.run_all --quick             # fast mode (CI smoke)
"""

from __future__ import annotations

import argparse
import json
import logging
import time

import joblib
import pandas as pd

from src.config import (
    DEFAULT_COMPETITION,
    DEFAULT_RANDOM_STATE,
    DEFAULT_SEASON,
    PROCESSED_DIR,
    RAW_SB_DIR,
)
from src.decision import build_recommendations, overall_recommendation
from src.ingestion import build_manifest, load_events_frame, load_matches_frame, write_manifest
from src.synthetic import generate_synthetic_dataset

log = logging.getLogger("agm.pipeline")


def _load_data(
    use_synthetic: bool, competition: int, season: int
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Load real StatsBomb data if present, otherwise generate synthetic."""
    sb_dir = RAW_SB_DIR / str(competition) / str(season)
    has_events = any((sb_dir / "events").glob("*.json")) if (sb_dir / "events").exists() else False
    if not use_synthetic and has_events:
        log.info("Loading StatsBomb Open Data: competition=%s season=%s", competition, season)
        matches = load_matches_frame(competition, season)
        events = load_events_frame(competition, season)
        # only keep matches whose event files were actually downloaded
        with_events = set(events["match_id"].unique())
        matches = matches[matches["match_id"].isin(with_events)].reset_index(drop=True)
        provenance = {
            "data_source": "statsbomb_open_data",
            "competition_id": competition,
            "season_id": season,
        }
    else:
        log.warning(
            "No raw StatsBomb data found - using deterministic SYNTHETIC data (offline fallback)."
        )
        matches, events = generate_synthetic_dataset(n_matches=24, seed=DEFAULT_RANDOM_STATE)
        provenance = {"data_source": "synthetic", "note": "offline/CI fallback generator"}
    return matches, events, provenance


def run_pipeline(
    use_synthetic: bool = False,
    quick: bool = False,
    competition: int = DEFAULT_COMPETITION,
    season: int = DEFAULT_SEASON,
) -> dict:
    """Execute every pipeline stage and persist artefacts. Returns a summary."""
    t0 = time.time()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # ---------------------------------------------------------------- data
    matches, events, provenance = _load_data(use_synthetic, competition, season)
    manifest = build_manifest(competition, season, matches, events, provenance)
    write_manifest(manifest)
    log.info(
        "Loaded %d matches, %d events (%s)",
        matches["match_id"].nunique(),
        len(events),
        provenance["data_source"],
    )

    # ----------------------------------------- standardise / enrich events
    from src.features import enrich_events

    events = enrich_events(events, matches)

    # ------------------------------------------------------------------- features
    from src.features import build_possessions, elo_features, label_strategies

    possessions = build_possessions(events)
    possessions = elo_features(possessions, matches)
    possessions = label_strategies(possessions, events)
    log.info("Built %d possessions", len(possessions))

    # -------------------------------------------------------------- validation
    from src.evaluation import split_possessions
    from src.validation import save_validation_report, validation_report

    train, val, test, split_report = split_possessions(
        possessions, matches, val_frac=0.2, test_frac=0.2
    )
    val_report = validation_report(events, matches, train, test)
    save_validation_report(val_report)
    log.info(
        "Validation: %s (%d errors, %d warnings)",
        val_report["status"],
        val_report["n_errors"],
        val_report["n_warnings"],
    )

    # ------------------------------------------------------------- value model
    from src.models.value_model import fit_calibrator, fit_value_models, predict_epv

    xgb, _, baselines = fit_value_models(train, random_state=DEFAULT_RANDOM_STATE)
    calibrator = fit_calibrator(xgb, val)
    pred_test = predict_epv(xgb, test, calibrator)
    pred_val = predict_epv(xgb, val, calibrator)

    # ------------------------------------------------------------- evaluation
    from src.evaluation import error_analysis, evaluate_all_models
    from src.models.calibration import calibration_metrics

    metrics = evaluate_all_models(train, val, test, xgb, calibrator, baselines)
    calib_test = calibration_metrics(test["epv"].astype(float).values, pred_test)
    calib_val = calibration_metrics(val["epv"].astype(float).values, pred_val)
    err_analysis = error_analysis(test, pred_test)

    evaluation_report = {
        "metrics": metrics,
        "calibration_test": calib_test,
        "calibration_val": calib_val,
        "temporal_split": split_report,
        "data_source": provenance["data_source"],
        "n_matches": int(matches["match_id"].nunique()),
        "n_possessions": int(len(possessions)),
        "league_average_epv": float(baselines.league_average_epv),
    }
    (PROCESSED_DIR / "evaluation_report.json").write_text(
        json.dumps(evaluation_report, indent=2, default=str), encoding="utf-8"
    )
    (PROCESSED_DIR / "error_analysis.json").write_text(
        json.dumps(err_analysis, indent=2, default=str), encoding="utf-8"
    )
    (PROCESSED_DIR / "temporal_split.json").write_text(
        json.dumps(split_report, indent=2), encoding="utf-8"
    )
    log.info(
        "Value model RMSE (test) = %.4f, ECE = %.4f",
        metrics["xgboost_calibrated"]["rmse"],
        calib_test["ece"],
    )

    # --------------------------------------------------------- tactical states
    from src.models.tactical_states import fit_tactical_states

    # State detection is DESCRIPTIVE clustering: fit on the full possession frame
    # so the final artefact carries stable names. The causal adjustment step
    # below runs on the train split only.
    n_clusters = 6 if not quick else 5
    states_all, cluster_map, kmeans, _ = fit_tactical_states(
        possessions, n_clusters=n_clusters, random_state=DEFAULT_RANDOM_STATE
    )
    possessions["tactical_state"] = states_all.values
    train["tactical_state"] = possessions.loc[train.index, "tactical_state"].values
    joblib.dump(kmeans, PROCESSED_DIR / "state_model.joblib")
    json.dump(
        cluster_map, (PROCESSED_DIR / "cluster_map.json").open("w", encoding="utf-8"), indent=2
    )

    state_profiles = (
        possessions.groupby("tactical_state", observed=True)
        .agg(
            n=("epv", "size"),
            baseline_epv=("epv", "mean"),
            pressure_proxy=("pressure_proxy", "mean"),
            n_passes=("n_passes", "mean"),
            net_progress_x=("net_progress_x", "mean"),
            entered_final_third=("entered_final_third", "mean"),
        )
        .reset_index()
    )
    state_profiles.to_csv(PROCESSED_DIR / "state_profiles.csv", index=False)
    log.info(
        "Tactical states detected: %s",
        dict(state_profiles[["tactical_state", "n"]].values.tolist()),
    )

    # ------------------------------------------------------- adjustment values
    from src.models.adjustments import estimate_adjustment_values

    temporal_gap = abs(metrics["xgboost_calibrated"]["rmse"] - metrics["xgboost_raw"]["rmse"])
    adjust_df = estimate_adjustment_values(
        train,
        calibration_ece=calib_val["ece"],
        temporal_gap=temporal_gap,
        n_boot=60 if quick else 200,
        random_state=DEFAULT_RANDOM_STATE,
    )
    adjust_df.to_csv(PROCESSED_DIR / "adjustments.csv", index=False)

    # --------------------------------------------------------- decision output
    recs = build_recommendations(adjust_df)
    recs.to_csv(PROCESSED_DIR / "recommendations.csv", index=False)

    # ablation + match-drop sensitivity (now that adjustment estimates exist)
    from src.evaluation import ablation_and_sensitivity

    ablation = ablation_and_sensitivity(train, test, adjust_df)
    (PROCESSED_DIR / "ablation_report.json").write_text(
        json.dumps(ablation, indent=2, default=str), encoding="utf-8"
    )

    decision_outputs = _build_match_decisions(possessions, matches, recs)
    (PROCESSED_DIR / "decision_outputs.json").write_text(
        json.dumps(decision_outputs, indent=2, default=str), encoding="utf-8"
    )
    log.info("Recommendations computed for %d (state x strategy) pairs", len(recs))

    # --------------------------------------------------------------- model card
    model_card = _build_model_card(
        evaluation_report, err_analysis, ablation, recs, manifest, provenance
    )
    (PROCESSED_DIR / "model_card.json").write_text(
        json.dumps(model_card, indent=2, default=str), encoding="utf-8"
    )

    # --------------------------------------------------------------- artefacts
    events.to_parquet(PROCESSED_DIR / "events.parquet", index=False)
    matches.to_parquet(PROCESSED_DIR / "matches.parquet", index=False)
    possessions.to_parquet(PROCESSED_DIR / "possessions.parquet", index=False)
    joblib.dump(xgb, PROCESSED_DIR / "value_model.joblib")
    joblib.dump(calibrator, PROCESSED_DIR / "calibrator.joblib")

    summary = {
        "status": "PASS",
        "data_source": provenance["data_source"],
        "n_matches": int(matches["match_id"].nunique()),
        "n_events": int(len(events)),
        "n_possessions": int(len(possessions)),
        "n_recommendations": int(len(recs)),
        "rmse_test": float(metrics["xgboost_calibrated"]["rmse"]),
        "ece_test": float(calib_test["ece"]),
        "seconds": round(time.time() - t0, 1),
    }
    log.info("Pipeline finished in %.1fs - %s", summary["seconds"], summary["status"])
    return summary


def _build_match_decisions(
    possessions: pd.DataFrame, matches: pd.DataFrame, recs: pd.DataFrame
) -> dict:
    outputs = {}
    for match_id, sub in possessions.groupby("match_id"):
        state_dist = sub["tactical_state"].value_counts()
        match_row = matches[matches["match_id"] == match_id]
        if match_row.empty:
            continue
        row = match_row.iloc[0]
        match_recs = recs[recs["tactical_state"].isin(state_dist.index)] if not recs.empty else recs
        overall = overall_recommendation(match_recs) if not match_recs.empty else None
        outputs[str(match_id)] = {
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "match_date": str(row["match_date"]),
            "home_score": int(row["home_score"]),
            "away_score": int(row["away_score"]),
            "states": [
                {
                    "state": s,
                    "label": str(s),
                    "count": int(c),
                    "share": round(float(c / len(sub)), 3),
                }
                for s, c in state_dist.items()
            ],
            "overall_recommendation": overall,
        }
    return outputs


def _build_model_card(
    evaluation_report: dict,
    err_analysis: dict,
    ablation: dict,
    recs: pd.DataFrame,
    manifest: dict,
    provenance: dict,
) -> dict:
    return {
        "model": "Adaptive Game Model v1.0",
        "task": "Context-aware tactical adjustment value estimation (event-based)",
        "data": manifest,
        "data_source": provenance,
        "target": "Expected Possession Value (EPV) in goal-probability units",
        "value_model": "XGBoost regressor + isotonic calibration",
        "state_model": "KMeans clustering with rule-based football naming",
        "adjustment_estimator": "Stabilised IPW + doubly-robust (AIPW), match-clustered bootstrap CIs",
        "validation": evaluation_report.get("temporal_split"),
        "metrics": evaluation_report.get("metrics"),
        "calibration": evaluation_report.get("calibration_test"),
        "error_analysis": err_analysis,
        "ablation": ablation.get("ablation"),
        "sensitivity": ablation.get("match_drop_sensitivity"),
        "known_limitations": [
            "Event-based: no player tracking data is used.",
            "Adjustment labels are transparent rule-based proxies of coaching concepts.",
            "Estimates are historical expectations with uncertainty, not guarantees.",
            "Applicability limited to opponents/leagues represented in training data.",
            "Small samples yield low-confidence recommendations by design.",
        ],
        "random_state": DEFAULT_RANDOM_STATE,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Adaptive Game Model pipeline")
    parser.add_argument("--synthetic", action="store_true", help="force synthetic data")
    parser.add_argument("--quick", action="store_true", help="fast mode for CI")
    parser.add_argument("--competition", type=int, default=DEFAULT_COMPETITION)
    parser.add_argument("--season", type=int, default=DEFAULT_SEASON)
    args = parser.parse_args()
    summary = run_pipeline(
        use_synthetic=args.synthetic,
        quick=args.quick,
        competition=args.competition,
        season=args.season,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
