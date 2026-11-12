# Actual Microsoft toolkit adapter: narrow, pinned comparison

Installed into an isolated `.venv-toolkit` in this workspace:
`agent-governance-toolkit-core==5.0.0`. Full transitive environment versions are
in `artifacts/toolkit-requirements.lock.txt`; model weights are not dependencies.
Source/ownership checked against official Microsoft repository and PyPI metadata:

- https://github.com/microsoft/agent-governance-toolkit
- https://pypi.org/project/agent-governance-toolkit-core/5.0.0/

The implementation uses the installed `agentmesh.governance.policy.PolicyEngine`
API: load_yaml and evaluate(agent_did, context). The official README wrapper
documents this family of declarative policy controls; installed v5.0.0 source
was inspected for exact signatures. This is a policy-engine slice of AGT, **not**
an evaluation of its full identity, sandbox, governance SDK or newer ACS runtime.

`tharun/agt_policy.yaml` uses only public observation facts: policy permission,
authority, required approval, referent presence, current state and intent match.
It deliberately gives the engine the same explicit facts available to THARUN.
Native engine outputs and the policy hash are retained in logs. No oracle labels,
fault type, gold decision, task variant or severity label are supplied to it.

Mapping is an adapter choice: allow->EXECUTE; require_approval->ESCALATE (or REFUSE
if approval unavailable); deny->REFUSE, except missing_referent->CLARIFY and
stale_state->STAGE. Those last reason handlers are ours, not a claim that this AGT
API natively emits all five research labels. No real approval request is sent.

Actual checks: allowed normal action, policy denial, approval, unavailable
approval, missing referent, stale state and intent mismatch. These are integration
checks against installed code. The package's transitive namespaces emit migration
warnings despite installation under its consolidated name; this is recorded,
not hidden by changing to an unpinned legacy release.

Run the actual adapter using the isolated Python:
```powershell
.venv-toolkit/Scripts/python.exe -m unittest discover -s tests -v
.venv-toolkit/Scripts/python.exe -m tharun run --out runs/agt-example --systems agt_policy tharun_fixed tharun_calibrated
```

This fact-based policy is strong on these easy synthetic fixtures by construction.
Matching it does not prove general governance; failing to beat it rules out a
superiority claim from this pilot. Broader fair policies and external environments
remain research work. The optional environment is not copied into the ZIP; its
lock file and integration code are included.
