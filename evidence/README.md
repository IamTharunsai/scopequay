# Synthetic pilot evidence

This is recorded engineering evidence, not publication-ready validation.
The raw synthetic fixed-proposal outcomes are byte-identical copies from the
local historical runs. Manifests omit local machine paths and configuration;
pilot-summary.json binds the original manifest hashes and raw outcome hashes.
Source snapshots are preserved and checked against each manifest's hashes.
Internal controller IDs retain the historical names for compatibility.

Use `python -m tharun verify-log evidence/native-dogwood-test` to verify its record
chain. Hashes show consistency against these records, not independent attestation.
The fixtures have no independent human review. Do not pool repeated systems or
thresholds as independent tasks. The public data has 40 synthetic families,
320 decision points, one ledger and eight domain vocabularies.

The optional AGT slice evaluates PolicyEngine only; Dogwood evaluates its native
CLI single-request fact policy. Both map native decisions through our wrapper.
Source snapshots do not vendor the third-party toolkit implementations.

The five-way cost candidate at alpha 0.05 exceeded that mean-loss target on test.
The threshold candidate did not improve useful autonomy over the fixed gate.
This negative evidence must remain visible in research descriptions.
