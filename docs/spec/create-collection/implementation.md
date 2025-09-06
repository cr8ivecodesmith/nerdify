Create Collection — Implementation
=================================

Implementation focus
--------------------
- Do not parse names for weight/style. Adjust naming is responsible for normalization.
- Minimal filename heuristic only for basename derivation:
  - Tokenize stems on `-`/`_`, lowercase for matching.
  - Drop only: italic markers, VF/Variable/Var, version‑like tokens (e.g., `0902`, `v1.2`).
  - Compute longest common token prefix; join using original casing from the first filename, sanitize for filesystem.
- Sorting reads OS/2 values directly:
  - Weight: `OS/2.usWeightClass` (fallback to 1000 if missing/unreadable).
  - Italic: `OS/2.fsSelection` bit 0; fallback to `head.macStyle` bit 1.
- Derive the output basename:
  - If all inputs share a single non-empty Typographic Family (name ID 16), use it as the basename.
  - Otherwise, apply the minimal filename heuristic above; if empty, use the parent directory name of the first font, or the first stem if the parent is empty. `--name` overrides both.

Error Handling
--------------
- Errors reading name/OS/2 tables raise `RuntimeError` and abort. `--dry-run` may still function with monkeypatched readers in tests.

Testing
-------
- Unit tests should monkeypatch the OS/2/italic reader to avoid heavy IO, and validate deterministic ordering and basename derivation without any naming heuristics.
