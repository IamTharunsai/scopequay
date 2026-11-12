# Local prototype scope

ScopeQuay is a single-user local sandbox, not a production security boundary.
It does not connect to real accounts, payments or business APIs. No internet
deployment of its Python HTTP server is supported.

Keep model weights, review notes, credentials and local databases outside commits.
The default .gitignore excludes local-data/, runs/, artifacts/, output/, .env
and virtual environments. Do not place real customer information in examples or
public issues. Hash chains are local consistency checks, not external attestation.

Tests exercise origin/host restrictions, CSRF checks, policy/authority holds,
transactional review, stale revisions and duplicate execution. Tests do not prove
absence of vulnerabilities. Do not post secrets to report an issue; use GitHub's
private vulnerability reporting if enabled, or ask the repository maintainer for
a private reporting route without including sensitive details.
