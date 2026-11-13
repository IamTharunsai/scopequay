# What ScopeQuay is trying to establish

Updated 13 November 2026. The product is an application-side action controller
and an experiment harness. It does not modify a foundation model, make an entire
provider safe, or add protection to unrelated ChatGPT/Claude conversations. It
can influence only tool actions routed through its own enforcement boundary.

## Potential practical value, not measured savings

It could help developers prevent unauthorized changes, reduce duplicate effects
after lost acknowledgments, route uncertain requests to clarification or approval,
and allow routine permitted work without unnecessary human interruption. Those
benefits must be measured. No dollar savings, reduction in incidents, adoption,
deployment safety or superiority has been established.

## What existing work already covers

- OpenAI documents input/output/tool guardrails and approval interruptions:
  https://developers.openai.com/api/docs/guides/agents/guardrails-approvals
- Anthropic describes tool design, evaluation and feedback-driven improvement:
  https://www.anthropic.com/research/writing-tools-for-agents
- AgentDojo evaluates tool agents under prompt injection:
  https://arxiv.org/abs/2406.13352
- Tau-bench evaluates tool-agent-user interaction and final database state:
  https://arxiv.org/abs/2406.12045
- AgentBoundary describes permission/risk counterfactuals, over-refusal and unsafe
  compliance, together with a runtime calibration module:
  https://arxiv.org/abs/2609.33658

The first two are verified primary documentation. The paper comparisons here are
bounded to their verified abstracts; they are not substitutes for full-text
review. AgentBoundary is particularly close to our calibration/counterfactual
plan. Do not claim that calibrating autonomy or reporting restraint versus useful
completion is itself an unoccupied gap.

## Candidate extensions to investigate

| Candidate | What would have to be shown |
|---|---|
| Intervention selection | Clarify/stage/escalate choices improve outcomes at validated intervention costs, beyond execute/refuse and strong policy baselines |
| Recovery-aware control | Observable effect verification prevents duplicate or unsafe retries without unnecessarily sacrificing completion |
| Risk feasibility | Selected budgets hold under explicitly stated assumptions; report infeasible budgets rather than hide them |
| Transfer | Benefits persist across sealed scenario families, realistic tools and exact versions of multiple models |
| Deployable integration | Benefits remain when compared with properly configured native policy engines under matched information and affordances |

These are candidate contributions. We have not verified that prior work lacks
them or that our implementation improves them. The local UI and GitHub repository
are useful engineering artifacts; they are not evidence of scientific novelty.

## What GPT/Claude/local-model comparisons could teach us

With the same tasks, visible facts, tool contracts, recovery policy and scoring,
we could identify incorrect targets, missing permission checks, over-refusal,
unnecessary intervention, duplicate effects and recovery failure. Report both
useful completion and harm, plus errors, model/version, prompt, tokens and timing.
Keep runtime cost and assumed intervention cost separate. Do not rank models
using only refusal rate or a handful of cherry-picked traces.

Such evidence can inform better prompts, tool descriptions, policy constraints,
approval thresholds and training/evaluation datasets. Informing model providers
would mean sharing reproducible failure cases and validated measurements, not
claiming that our wrapper repaired their underlying models.

The current pilot remains negative for the intended threshold advantage, and one
cost candidate exceeded its held-out mean-loss target. Stronger scenarios,
independent annotations, a full closest-work review and a sealed confirmatory
study are required before a paper can claim an improvement. A small local model
is useful for plumbing and debugging; it cannot establish frontier-model behavior.
