# Linting & Styling Implementation

This document explains how the spec is applied in this repo and how to use it day-to-day.

## Configuration Files
- `pyproject.toml`
  - Ruff
    - `line-length = 100`
    - `target-version = "py311"`
    - Rule sets: `E,W,F,I,UP,N,B,C4,SIM,C90,D,PT,ANN,ERA,ICN,ISC,TID,PTH,RET,RUF`
    - McCabe: `max-complexity = 15`
    - Pydocstyle: `convention = "google"`
    - Per-file ignores: relax `D` and `ANN` in `tests/**/*`
    - Exclusions: binary/asset and build directories
  - Black
    - `line-length = 100`
    - `target-version = ["py311"]`
    - `extend-exclude` mirrors Ruff exclusions

## Commands
- Lint all:
  - `ruff check .`
- Auto-fix safe issues:
  - `ruff check . --fix`
- Format changed files:
  - `black path/to/file.py`
- Sort imports (via Ruff):
  - `ruff check --select I --fix path/to/file.py`
- Run tests (quiet):
  - `pytest -q`

## Typical Workflow
1. Implement changes.
2. `ruff check .` and review output.
3. `ruff check . --fix` to auto-apply safe fixes.
4. `black .` to format.
5. `pytest -q` to verify.

## What Ruff Enforces Here
- Import order and grouping (`I`)
- No unused imports/variables (`F`)
- Modern Python patterns (`UP`)
- Naming consistency (`N`)
- Bug-prone patterns (`B`)
- Simpler comprehensions and statements (`C4`, `SIM`)
- Reasonable complexity (`C90` <= 15)
- Docstrings present and tidy per Google style (`D`) with pragmatic ignores
- Pytest best practices (`PT`)
- Prefer `pathlib.Path` over `os.path` (`PTH`)

## Notes & Exceptions
- Black remains the formatter of record; both Ruff and Black use line length 100. Conflicts are mitigated with `E203` ignore (Ruff no longer exposes `W503`).
- Some `ANN*` rules are ignored for practicality (e.g., not typing `self`/`cls`).
- Docstring strictness is reduced for modules, packages, and dunder methods to avoid noise.

## Maintenance
- Update `ruff.toml` when standards evolve.
- Keep exclusions minimal and reviewed periodically.
- When adding new folders, consider whether they should be excluded.
