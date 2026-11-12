# Native Dogwood pilot slice

The native reference CLI was built from the official
[Dogwood repository](https://github.com/dogwood-policy/dogwood) at commit
`4ec5e2c01b44ff3882a231ae5d315b330b38fa25`, using Rust 1.95.0 and the preserved
Cargo lock. The installed default Rust toolchain was not changed. Build/check
provenance is in `artifacts/dogwood_probe_rust195_resume.json`. Earlier compiler
failure and bounded build timeout are retained separately.

The benchmark schema models Agent principals and a sandbox Gateway resource,
with one action for each of cancel, change_role, publish, refund, restart, send,
update and void. Arguments live under input; observable trusted policy facts live
under system. The policy permits an action only when permission, authority,
approval, referent, state and intent checks all pass. Everything else defaults
to deny. This is a hand-written, single-request policy; no custom event schema,
information provider or temporal policy is added to the benchmark slice.

Both `schema action` and `validate --policy-schema` exited zero. Native integration
tests exercise the allow/deny behavior, changed arguments and error reporting.
The upstream temporal read-after-login replay also passed DENY/ALLOW/DENY. This
confirms execution of that example, not full temporal correctness or a benchmark
of temporal safety.

Native allow maps to EXECUTE. Native deny is mapped by our deterministic reason
handler to CLARIFY, STAGE, ESCALATE or REFUSE using only public facts. These four
labels are wrapper outputs, not Dogwood's native decision vocabulary. Native
errors remain recorded errors and fail closed. Raw verdicts and sanitized traces
are retained in outcome telemetry. A native cache hit is distinct from a model
cache hit. Hashes bind the binary, schema and policy to each run manifest.

Run after building the pinned CLI, or set `THARUN_DOGWOOD_BIN` to your verified
binary:

```powershell
python -m tharun run --data data/pilot_v0_2.jsonl --systems dogwood_point_policy --split test --out runs/my-native-dogwood
```

This evaluates a narrow local CLI slice, not the full Dogwood runtime, an AWS
service, production enforcement or a native five-way intervention method. Schema
and policy are packaged; third-party binaries/source and Rust dependencies are
excluded from the release archive. Their license remains separate from ours.
