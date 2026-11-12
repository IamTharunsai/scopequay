# Reference labels and model-generated proposals

Recorded 24 October 2026. A five-way label in this fixture describes its supplied
resource and amount. When an agent changes those arguments, the reference label
cannot automatically grade the new proposal. New episode records mark these
decisions as label-inapplicable and omit them from label accuracy. Only nominally
feasible reference-matching proposals are included in refusal/intervention
denominators; this is a conservative known-label subset, not a claim that every
changed proposal is unsafe. Useful autonomy keeps the original task denominator.
Completion and harm are evaluated against actual ledger effects.

Earlier agent records lack applicability flags. Their label accuracy and
unjustified-refusal metrics are omitted in reanalysis and explicitly marked in
issue sidecars. Original manifests, source snapshots and raw logs remain intact.
This does not invalidate the actual-state completion/harm endpoint itself, but
the tiny synthetic pilot cannot establish general model rankings.

Declared intervention costs currently apply to the first decision. They are
assumed units, not dollars, measured human effort or cumulative episode costs.
