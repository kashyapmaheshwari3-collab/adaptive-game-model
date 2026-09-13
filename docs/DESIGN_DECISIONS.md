# Design decisions

This document records the decisions I made while turning the Adaptive Game
Model into a usable football analytics product. It is intentionally written in
plain language: I should be able to explain each choice in an interview, and a
future analyst should be able to challenge or replace it.

## 1. The decision comes before the model

I did not start with “which algorithm gives the best score?” The product
question is:

> Given the opponent's observed structure, which adjustment should we consider
> for the next phase?

That question determines the rest of the design. A descriptive pass map can be
useful, but it does not by itself tell a staff member what to try next.

## 2. I chose event data deliberately

The first version uses StatsBomb Open Data because it is reproducible,
documentable, and accessible to someone reviewing the repository. It is not a
tracking-data system. That means I can reason about on-ball actions and
possession sequences, but I cannot claim to observe every off-ball movement,
pressure angle, or exact spacing relationship.

This boundary is a product decision, not an accidental omission. A tracking
adapter is a future extension once the data licence and schema are available.

## 3. I defined the football ontology before fitting models

Possessions, zones, progression, tactical states, and outcome levels are
defined before the model is trained. The 0–5 possession outcome scale gives the
pipeline a common target:

- 0: lost before progression
- 1: retained without meaningful progression
- 2: reached an advanced zone
- 3: created a dangerous action
- 4: created a shot
- 5: created a high-value shot

This makes the work auditable. If a coach disagrees with a definition, the
definition can be changed and the full pipeline rerun.

## 4. I use a calibrated baseline-plus-model approach

The model comparison includes league-average, Elo-only, linear, raw XGBoost,
and calibrated XGBoost predictions. I selected gradient boosting because it
handles mixed football features and nonlinear interactions without making the
dashboard impossible to explain.

I calibrate the production prediction rather than presenting raw model output.
For this use case, a slightly less accurate but well-calibrated estimate is
more useful than a sharper-looking estimate whose confidence is unreliable.

## 5. I validate time, not just rows

Football actions from the same match are correlated. A random row split could
place nearly identical contexts in both training and testing. I therefore sort
matches chronologically and keep every possession from a match in one split:
24 training matches, 8 validation matches, and 8 future test matches in the
current run.

The test set is reserved for the final evaluation. Leakage checks are an
automated validation gate, not a manual promise.

## 6. I treat tactical adjustment as an observational comparison

Teams do not choose tactical responses at random. Directly comparing outcomes
could simply reward the teams, players, or scorelines associated with a
particular response. I therefore use propensity weighting and a doubly robust
estimator, then attach match-clustered bootstrap intervals.

This does not magically create a randomised experiment. It makes the
assumptions visible and reduces measured confounding. The recommendation
should still be treated as historical evidence, not a guarantee.

## 7. I name clusters with football language

K-means is useful for discovering recurring shapes in a small prototype, but
“Cluster 7” is not a useful coaching output. I use football prototypes to
name the states and keep the state definitions inspectable. A future version
could replace K-means with a probabilistic or sequence model without changing
the dashboard contract.

## 8. I put uncertainty into the product

Every recommendation carries an estimated uplift, confidence interval, sample
size, confidence label, risk, execution requirement, and applicability limit.
This prevents a small or unstable subgroup from being presented as a universal
instruction.

## 9. I keep a human in the loop

The dashboard is designed for an analyst or coach to challenge the output.
Comments, overrides, feedback, confidence adjustments, and video evidence are
part of the workflow. The system supports a decision; it does not make the
matchday decision.

## 10. What I would do next

My next technical priorities would be:

1. Add more seasons and competitions and test cross-league generalisation.
2. Add a tracking-data adapter with separate validation rather than silently
   mixing incompatible data.
3. Expand leave-one-match-out sensitivity for every recommendation.
4. Link recommendations to video clips and analyst-confirmed tactical labels.
5. Compare the current model with a sequence model only after the ontology and
   validation remain stable.

## How to talk about ownership

I can honestly say:

> I am responsible for the product question, football ontology, feature
> definitions, validation design, uncertainty requirements, deployment choices,
> and the interpretation of the results. I can walk through the implementation
> module by module and explain where the system is strong, where it is weak,
> and what I would change with club data.

That is stronger than claiming the prototype is more mature or more
independent than it really is.