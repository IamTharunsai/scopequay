# ScopeQuay: Risk-Calibrated Selective Autonomy for Tool-Using LLM Agents

**Original working draft, 12 November 2026. Not submission ready.**
Author list, affiliations and venue are not yet confirmed. This draft describes
the implemented system and a synthetic engineering pilot. It does not report a
validated improvement or claim a new safety theorem. Earlier records retain the
previous project name; ScopeQuay is the current public name.

## Abstract

An agent's ability to call a tool does not establish that it should do so.
Consequential actions require decisions about authority, intent, ambiguity,
evidence and recoverability. ScopeQuay studies selective autonomy as a choice
among execution, clarification, staging, escalation and refusal, with additional
recovery decisions after uncertain tool outcomes. We implement fixed and empirical
calibration controllers, a cost-sensitive exploratory candidate, an executable
effect ledger and reproducible fixed-proposal evaluation. The current generator
contains 40 synthetic families and 320 decision points with family-disjoint
training, calibration and test sets and a held-out vocabulary domain. In the
112-point repaired test split, the threshold candidate is more conservative
than the fixed gate. A separate cost candidate exceeds its nominal mean-loss
target on the held-out test split. These observations motivate improvements in
method and task design; they do not establish superiority, independent benchmark
validity or a statistical safety guarantee. A local approval dashboard demonstrates
the workflow separately from the research evaluation.

## 1. Problem and motivation

Tool-using agents can produce effects beyond their text output. A syntactically
valid request may target the wrong resource, lack authority, violate policy, or
repeat an effect after a lost acknowledgment. Conversely, refusing every request
prevents useful work. A practical controller must therefore be evaluated jointly
on restraint and useful completion.

ToolEmu studies risk assessment through language-model-emulated tools [1].
AgentDojo supplies an extensible environment for prompt-injection attacks and
defenses around tools [2]. Tau-bench evaluates tool-agent-user interaction with
domain policies and final database-state checks [3]. These works already establish
that tool-agent risk evaluation and executable/state-based assessment are not
new contributions by themselves. Selective classification explicitly studies
the relation between risk and coverage [4]. Conformal Risk Control gives a
framework for controlling expected monotone loss under its stated assumptions [5].
Our empirical threshold search does not implement that theorem.

The intended contribution is a carefully validated joint evaluation of graded
intervention, useful autonomy and post-failure effects, paired with a controller
that earns an empirically demonstrable trade-off. At present this remains a
research objective. A full-text review of the closest intervention/delegation
papers and contemporary toolkit capabilities is required before asserting a
defensible novelty boundary.

## 2. Research question and hypotheses

**RQ1.** Under matched visible information and a specified severity-weighted
harm budget, can a calibrated controller retain more useful autonomous task
completion than fixed gates, prompt-only controls, trained classifiers and
configured deployable policy engines?

**H1 (unconfirmed).** A calibrated controller has greater useful autonomy than
the strongest matched comparator at the same harmful-action rate or stated
severity-loss constraint. Evaluation must show the full trade-off and include
refuse-all as a diagnostic endpoint.

**RQ2.** How do verification and recovery affect duplicate effects and safe
completion after acknowledgment loss or partial commit?

**H2 (unconfirmed beyond the toy simulator).** Checking observable effect history
before a retry reduces duplicate effects relative to naive retry, at an explicitly
measured completion and intervention cost.

These are continuing research hypotheses. The October pilot outcomes have already
been inspected, so this document is not a preregistration of those outcomes.
Future confirmatory experiments need a frozen protocol and untouched evaluation
families before results are examined.

## 3. Formal setup

Let x be the public observation of a proposed tool action: instruction, requested
and proposed resource, operation and quantity, current authority, explicit policy,
ambiguity, approval requirements, state freshness, reversibility and evidence
features. Hidden oracle labels and injected faults remain evaluator-side.

A policy pi maps x to one of A = {EXECUTE, CLARIFY, STAGE, ESCALATE, REFUSE}.
EXECUTE permits the proposed effect. CLARIFY asks for missing intent. STAGE holds
or prepares an action for checking without committing its external effect.
ESCALATE requests an authorized review. REFUSE terminates a prohibited request.
Recovery choices include VERIFY, RETRY, COMPENSATE, ROLLBACK and HALT.

For episode i, let C_i indicate verified safe completion, E_i indicate a nominally
autonomously feasible reference task, H_i indicate any harmful episode effect,
and s_i in [0,1] be its severity. The current descriptive endpoints are:

- Useful autonomy U = sum_i E_i C_i / sum_i E_i.
- Mean severity loss R = (1/n) sum_i s_i H_i.
- Harmful episode rate = sum_i H_i / n.
- Harmful-action rate = harmful initial or repeat effect events / commit attempts.
- Unjustified refusal = refusals on known safe reference proposals / known safe
  reference proposals, with proposal-label coverage reported separately.
- Duplicate-effect rate is conditioned on exposed injected faults.

Mean severity loss and harmful-action rate are different endpoints. Equal R
does not imply equal action-level harm. The current main optimization uses an
empirical calibration constraint on R, not a guarantee of either endpoint.

The intended optimization is to maximize useful autonomy (or minimize validated
intervention cost) subject to a defensible risk budget. Its operating population,
loss definition, feasibility conditions and statistical assumptions must be stated
before a deployed risk-control claim is possible.

## 4. Implemented candidates

The fixed gate combines explicit authority/policy/approval checks with intent,
state and evidence checks. The threshold candidate trains a regularized logistic
harm score using forced-execution effects on training families, then selects a
threshold on calibration families under an empirical mean-loss limit. Interventions
use visible facts. This is a reference implementation, not a novel learning theorem.

The exploratory five-way candidate selects among admissible interventions using
declared immediate cost plus lambda times predicted loss minus gamma times
predicted useful completion. Multipliers are chosen on calibration data subject
to a utility floor and empirical loss target. Costs are assumed units; terminal
interventions have no imagined successful human response. The learned quantities
do not model long-horizon approval or clarification outcomes. A selected zero
risk multiplier must not be described as evidence that calibrated risk estimation
is useful.

Baselines include ungated execution, static policy, intent/permission checks,
a transparent trained binary classifier, prompt/reviewer modes and refuse-all.
The optional Microsoft core 5.0.0 adapter evaluates only its PolicyEngine slice.
The pinned native Dogwood adapter evaluates a single-request public-fact policy
through its reference CLI. Native toolkit results are mapped to the five labels
by wrappers. These are not evaluations of the full toolkit stacks, identity
systems, temporal-policy coverage or production deployment.

## 5. Environment and evaluation design

The repaired v0.2 fixture contains 40 families, each with eight variants: normal,
ambiguous, unauthorized, policy conflict, approval required, acknowledgment loss,
partial commit and stale state. The 320 points split into 112 training, 56
calibration, 112 test and 40 transfer points. Families do not cross splits.
The eight domain labels are vocabularies over one SQLite effect ledger, not eight
independent realistic APIs. Transfer is therefore vocabulary-level transfer.

Fixed proposals isolate gate decisions. The bounded agent extension lets an
installed local model generate arguments and observe public tool effects.
Wrong generated arguments change the action being evaluated: five-way reference
gold labels cannot automatically grade that modified proposal. New records mark
label applicability; legacy agent label/refusal endpoints without those flags
are omitted in reanalysis. Actual-state completion and harm are separate endpoints.

Clarification, staging and escalation terminate in the benchmark and receive no
fabricated human-success credit. Recovery verifies the ledger after uncertain
outcomes, retries only where appropriate, or compensates and halts. Historical
harm remains counted after compensation. Completion can therefore be below one
even for a correct pre-action gate when safe recovery halts after partial rollback.
Normal and fault slices must be examined separately.

Run manifests bind fixture hashes, configuration, versions and source snapshots.
Outcome files have record hash chains. These are local reproducibility mechanisms,
not independent attestation. The public evidence export retains original synthetic
outcome bytes and source snapshots while redacting machine paths from metadata.

## 6. Observed engineering pilot

The following table is derived from the preserved v0.2 fixed-proposal test records,
with 112 points from 14 families and 42 nominally feasible reference points per
system. It is not a publication model ranking. See evidence/pilot-summary.json
for exact grouping, hashes and the source run for each value.

| Controller / adapter slice | Useful autonomy | Mean severity loss |
|---|---:|---:|
| Fixed reference gate | 0.666667 | 0 |
| Empirical threshold candidate | 0.285714 | 0 |
| Configured Microsoft PolicyEngine slice | 0.666667 | 0 |
| Native Dogwood point-policy slice | 0.666667 | 0 |
| Exploratory cost candidate, alpha = 0.05 | 0.666667 | 0.057357 |

The threshold candidate does not demonstrate H1. The cost candidate exceeds its
0.05 target on test and cannot be reported as satisfying that constraint.
Zero observed severity loss on these synthetic points does not imply zero future
risk. Multiple systems run on the same families are paired observations, not
additional independent task families. Bootstrap summaries are descriptive and
do not establish rare-harm guarantees.

Real local Llama experiments also exist, but their tiny corrected agent cohorts
are not used here to claim broad model generalization. Qwen completed a small
smoke test only. Installed model inventory is not benchmark replication.
Earlier token-feedback leakage runs remain local diagnostic records, explicitly
excluded from clean model comparisons. No result in this section comes from
interactive approvals in the new dashboard.

## 7. Product demonstration and scope

The local single-user dashboard demonstrates a persistent approval queue, explicit
review notes, gate re-evaluation, a separate execution step, simulated recovery
and an exportable hash-chained audit trail. Approval resolves an approval hold;
it does not grant missing authority or override policy. Transactions and revisions
prevent duplicate simulated execution on concurrent clicks. Review notes are
self-declared and do not authenticate reviewer identity. This is a product
demonstration, not a study of human behavior or production effectiveness.

## 8. Limitations and threats to validity

Synthetic labels depend heavily on visible policy facts and may favor rule gates.
Task diversity, cross-domain transfer and sample independence are limited.
There are no independent annotations yet. Intervention costs and human outcomes
are assumed or absent. Only one local model has a benchmark pilot; capacity limits
prevent broad replication on the current laptop. Toolkit coverage is narrow.
Agent label scope and historical metadata leakage require explicit exclusions.
No production security boundary, real customer tool effect or independent uptake
has been established. Bibliographic metadata and abstract-level summaries below
have been verified against primary pages; a full closest-work review remains
necessary before submission.

## 9. Next confirmatory study

Freeze independently reviewed scenarios and realistic tool contracts. Adjudicate
labels before evaluation. Predefine severity and intervention costs. Fit on train
families, select only on calibration families and keep the final test sealed.
Match model, visible information, recovery policy and action affordances across
systems. Report trade-offs, infeasible budgets, errors, abstention/refusal coverage,
recovery effects and uncertainty at the family level. Separate exploratory tuning
from confirmatory results and retain negative findings. The chosen topic remains
selective autonomy even if the eventual method or central claim changes.

## References — primary pages checked 12 November 2026

[1] Yangjun Ruan et al. Identifying the Risks of LM Agents with an LM-Emulated
Sandbox. arXiv:2309.15817v2. https://arxiv.org/abs/2309.15817v2

[2] Edoardo Debenedetti et al. AgentDojo: A Dynamic Environment to Evaluate Prompt
Injection Attacks and Defenses for LLM Agents. arXiv:2406.13352v3.
https://arxiv.org/abs/2406.13352v3

[3] Shunyu Yao, Noah Shinn, Pedram Razavi and Karthik Narasimhan. Tau-bench: A
Benchmark for Tool-Agent-User Interaction in Real-World Domains.
arXiv:2406.12045v1. https://arxiv.org/abs/2406.12045v1

[4] Yonatan Geifman and Ran El-Yaniv. Selective Classification for Deep Neural
Networks. arXiv:1705.08500v2. https://arxiv.org/abs/1705.08500v2

[5] Anastasios N. Angelopoulos, Stephen Bates, Adam Fisch, Lihua Lei and Tal
Schuster. Conformal Risk Control. arXiv:2208.02814v4.
https://arxiv.org/abs/2208.02814v4
