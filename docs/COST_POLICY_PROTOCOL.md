# Exploratory cost-aware THARUN candidate

Specified 2026-10-23 after the unfavorable v0.1 threshold pilot, before fitting
this candidate. This is method development informed by earlier diagnostics, not
a preregistered confirmatory test. The original model, thresholds and results
stay unchanged. Any final claim requires new, independently reviewed test data.

## Candidate

Fit two regularized logistic models on training families only:
1. Expected normalized severity loss under execution (soft [0,1] target).
2. Probability of verified safe eligible completion under execution.

Non-execution choices terminate the present simulator: immediate external harm
and completion are therefore structurally zero. Do not fabricate a successful
clarification or hypothetical approval. This means the method is an immediate
intervention policy, not a learned long-horizon model of human responses.

At each observation, minimize predicted declared cost + lambda * predicted loss
- gamma * predicted utility over policy-admissible actions. Policy, authority,
approval and exact intent constraints are hard. Clarify is eligible for missing
information/low evidence; staging is a non-mutating option; escalation requires
an available reviewer; refusal is always available. No oracle enters this choice.

Declared cost units (assumptions, not measured dollars or time): EXECUTE 0,
CLARIFY 1, STAGE 2, ESCALATE 3, REFUSE 4. These numbers need sensitivity analysis
and user/operator validation before a substantive cost claim.

Calibrate lambda in {0,.25,.5,1,2,4,8,16,32,64,128} and gamma in {0,1,2,4} on
calibration families only. Select minimum actual mean declared intervention cost
subject to empirical mean severity loss <= .05 and useful autonomy >= .5.
Break ties by lower loss, then greater autonomy, then smaller multipliers. If no
candidate is feasible, fail fitting explicitly; never label an infeasible policy
as meeting a risk budget. Record all grid outcomes.

This is a complete executable candidate policy, not a proof of calibrated safety.
There is no conformal/conditional/shift guarantee. Only terminal outcomes exist
for interventions in this simulator. The original threshold controller remains
a separate comparison. Hold-out diagnosis on these already-seen task templates
is exploratory regardless of whether the resulting numbers improve.

Follow-up exploratory diagnosis: sweep alpha in {0,.01,.025,.05}, keeping the
same multiplier grid and utility floor. This grid is a post-pilot sensitivity
analysis, not a source of a test-selected winner. Record infeasible calibration
policies and out-of-budget held-out outcomes. A zero selected risk multiplier
means the fitted objective ignores the risk model, which must be stated.
