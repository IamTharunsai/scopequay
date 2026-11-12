# Fixture repair v0.2: keep the original pilot, repair future generation

Recorded 2026-10-23 after auditing v0.1 fixtures. The original data/pilot.jsonl and
all existing run records are preserved. They are never overwritten by this repair.

The audit found six families with quantity one, for which an integer half-commit
could not expose partial effects. The generator now clamps the same seeded draw
to at least two. This preserves the draw schedule and all other field draws,
while making every generated partial effect strictly smaller than the request.
New repaired fixtures are written to data/pilot_v0_2.jsonl, with a separate
calibration artifact and separately named runs. No cross-version score comparison
is presented as a method improvement. This fixes fixture validity, not a
calibrated-controller failure. It was informed by an audit and is exploratory.

The remaining counterfactual/realism limits in artifacts/fixture_audit.json are
not erased by this repair. Visible explicit policy facts still make rule gates
strong; high_consequence still changes two public fields. Independent annotation
and richer environment construction remain needed.
