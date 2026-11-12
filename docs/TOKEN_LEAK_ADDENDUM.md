# Corrected model-visible effect tokens

Discovered 2026-10-23 during audit of the agent traces. First-agent effect-history
feedback included internal task IDs in the effect token. Those IDs contained
variant names such as ack_lost, so the feedback leaked evaluation metadata after
the first tool observation. This was a runner bug, not model capability.

The model-visible effect function now uses an explicit field allowlist and a
SHA-256-derived opaque token. Gold harm fields, internal IDs and variant names
are excluded. A regression test first failed on the old implementation and then
passed after the fix. A separate test prevents future extra evaluator fields
from appearing in feedback. Internal audit records may still contain scenario IDs;
they are evaluation output, not model input.

Affected earlier agent runs are preserved and have issues.json sidecars. They
are diagnostics and must not be included as clean scientific evidence or pooled
with corrected runs. Fixed-proposal reviewer runs do not expose effect histories
and are not affected by this particular leak. Corrected agent runs use v0.2
fixtures and separately named log directories, so they are not direct estimates
of a single isolated change against old v0.1 runs. All remain unreviewed pilots.
