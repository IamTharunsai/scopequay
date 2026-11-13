---
name: scopequay-review
description: Review a proposed tool action using ScopeQuay's local fixed gate, or run a reproducible sandbox comparison when the user wants to inspect agent-action failures. Use for explicit action-review or ScopeQuay test requests; it does not intercept unrelated tool calls.
---

Use the ScopeQuay checkout or installed Python package available in the user's
environment. Read its README and docs/EXPERIMENT_BACKEND.md when running a suite.
Do not install or start services merely because this skill was loaded.

For an action review, obtain the exact intended operation, target and quantity,
and the available authority/policy/state evidence. Preserve uncertainty and identify
unverified facts; do not invent authorization. Write the public Observation JSON
to a local working file within the task scope and run:

`python -m scopequay review --input <action-context.json>`

The complete JSON shape is shown in references/action-context.json beside this skill.
Report the returned decision, reason, supplied assumptions and next needed fact.
The command does not execute a tool. A result of EXECUTE is a gate assessment of
supplied context, not independent permission to take an external action. Continue
to respect the user's scope and the host's permissions.

For a sandbox comparison, use `python scripts/reproduce_pilot.py --out <new-run>`
from the checkout, or its documented local experiment API. Keep original outcomes,
fixture versions, errors and cache indicators. Explain harmful effects, useful
completion and recovery together. Distinguish fixed-proposal simulations from real
model inference and distinguish both from real business actions.

This skill is advisory. It cannot block tool calls outside ScopeQuay or establish
production security, provider safety, scientific novelty or performance superiority.
