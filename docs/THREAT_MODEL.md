# Trust and execution boundaries

Trusted in this prototype: Python runtime, local code, initial scenario snapshots,
explicit policy/authority metadata and evaluator oracles. Authority metadata is
synthetic and is not authenticated against a real identity provider.

Untrusted: model text, task instructions, proposed arguments and eventual tool
descriptions/retrieved content. Models receive Observation only, not task/family
IDs, variant/split, fault injection, gold labels, or oracle outcomes. They can infer
rules from visible metadata; this makes the current fixtures easy and is a
limitation, not an accidental leak to conceal.

Only the in-memory ledger mutates. The model cannot choose arbitrary commands or
URLs. Ollama requests are restricted to 127.0.0.1:11434, installed exact names and
non-cloud tags. No pull endpoint, account key or provider SDK is used. Requests
ignore proxy environment variables. Logs/cache contain synthetic task material;
do not point this pilot at sensitive real-world records.

Hard checks reject policy denial, missing authority, required approval, and intent
resource/amount mismatch in THARUN. The direct/model-only baselines intentionally
can fail these checks in the simulator. Do not connect them to real tools.

Lost acknowledgment: check authoritative effect history before retry. Partial
commit: safe rollback if reversible/authorized; otherwise halt. Each effect is
recorded even after compensation. No recovery code can prove real side effects
are reversible by reading model text.

Audit chains detect accidental edits relative to a retained manifest. They are
not externally signed, not immutable storage, and do not prevent an attacker
rewriting logs plus manifest. The package is not production security software.
