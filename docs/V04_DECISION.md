# ScopeQuay v0.4 research alpha

The user requested one product covering the implemented scenario families, without
splitting the work into separate persona products. The release workflow is:
select suite → compare controllers → inspect action/effect/recovery → export evidence.
An action-review SDK and advisory skill use the same fixed-gate engine.

The test and transfer splits together contain 152 held-out points spanning eight
domain vocabularies and eight variants. Training/calibration points remain excluded
from evaluation. This is one generic ledger, not comprehensive real-world domain
coverage. All possible business scenarios cannot be honestly promised.

## Stack decision

Keep Python 3.12+ for policy, SQLite effects, CLI, API and evaluation. Keep the
small web client in HTML/CSS/JavaScript with explicit API contracts. This avoids
a speculative rewrite and keeps the no-dependency local demonstration available.
TypeScript becomes useful when the frontend's size and contributors justify a
build pipeline; it is not a prerequisite for correct research. Rust remains in
the optional native Dogwood dependency. No language choice makes a product best.

## Delivered scope

Connected experiment UI, persisted jobs and result export; supplied-action and
local-agent modes; domain/variant/split slices; visible action and recovery trails;
recorded evidence separate from new runs; advice-only SDK/CLI and installable
skill; unchanged illustrative approval demo; explicit unavailable-model/error
states. Cloud providers, genuine business connectors, authenticated teams and a
production-grade job scheduler remain outside this alpha.

## Release acceptance

Run meaningful backend/policy/skill tests; exercise HTTP submission and result
verification; inspect desktop/mobile UI and errors; ensure model calls are never
implied by a supplied-action test; preserve existing raw evidence; verify package
assets and installable skill; publish accurate README and launch materials.
Independent review, representative user demand and scientific validation remain
open. Passing this release gate does not complete the research project.
