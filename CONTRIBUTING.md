# Contributing

Use Python 3.12+ and run `python -m unittest discover -s tests -v`.
The core and dashboard use the standard library. Native toolkit tests skip if
their optional pinned dependencies are unavailable. Tests must not call paid
model APIs or download model weights.

Keep product demos separate from benchmark evidence. Never replace negative
findings, silently alter fixture versions, or count cached inference as a fresh
replicate. New metric definitions require an explicit protocol addendum and
derived-analysis provenance. Do not alter historical raw records or snapshots.

For research contributions, give sources and identify what is observed, assumed,
hypothesized or unverified. Do not claim statistical safety, novelty, human
agreement, production readiness or independent adoption without supporting evidence.
