"""Tactical adjustment labels (Phase 4).

Each possession is labelled with the adjustment strategies that were actually
observed in it. Labels are transparent, rule-based proxies derived from event
geometry - they are NOT model predictions - so the causal estimation step can
compare observed outcomes across strategies inside the same tactical state.

The proxies are documented in ``docs/data_dictionary.md`` and
``docs/methodology.md``; each can be inspected and overridden by an analyst
(human-in-the-loop design).
"""

from __future__ import annotations

import pandas as pd

from src.config import CENTRAL_BAND, HALF_SPACE_LEFT, HALF_SPACE_RIGHT, TOUCHLINE_BAND


def _label_strategy_flags(possessions: pd.DataFrame, pass_agg: pd.DataFrame) -> pd.DataFrame:
    """Merge possession-level strategy flags from a per-possession pass aggregate."""
    flags = pass_agg[
        [
            "match_id",
            "possession",
            "fb_inversion",
            "wide_final_third",
            "far_side_half_space",
            "third_man_combos",
            "risky_central_share",
            "central_buildup_share",
        ]
    ]
    df = possessions.merge(flags, on=["match_id", "possession"], how="left").fillna(
        {
            "fb_inversion": 0,
            "wide_final_third": 0,
            "far_side_half_space": 0,
            "third_man_combos": 0,
            "risky_central_share": 0.0,
            "central_buildup_share": 0.0,
        }
    )

    df["s_build_up_shape_three_two_five"] = (
        (df["start_x"] < 40) & (df["n_passes"] >= 6) & (df["central_buildup_share"] >= 0.35)
    ).astype(int)
    df["s_fullback_inversion"] = (df["fb_inversion"] > 0).astype(int)
    df["s_increase_winger_width"] = (df["wide_final_third"] > 0).astype(int)
    df["s_attack_far_side_half_space"] = (df["far_side_half_space"] > 0).astype(int)
    df["s_third_man_combination"] = (df["third_man_combos"] > 0).astype(int)
    df["s_reduce_risky_central_passes"] = (df["risky_central_share"] < 0.25).astype(int)
    df["s_aggressive_counterpress"] = (
        (df["counterpress_flags"] > 0)
        | ((df["recovery_type"].isin(["interception", "ball_recovery"])) & (df["start_x"] >= 50))
    ).astype(int)
    df["s_mid_block_retreat"] = (
        (df["start_x"] < 35) & (df["n_passes"] <= 3) & (df["net_progress_x"] < 25)
    ).astype(int)
    return df


def label_strategies(possessions: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Compute adjustment-strategy labels for every possession."""
    if possessions.empty:
        return possessions.copy()

    passes = events[(events["type"] == "pass") & events["possession"].notna()].copy()
    passes = passes.sort_values(
        ["match_id", "possession", "event_seconds", "timestamp", "index"]
        if "index" in passes.columns
        else ["match_id", "possession", "event_seconds", "timestamp"]
    )

    if not passes.empty and "event_seconds" not in passes.columns:
        passes["event_seconds"] = 0.0

    def agg_grp(grp: pd.DataFrame) -> dict:
        end_central = grp["end_y"].apply(lambda v: pd.notna(v) and in_central_local(v))
        end_hs = grp["end_y"].apply(lambda v: pd.notna(v) and in_half_space_local(v))
        fb_zone = (
            (grp["x"] >= 15)
            & (grp["x"] <= 55)
            & ((grp["y"] < TOUCHLINE_BAND) | (grp["y"] > 80 - TOUCHLINE_BAND))
        )
        inversion = fb_zone & end_central & (grp["end_x"] > grp["x"])
        wide_ft = (grp["end_x"] > 50) & (
            (grp["end_y"] < TOUCHLINE_BAND) | (grp["end_y"] > 80 - TOUCHLINE_BAND)
        )
        switch = (grp["pass_switch"] == True) | ((grp["end_y"] - grp["y"]).abs() > 22)  # noqa: E712
        far_hs = switch & end_hs & (grp["end_x"] > 62)
        risky = end_central & (grp["under_pressure"] == True)  # noqa: E712
        central_passes = grp["end_y"].apply(lambda v: pd.notna(v) and in_central_local(v))

        # third-man combos: three consecutive short passes (length < 18m)
        combos = 0
        lens = grp["pass_length"].dropna().values
        if len(lens) >= 3:
            combo_flags = (lens[:-2] < 18) & (lens[1:-1] < 18) & (lens[2:] < 18)
            combos = int(combo_flags.sum())

        return {
            "fb_inversion": int(inversion.sum()),
            "wide_final_third": int(wide_ft.sum()),
            "far_side_half_space": int(far_hs.sum()),
            "third_man_combos": combos,
            "risky_central_share": float(risky.sum() / max(int(central_passes.sum()), 1)),
            "central_buildup_share": float(
                ((grp["end_x"].between(40, 60)) & end_central).sum() / max(len(grp), 1)
            ),
        }

    def in_central_local(y):
        return CENTRAL_BAND[0] <= y <= CENTRAL_BAND[1]

    def in_half_space_local(y):
        return (HALF_SPACE_LEFT[0] <= y < HALF_SPACE_LEFT[1]) or (
            HALF_SPACE_RIGHT[0] <= y < HALF_SPACE_RIGHT[1]
        )

    if passes.empty:
        agg = pd.DataFrame(
            {
                "match_id": [],
                "possession": [],
                "fb_inversion": [],
                "wide_final_third": [],
                "far_side_half_space": [],
                "third_man_combos": [],
                "risky_central_share": [],
                "central_buildup_share": [],
            }
        )
    else:
        agg = (
            passes.groupby(["match_id", "possession"], sort=False)
            .apply(lambda g: pd.Series(agg_grp(g)), include_groups=False)
            .reset_index()
        )

    return _label_strategy_flags(possessions, agg)
