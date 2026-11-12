# Running ScopeQuay locally and sharing it on GitHub

| Location | What runs there | Where state lives |
|---|---|---|
| Your computer | Python approval server, SQLite demo, optional Ollama experiments | Ignored local-data/ and runs/ folders |
| GitHub repository | Versioned source, tests, synthetic fixtures, research draft | Git commits; no approval notes or local model weights |
| GitHub Actions | Automated tests on a fresh runner | Temporary test data; no local Ollama service or model inference |
| GitHub Pages | Public project guide and screenshot | Static files only; cannot run the Python approval backend |

The same source runs on another computer after cloning and installing Python
3.12+. The approval demo needs no model download or third-party Python packages.
It uses the fixed reference gate and a deterministic sandbox, so its behavior is
easy to inspect. Local model experiments are a separate research workflow.

## Local application

```powershell
python -m scopequay serve
```

Open http://127.0.0.1:8765. Load examples, select the refund needing approval,
write a review note, and record approval. The gate runs again. Click Run in sandbox
separately to execute. The audit trail survives a server restart. Export it with
Export audit JSON. Stop with Ctrl+C in the terminal running the server.

Confirm target means the displayed example target. Confirm simulated fresh check
means a demo state update, not a fresh query to an actual business service.
Missing permissions and policy denial cannot be overridden by approval.

The server binds only to 127.0.0.1 and validates Host, Origin and a per-start CSRF
token for mutations. This is not account authentication or team access control.
The Python standard-library HTTP server is for local development; do not expose
it on the internet. No environment variable or API key is needed.

## Research engine

```powershell
python -m unittest discover -s tests -v
python -m scopequay validate --data data/pilot_v0_2.jsonl
python -m scopequay calibrate --data data/pilot_v0_2.jsonl --out artifacts/my-calibration.json
python -m scopequay run --data data/pilot_v0_2.jsonl --artifact artifacts/my-calibration.json --out runs/my-first-run
```

For installed Ollama models, start Ollama, then use `python -m scopequay models`.
Use the CLI's explicit call and duration limits before an agent experiment.
No model is downloaded automatically, and cloud model names are rejected.
No paid model APIs are used. Optional AGT/Dogwood integrations need their pinned
dependencies; the core and dashboard do not.

## Before a production service

Real connectors need authenticated reviewers, scoped identities, trusted state
retrieval, durable tool-level idempotency, concurrency/approval expiry contracts,
isolation, observability and operational review. This local prototype does not
implement those production guarantees. A future paid product is a separate
engineering and validation step, not an implication of publishing this repository.
