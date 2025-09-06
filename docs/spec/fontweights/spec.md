Font Weights Config
===================

Overview
--------
- Purpose: Centralize the font weight table in a repository-level TOML file so all scripts share a single source of truth and you can add or adjust weights without code changes.
- File: `fontweights.toml` at the project root (or an explicit path in future flags/env).
- Consumers: `weightadjust.py`, `nameadjust.py`, `createcollection.py` (and any future tools needing weight names/values or synonyms).

Discovery
---------
- Required file: `./fontweights.toml` (current working directory / repo root).
- Future override paths (not required immediately):
  - Environment variable `FONTWEIGHTS_FILE`.
  - CLI flags like `--fontweights` for specific tools.
- If the file is missing or cannot be parsed, tools fail fast with a clear error.

TOML Schema
-----------
- `weights`: canonical names to numeric values (100–900 typical, but arbitrary numeric values are allowed).
- `aliases`: optional mapping of alias phrases to canonical names for parsing/inference.

Example (default):

```toml
[weights]
Thin = 100
"Extra-Light" = 200
Light = 300
Regular = 400
Medium = 500
"Semi-Bold" = 600
Bold = 700
"Extra-Bold" = 800
Black = 900

[aliases]
Hairline = "Thin"
"Ultra Light" = "Extra-Light"
Extralight = "Extra-Light"
"Extra Light" = "Extra-Light"
"Semi Bold" = "Semi-Bold"
Semibold = "Semi-Bold"
"Demi Bold" = "Semi-Bold"
Demibold = "Semi-Bold"
Book = "Regular"
Roman = "Regular"
"Ultra Bold" = "Extra-Bold"
Extrabold = "Extra-Bold"
Heavy = "Black"
```

Normalization & Matching
------------------------
- Lookups are case‑insensitive and whitespace‑normalizing.
- Hyphens and spaces are treated equivalently during matching. For example, `Extra-Light` and `Extra Light` match the same canonical weight.
- Tools may normalize phrases by:
  - Lowercasing
  - Splitting on whitespace and hyphens
  - Rejoining with a single space
- Authors may still list common variants explicitly in `[aliases]` for clarity.

Ordering
--------
- Tools iterate weights in ascending numeric order unless explicitly overridden in tool‑specific flags.
- Canonical names are preserved as written in `[weights]` when composing filenames and internal name records (e.g., `Cool-Regular-410.ttf`).

Behavioral Guarantees
---------------------
- Extensibility: Adding additional weights (e.g., `950 = "Extra-Black"`) automatically participates in tools that enumerate the table, provided the font’s `wght` axis range permits it.
- Parsing: Scripts that infer weight from phrases use `[aliases]` and canonical names from `[weights]` to map phrases to numeric weights.

Error Handling
--------------
- Missing/invalid TOML: tools emit a concise, actionable error and exit non‑zero.
- Aliases that point to a non‑existent canonical name: ignored with a warning (does not block execution if `[weights]` is valid).
- Conflicts: if multiple canonical names share the same numeric value, tools still work; ordering remains numeric, then by name.
