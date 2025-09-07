# Linting & Styling Spec

Purpose: establish clear, automated linting and formatting rules for this repository to keep code readable, consistent, and modern.

## Tools
- Ruff (linting, import sorting, modernization)
- Black (formatting)

Configuration lives in `pyproject.toml` for both tools.

## Python Version
- Target: Python 3.11 (`target-version = "py311"`)

## Global Settings
- Line length: 100 characters
- Exclusions: `FontPatcher/`, `fonts/`, `fonts_weighted/`, `patched/`, `collection/`, `docs/_build/`

## Enabled Rule Sets (Ruff)
- E/W: pycodestyle errors/warnings
- F: pyflakes
- I: isort (import sorting via Ruff)
- UP: pyupgrade (modernize syntax)
- N: pep8-naming
- B: flake8-bugbear
- C4: flake8-comprehensions
- SIM: flake8-simplify
- C90: mccabe complexity (max 15)
- D: pydocstyle (Google convention)
- PT: pytest style
- ANN: flake8-annotations
- ERA: eradicate commented-out code
- ICN/ISC/TID/PTH/RET/RUF: additional correctness and style improvements

## Ignored Rules (intentional)
- E203: Compatible with Black’s formatting
- ANN401: Reasonable exceptions for pragmatic `Any`
- D100, D104, D105, D107, D203, D213, D417: Reduce docstring noise; follow Google style

## Docstring Convention
- Google style (`[lint.pydocstyle] convention = "google"`)
- Tests relax docstring requirements (`tests/**/*` ignore `D`, `ANN`)

## Complexity Budget
- McCabe complexity: 15

## Formatting
- Use Black for code formatting (not Ruff formatter).
- Black configured in `pyproject.toml` with `line-length = 100` and exclusions mirroring Ruff.

## Developer Workflow
1. Write code with type hints where non-trivial; keep functions small.
2. Run Ruff on changed files: `ruff check path/to/file.py`
3. Auto-fix where safe: `ruff check --fix path/to/file.py`
4. Format: `black path/to/file.py`
5. Run tests: `pytest -q`

## CI Expectations (recommended)
- Lint (Ruff check) and format (Black --check) must pass.
- Test suite must pass.
