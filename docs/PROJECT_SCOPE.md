# Project Scope — What This Does, What It Doesn't, Who It's For

**The honest, complete answer to: *"What exactly is this project?"*** Use this
file to set expectations before anyone evaluates the system — including
yourself. It is deliberately explicit about limits, because in football
analytics, *knowing the limits* is the professional credential.

---

## 1. What the project does

The **Adaptive Game Model** is a **tactical decision-support engine**, not a
prediction tool. Given a team's current game model and the opponent's observed
structure, it estimates: **which tactical adjustment is most likely to improve
the value of our next possession?**

It does this in five steps:

1. **Understands every possession** — events are grouped into attacking phases
   and scored on a 0–5 outcome ladder (lost before progression → high-value
   shot) — see `docs/data_dictionary.md`.
2. **Values the possession** — a calibrated model estimates the expected value
   of each possession state (goal-probability units, "EPV").
3. **Names the situation** — possessions are clustered and labelled with
   football language, never "Cluster 7": opponent low block, opponent high
   press, wide overload, final third vs compact defence, neutral build-up, etc.
4. **Estimates the adjustment value** — for each tactical state, it compares
   alternative responses (third-man combination, full-back inversion, wider
   winger, aggressive counter-press, mid-block retreat...) using **causal
   methods** (inverse probability weighting + doubly-robust AIPW) to correct for
   the fact that teams don't choose tactics randomly.
5. **Speaks the coach's language** — every recommendation carries an expected
   benefit, a **95% confidence interval**, a sample size, the main risk, the
   execution requirement, and a high/medium/low confidence label.

Example output (real, from the La Liga run):

> "Against **neutral build-up**, adopting **mid-block retreat after loss**
> historically created **+0.0162 EPV per possession** (95% CI
> [+0.0136, +0.0197]) with **medium confidence**, based on 311 comparable
> sequences. Risk: concedes territorial control. Execution: structural."

Also included: match explorer, event-sequence examples, data-quality
validation dashboard, model card, error analysis, and a **human-in-the-loop**
layer (analyst comments, scout override, coach feedback).

## 2. What the project does NOT do (read this twice)

| It does not... | Because / what it does instead |
|---|---|
| Predict match winners or final scores | That's a different problem class. This models *decisions within* matches. |
| Use tracking/GPS data | Deliberate: event data is public, reproducible, licence-clean. This is an **event-based** system. A tracking-data version is a future extension, not a hidden gap. |
| Guarantee a tactic works | Nothing in football can. It reports *historical expected value with uncertainty* — a recommendation is a hypothesis with evidence, not a certainty. |
| Replace a coach's judgement | It supports it. The human-in-the-loop design assumes a human always makes the final call. |
| Cover every league/opponent | Estimates are only as good as the data they were trained on (currently La Liga 2015/16). It generalises *methodologically*, not automatically in absolute value terms. |
| Run live/in-match from streaming feeds | It is a batch system: pre-match and post-match analysis on complete event data. |
| Value players or predict transfers | Out of scope by design. |
| Tell you the "optimal formation" as a fact | Formations are inputs/proxies; the system reasons about *behavioural states and adjustments*. |

## 3. Who should use it (and how)

| Persona | How they use it |
|---|---|
| **Head coach / assistant coach** | Pre-match: which adjustment against this opponent's structure. In-match: what's changed, what to try next. |
| **Performance/tactical analyst** | Opponent profiling, sequence evidence, "what-if" scenario exploration. |
| **Head of analytics / data scientist** | The pipeline, model card, calibration, ablation, error analysis — the craft behind the output. |
| **Sporting director / Head of recruitment** | Evidence about a squad's *adaptability* — how a team/system can change behaviour, which informs recruitment and manager decisions. |
| **Anyone evaluating an analyst** | The full craft on display: engineering, causality, uncertainty, executive communication, deployment. |

The design principle: **executives get one page, analysts get the sequence
evidence, data scientists get the model card** — all from the same artefacts.

## 4. Expectations to set up front (your 30-second pitch)

- "This is a **context-aware tactical adjustment engine** built on public
  event data — it asks *what should we change next*, not *who wins*."
- "It's **event-based, not tracking-based**, and I'm explicit about that."
- "Every recommendation ships with **uncertainty** — confidence interval,
  sample size, risk — because that's what makes it useful to a coaching staff."
- "Validation is **temporal and match-level** — future matches as the test
  set — with calibration, ablation, sensitivity, and error analysis."
- "The **human stays in the loop**; this is decision support, not autopilot."

## 5. Design decisions worth defending

1. **Causal framing, not correlation** — teams don't randomise tactics, so we
   use IPW + doubly-robust estimation instead of naive averages.
2. **Calibration over headline accuracy** — ECE 0.004; a calibrated model is
   what a coach can actually trust.
3. **Named tactical states** — football language ("opponent low block") instead
   of cluster numbers, so a coach can act on it.
4. **Uncertainty on everything** — CI, sample size, coverage, applicability
   limits; uncertainty is a feature, not a failure.
5. **Human-in-the-loop** — comments, overrides, feedback fields are first-class
   citizens, not afterthoughts.
6. **Honest scope** — event data, batch, La Liga PoC, non-commercial data
   licence — all stated up front in the README, docs, and model card.

## 6. Known limitations (own them — it's the credibility move)

- Event data has no spatial pressure/tracking context.
- Adjustment labels are transparent rule-based proxies of coaching concepts.
- Estimates are historical expectations with uncertainty, not guarantees.
- Applicability is limited to opponents/leagues represented in training data.
- Small samples yield low-confidence recommendations *by design* (and the UI
  says so).

## 7. FAQ — common questions and direct answers

**Q: Is this just another passing-plot project?**
No — passing maps are descriptive. This is a *decision engine*: it detects a
situation, compares alternative tactical responses, and reports the expected
change in possession value with uncertainty.

**Q: Without tracking data, is it even credible?**
Yes — and the claim is scoped: event data is sufficient for possession-level
tactical state detection and adjustment estimation. Tracking data would refine
it, and the architecture isolates that as a future data-source extension.

**Q: Why not just train a neural net?**
Because the goal is *usable, trustworthy, explainable* output for coaching
staff. A well-calibrated gradient-boosted model with named states, CIs, and
error analysis beats an opaque network for this decision task. The build plan
documents neural/sequence models as an advanced comparison extension.

**Q: Won't good teams dominate the recommendations?**
Possible in principle — that's why we report per-state sample sizes, use
causal correction (IPW/AIPW), and include match-drop sensitivity. It's a known
limitation, tracked explicitly.

**Q: Does it work for any league?**
Methodologically yes. Numerically, re-train on that league's data first
(one command with StatsBomb Open Data; the same schema for proprietary data).
