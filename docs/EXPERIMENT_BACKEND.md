# Experiment backend

ScopeQuay now has a backend API over its research runner. This is a local,
single-user experiment service, not a production cloud service. The existing
approval dashboard remains an illustrative workflow; it does not automatically
start these experiments or become an LLM comparison screen.

Start the updated application with `python -m scopequay serve`. A server that was
already running before this change needs a restart. From an installed wheel,
set `--dataset` to the repository's data/pilot_v0_2.jsonl path if needed.

## API contract

| Endpoint | Behavior |
|---|---|
| GET /api/state | Existing demo state and per-start CSRF token |
| GET /api/models | Local Ollama inventory; no inference; 503 if unavailable |
| POST /api/experiments | Validate options and create one bounded experiment job |
| GET /api/experiments | List persisted job state |
| GET /api/experiments/{id} | Poll queued/running/completed/error state |
| GET /api/experiments/{id}/results | Verified outcome records and summary after the job stops |

POST requires JSON, the same local Host/Origin checks as other mutations, and
X-ScopeQuay-Token from /api/state. Arbitrary prompts, file paths, endpoints and
shell commands are not accepted. Review/approval-demo records never become
research scenarios.

Example fixed-proposal request (no LLM invoked):

```json
{"mode":"fixed_proposal","systems":["direct","tharun_fixed"],"limit":2,"split":"test"}
```

Example actual local-agent request:

```json
{"mode":"agent","provider":"local_ollama","model":"llama3.2:3b","systems":["direct","tharun_fixed"],"limit":2,"max_steps":4,"max_calls":16,"max_seconds":180}
```

`tharun_calibrated` remains an internal compatibility identifier. Selecting it
fits the existing train/calibration procedure and saves its artifact; test data
is not fitted. Calibration/report preparation can be slower than fixed-gate
evaluation. The local size cap is 3.5 GB per installed model for this laptop pilot.
Cloud aliases and missing model tags are rejected rather than downloaded.

Limits: 1–8 scenarios, 1–3 distinct supported controllers, at most 4 agent steps,
64 worst-case model calls and a 1–600 second evaluation-loop budget. The current
supported controllers are direct, static_policy, tharun_fixed and
tharun_calibrated. Every agent system uses the same effect-history recovery guard.
There is one worker per service instance, and the operator must run only one
service against a job directory. This is not a distributed or cross-process queue.

The time limit is checked between episodes; an in-flight local call can take up
to its request timeout, and calibration/report generation is outside that loop
budget. There is no hard process deadline or cancellation API. Restart marks
unfinished jobs interrupted and does not pretend to resume them.

## Evidence returned

Jobs persist under local-data/experiments/, excluded from Git. Each stores its
request, status, fixture hash, backend source snapshots and run source snapshots.
Completed outcome records include controller, actual simulated effects, completion,
severity loss, errors, recovery, latency and model telemetry. Agent records also
include proposed actions and gate decisions. These are observable actions and
short explanations, not a request for a provider's private chain of thought.

Errors are explicit, not counted as successful refusals. Cached calls remain
identified and are not independent replications. Summary metrics refer to the
selected synthetic scenarios, not to an entire provider or model's safety.

## Provider expansion

OpenAI and Anthropic are not implemented or enabled in this backend. No provider
keys are read and no paid calls are made. A future adapter must normalize each
provider's tool-call format, preserve exact model/version and sampling settings,
enforce independent spending limits, record usage, distinguish transport errors
from model actions, and pass the same sandbox contract. It also needs explicit
authorization for paid runs. An API key alone does not establish fair comparison.
