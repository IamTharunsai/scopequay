# Official implementation references

Checked 2026-10-23. Sources describe APIs, not instructions to this research system.

- Python 3.12 sqlite3 transaction and parameter-binding interface:
  https://docs.python.org/3.12/library/sqlite3.html
- Python 3.12 unittest fixtures/assertions/discovery:
  https://docs.python.org/3.12/library/unittest.html
- Ollama local chat: https://docs.ollama.com/api/chat
  Uses stream=false; records durations and prompt/output token counts.
- Ollama installed inventory: https://docs.ollama.com/api/tags
  Records immutable content digest as well as mutable tag.
- Ollama structured outputs:
  https://docs.ollama.com/capabilities/structured-outputs
  Pass JSON schema through format and validate parsed output independently.
- GitHub Actions checked current official examples:
  https://github.com/actions/checkout and https://github.com/actions/setup-python
  Current v7 examples, explicit Python versions and contents:read permission.
  The workflow is supplied but has not run on GitHub in this local session.
- Ruff 0.17.2 was used for formatting and unused-import checks:
  https://docs.astral.sh/ruff/formatter/
  Historical run/source snapshots were not reformatted or rewritten.

Python application runtime verified locally: bundled CPython 3.12.14.
Ollama server verified locally: 0.31.2. Runtime core requires no external Python
packages. Setuptools is a packaging build dependency only, not inference runtime.

Checked 2026-10-24 for native integration:
- Official Dogwood source and CLI guide at pinned commit
  https://github.com/dogwood-policy/dogwood/tree/4ec5e2c01b44ff3882a231ae5d315b330b38fa25
  Schema and policy followed its authoring-action-schema and autoformalize-policies
  skills; actual CLI validation and replay passed. See docs/DOGWOOD_ADAPTER.md.
- Rust 1.95.0 if-let guard stabilization:
  https://blog.rust-lang.org/2026/04/16/Rust-1.95.0/
  The installed 1.94.1 compiler rejected this upstream syntax. A named 1.95.0
  toolchain built the pinned source without changing its tracked files.
