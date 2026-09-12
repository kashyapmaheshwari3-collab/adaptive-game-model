"""Validation - temporal split, baselines, calibration, error analysis, ablation."""

import streamlit as st

from app.utils import load_artefacts

st.set_page_config(page_title="Validation", page_icon="🧪", layout="wide")
st.title("Model Validation")
st.caption("Future matches are the test set - never random splits.")

a = load_artefacts()
ev = a["evaluation"]
err = a["error_analysis"]
abl = a["ablation"]

st.subheader("Baselines (out-of-time test set)")
metrics = ev.get("metrics", {})
rows = []
for name, m in metrics.items():
    rows.append(
        {
            "Model": name,
            "RMSE": round(m.get("rmse", 0), 4),
            "MAE": round(m.get("mae", 0), 4),
            "R2": round(m.get("r2", 0), 3),
            "n": m.get("n", 0),
        }
    )
st.dataframe(rows, use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    st.subheader("Calibration (deciles)")
    cal = ev.get("calibration_test", {})
    st.markdown(f"**ECE = {cal.get('ece', 0):.4f}** (MSE {cal.get('mse', 0):.5f})")
    bins = cal.get("bins", [])
    if bins:
        st.line_chart(
            {"pred": [b["pred_mean"] for b in bins], "actual": [b["actual_mean"] for b in bins]}
        )
with c2:
    st.subheader("Temporal split")
    ts = ev.get("temporal_split", {})
    st.markdown(f"Train matches: {ts.get('train', 0)}")
    st.markdown(f"Validation matches: {ts.get('val', 0)}")
    st.markdown(f"Test matches: {ts.get('test', 0)}")
    np_ = ts.get("n_possessions", {})
    st.markdown(
        f"Possessions - train {np_.get('train', 0)} / val {np_.get('val', 0)} / test {np_.get('test', 0)}"
    )

st.subheader("Error analysis")
st.markdown("**Three worst failures (why + what data would fix them):**")
for f in err.get("failures", [])[:3]:
    st.markdown(
        f"- {f.get('team')} vs {f.get('opponent')} (min {f.get('minute')}): "
        f"actual {f.get('actual_epv'):.3f} vs predicted {f.get('pred_epv'):.3f} - "
        f"_{f.get('explanation', '')}_"
    )
st.markdown("**Three best predictions:**")
for s in err.get("successes", [])[:3]:
    st.markdown(
        f"- {s.get('team')} vs {s.get('opponent')} (min {s.get('minute')}): "
        f"residual {s.get('residual'):+.3f}"
    )

st.subheader("Ablation")
ab = abl.get("ablation", {})
if ab:
    st.dataframe(
        [{"Feature group": k, "RMSE": round(v.get("rmse", 0), 4), "R2": round(v.get("r2", 0), 3)}
         for k, v in ab.items()],
        use_container_width=True,
    )

st.subheader("Match-drop sensitivity")
sens = abl.get("match_drop_sensitivity", {})
if sens:
    for k, v in sens.items():
        rng = v.get("estimate_range")
        st.markdown(
            f"- **{k}**: spread {v.get('spread', 0):.4f} "
            f"(range {rng[0]:+.4f}..{rng[1]:+.4f}) -> {'stable' if v.get('stable') else 'UNSTABLE'}"
        )
