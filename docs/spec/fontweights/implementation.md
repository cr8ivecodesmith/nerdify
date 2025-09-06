Font Weights Config — Implementation Notes
=========================================

Goals
-----
- Provide a single loader for `fontweights.toml` and expose a small, clear API for consumers.
- Preserve current defaults when config is missing.
- Keep parsing/normalization rules deterministic and testable.

Data Model
----------
- Canonical weight: `(name: str, value: int)` from `[weights]`.
- Aliases: `alias_phrase -> canonical_name` from `[aliases]`.
- Derived lookup:
  - `normalized_name -> canonical_name` (includes canonical names and aliases).
  - `canonical_name -> value`.

Normalization
-------------
- Normalize phrases by:
  1. Lowercasing
  2. Splitting on whitespace and hyphens
  3. Rejoining with single spaces
- Examples:
  - `"Extra-Light" -> "extra light"`
  - `"  Semi   Bold" -> "semi bold"`

Loader API
----------
- Module: `fontweights.py` (to be added alongside scripts).
- Public functions:
  - `load_config(path: Path | None = None) -> FontWeights`:
    - Reads `path` or `./fontweights.toml`.
    - Raises `RuntimeError` with a clear message if missing or invalid.
  - `standard_weights(cfg: FontWeights) -> list[tuple[int, str]]`:
    - Returns `[(value, canonical_name), ...]` sorted by `value` ascending.
  - `lookup_value(cfg: FontWeights, phrase: str) -> int | None`:
    - Returns the numeric weight for a phrase (alias or canonical).
  - `canonical_name_for(cfg: FontWeights, phrase: str) -> str | None`.

Defaults
--------
- None. The config file is required. Provide a default example in the repo root.

Integration Plan
----------------
1. `weightadjust.py`
   - Remove `WEIGHT_TABLE`; require `fontweights.toml` via `load_config()`; error out if not found.
   - Iterate `standard_weights(cfg)` and use canonical names for basenames.
   - Keep range validation/clamping logic.
2. `nameadjust.py`
   - Replace `_BASE_STYLES` and the hardcoded weight map in `_infer_weight_and_italic_from_subfamily` with `lookup_value` over canonical and alias phrases.
   - Keep italic detection as is; if no weight match is found, return `400` only if the config maps a term like `Regular`; otherwise return `None` for weight.
3. `createcollection.py`
   - No dependency. Sorting uses OS/2 values; no name/token parsing.

Error Handling
--------------
- If `fontweights.toml` is missing or malformed:
  - Raise `RuntimeError` and exit with an actionable error from each tool.
- If aliases point to missing canonical names:
  - Ignore those aliases; log a concise warning.

Testing
-------
- Add unit tests for `fontweights.py` covering:
  - Error on missing file.
  - Parsing a minimal TOML and overriding/adding weights.
  - Normalization behavior (spaces vs hyphens, case‑insensitive).
  - Alias mapping and conflict handling.
- Update existing tests to provide a temporary `fontweights.toml` fixture where needed.
  - `tests/test_weightadjust_v3.py` should create a temp config (e.g., the nine standard weights) and assert filenames accordingly.

CLI Considerations (Future)
---------------------------
- Add `--fontweights` optional flag to individual tools, and/or `FONTWEIGHTS_FILE` env var.
- Do not add external dependencies; use stdlib `tomllib` (Python 3.11+) or `tomli` if needed; prefer stdlib and pin minimum Python accordingly.
