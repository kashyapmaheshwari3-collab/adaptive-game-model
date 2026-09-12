# Methodology - Adaptive Game Model

**Project title:** Adaptive Game Model: A Context-Aware Tactical Adjustment Engine for Football

**Research question:** Can a model identify which tactical adjustments increase the quality of a team's next possession against different defensive structures?

**Explicit scope statement:** This is an *event-based* tactical decision model, not a complete tracking-data system. It does not use player tracking or physical data.

---

## 1. The decision problem

We do not predict "who wins". We answer:

> Given the opponent's structure and our current game model, which tactical adjustment is most likely to improve our next attacking or defensive phase?

This frames tactical analysis as a **decision problem with counterfactual reasoning**: for a detected tactical state, we estimate the counterfactual value of alternative responses, with explicit uncertainty.

## 2. Phase 1 - Tactical vocabulary

For each possession we compute or infer: starting/ending zone, number of passes, direction of progression, midfield crossing, final-third entry, shot production, defensive pressure proxy, opponent formation, scoreline, minute, home/away, and numerical context where inferable. Outcomes are mapped to the 0-5 scale (see Data Dictionary). This ontology lives in `src/config.py` so every module shares one vocabulary.

## 3. Phase 2 - Possession value model

**Target - Expected Possession Value (EPV):**

```
EPV = E[goal value created by this possession]
      - E[transition exposure if the ball is lost in an advanced area]
```

Measured in goal-probability units per possession. Constructed from the 0-5
outcome scale: shots contribute their xG, dangerous actions a calibrated
baseline, and early losses in advanced areas carry a transition cost.

**Features (ex-ante, all observable at possession start):**
start location, recovery type, play pattern, minute, period, home/away,
scoreline, formations, Elo ratings (team / opponent / difference), and
first-action pressure. Using only ex-ante features avoids look-ahead leakage
into the value estimate.

**Models:** XGBoost regressor with isotonic calibration; baselines: league
average, linear regression, Elo-only regression, dummy regressor.

**Evaluation:** log-style MSE/RMSE, calibration curves, expected calibration
error (ECE), and **strictly chronological** train/val/test splits at match
level (never random splits; never mixing actions from the same match).

> A model with slightly lower accuracy but excellent calibration is more useful to a coaching staff than an opaque model with impressive headline accuracy.

## 4. Phase 3 - Tactical state detection

Unsupervised clustering (KMeans) over possession descriptors discovers repeated
patterns; clusters are then **named by football prototypes** (hand-built,
canonical, raw-unit prototypes per state; a centroid is assigned to its nearest
prototype under weighted feature distance). States are never presented as
"Cluster 7" - each carries a coaching-language name and description:

| State | What it looks like |
|---|---|
| `opponent_low_block` | Deep block, denies central access, invites wide circulation |
| `opponent_high_press` | Aggressive press, central access denied, high turnovers |
| `narrow_front_two_buildup` | Front two stay narrow; full-backs gain space |
| `defensive_transition_after_loss` | Ball just lost, structure unsettled, numbers in flux |
| `wide_overload` | Play concentrated on one flank; far side opens |
| `central_progression` | Advancing between opponent lines |
| `final_third_vs_compact_defence` | Final-third attack vs compact block; half-spaces key |
| `neutral_buildup` | Routine build-up, neither side committed |

Prototype matching is transparent and explainable; each mapping can be
inspected and overridden by an analyst.

## 5. Phase 4 - Adjustment value estimation

For every (state x adjustment) cell we estimate the Average Treatment Effect
(ATE) of *using* the adjustment on possession EPV:

1. **Propensity scores** - logistic regression over ex-ante covariates
   (location, minute, scoreline, home/away, Elo difference).
2. **Stabilised inverse-probability weighting (IPW)** - ATE estimator with
   overlap clipping to a positivity floor.
3. **Doubly robust (AIPW)** - outcome-model plug-in plus IPW residual
   correction; consistent if *either* the propensity or the outcome model is
   correct.
4. **Match-clustered bootstrap** - resample whole matches (not events) to
   respect within-match correlation; produces the 95% confidence interval.
5. **Diagnostics** - positivity (min propensity), overlap, sample size,
   calibration ECE, temporal gap, and match-drop stability feed a
   `high`/`medium`/`low` confidence label.

**Selection-bias note:** teams do not choose tactics randomly - stronger teams
may select certain actions more often, and scoreline affects behaviour. The
covariates in the propensity model explicitly control for team strength
(Elo) and match context, which mitigates the most important confounders in
public event data. Remaining unobserved confounding is disclosed in the
sensitivity analysis and known limitations.

**Output contract** (every estimate ships with): estimated value, confidence
interval, sample size, comparable situations, main risk, execution
requirement, applicability limits.

## 6. Phase 5 - Coach-facing output

Recommendations are written in coaching language, e.g.:

> "Against **opponent low block**, adopting **attack the far-side half-space**
> historically created **+0.018 expected possession value per possession**
> (95% CI [+0.002, +0.034]) with **medium confidence**, based on 47
> comparable sequences."

They never claim "this tactic will definitely work".

## 7. Phase 6 - Testing

- Chronological splitting only (train on earlier matches, validate/test on later).
- Match-level holdout: no action from a match appears in two splits (leakage check).
- Baseline comparisons, calibration, ablation (drop Elo / match context / location).
- Error analysis: 3 successes, 3 failures, why, and which data would fix them.
- Match-drop sensitivity: are recommendations stable when matches are removed?
- Honesty about dominant-team bias: Elo-conditioned features and league-specific
  validation make over-recommendation of elite teams explicit.

## 8. Human-in-the-loop

The dashboard supports analyst comments, scout override, coach feedback,
confidence adjustment, video evidence links, and tactical assumptions; all
recorded to `data/processed/hitl_log.json` (see README).

## 9. Known limitations

1. Event-based: no tracking data (space, timing, off-ball movement).
2. Strategy labels are transparent proxies of coaching concepts; they are not
   perfect encodings of a coach's intent.
3. Historical expectation, not guarantee; confidence intervals are honest.
4. Applicability limited to opponents/leagues represented in training data.
5. Small samples yield low-confidence recommendations by design.
