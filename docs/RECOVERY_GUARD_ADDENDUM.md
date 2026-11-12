# Recovery-guard condition: exploratory engineering amendment

Recorded 2026-10-23 after the first 32 closed-loop agent episodes and before
running the explicit recovery-guard condition. No earlier outcome was overwritten
or rescored as if it had used the new guard. The calibrated threshold is unchanged.

Observed implementation gap: a correct initial gate verdict did not stop the
model from applying a completed task repeatedly. Fixed-proposal evaluation with
automatic verification did not expose this behavior. The initial agent run
retains these failures, including wrong-resource and repeated-effect traces.

New optional monitor: before any subsequent mutation, inspect observable effect
history. A matching already-committed effect returns its status without another
commit. A partial/mismatched effect is rolled back only if policy, authority and
reversibility permit it, then halted; otherwise it is halted. This prevents a
second write in those cases but cannot erase harm from the first write.

The ledger now records resource and operation alongside token/amount to make
verification possible without the oracle's hidden harm labels. The monitor does
not consume severity, gold decisions or execute_harm. Tests cover normal repeats,
lost acknowledgments, partial mutation and wrong-resource historical harm.

For fairness the monitor can be applied to every comparator under the same
condition, not just THARUN. Compare recovery-on vs recovery-off explicitly; do not
attribute the monitor's effect to the calibrated score. This amendment is
exploratory after observing failures, not preregistered confirmatory evidence.
