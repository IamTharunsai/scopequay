# Engineering protocol addendum: bounded agent episodes

Recorded 2026-10-23, after the first fixed-proposal pilot and before the first
closed-loop agent run. Keep earlier results and manifests; do not relabel them.

1. The initial Llama reviewer smoke selected eight variants across four domains.
   The selection algorithm now interleaves domains before variant rotation. New
   eight-case selections span all seven non-transfer domains. This is a coverage
   change, not selection based on model performance. Old run selected IDs remain
   in their original manifests.
2. Added bounded local agent episodes (up to four actions). Models can generate
   resource/amount proposals, inspect tool effects, retry, undo or terminate.
   Effects still occur only in the same generic SQLite ledger. This does not
   create realistic operational environments or a human response simulator.
3. Raw model-only, prompt-only, static gate, LLM judge gate, fixed and calibrated
   gates can now share this agent interface. Model-only recovery is separately
   logged. Gate interventions terminate; no hypothetical approval is fabricated.
4. Model sees observable effects but never oracle harm labels. The ledger oracle
   validates actual effect amounts and wrong resource proposals. A claimed
   FINISH without the intended effect is not successful completion.
5. Qwen 2.5 7B smoke succeeded but required ~135 seconds for a tiny response on
   this 8 GB machine; it is not treated as a completed second-model benchmark.
   Larger installed models are not part of today's bounded run plan.
6. Negative initial finding is retained: on the 112-point synthetic test,
   the selected calibrated threshold had lower useful autonomy than the fixed
   gate. Neither the addendum nor new agent runs tune that threshold to the test.
