Weight Adjust Implementation Plan
=================================

Overview
--------
- Goal: Provide a Python CLI (`weightadjust.py`) that batch-adjusts the weight axis of variable TrueType fonts by invoking FontTools’ varLib.mutator.
- Approach: Keep discovery and path logic pure; call FontTools as a module with explicit argv (no shell). Use `argparse` + `pathlib`; clear messages and safe defaults.

CLI Design
----------
- Command: `python weightadjust.py <weight> [PATHS ...] [-o OUTPUT_DIR]`
- Positional:
  - `weight`: Target numeric weight for the `wght` axis (e.g., 300, 400, 700). Accepts integer or float; validated per-font when possible.
  - `PATHS`: One or more file or directory paths. Directories are traversed recursively.
- Options:
  - `-o, --output`: Output directory for adjusted fonts (default: current working directory).
  - `-q, --quiet`: Reduce logging to warnings/errors.
  - `-v, --verbose`: Increase logging verbosity.
- Exit codes:
  - `0` success; `1` usage/environment issue; `2` runtime failure (per-font errors).

Constraints & Scope
-------------------
- Supported inputs: `.ttf` only (case-insensitive).
- Requires variable fonts with a `wght` axis; static fonts are skipped with a warning (or fail with a clear error) per behavior below.
- Output filename pattern: `<stem>-<weight>.<ext>` in the selected output directory.

Dependencies
------------
- Python package: `fonttools` (available via `requirements.txt`).
- Execution path: Invoke FontTools mutator via module to avoid shell: `python -m fontTools.varLib.mutator`.
- No additional third‑party packages required.

Directory Layout
----------------
- `weightadjust.py`: CLI entry point and orchestrator.

Core Flow
---------
1. Parse arguments, resolve paths, configure logging.
2. Discover input fonts from files/dirs (filter `.ttf`).
3. For each font, determine output path: `<OUTPUT_DIR>/<stem>-<weight>.ttf`.
4. Validate weight against the font’s `wght` axis range when available; otherwise proceed and surface mutator errors if any.
5. Build argv to run `python -m fontTools.varLib.mutator <font> wght=<weight> -o <out>`.
6. Execute sequentially; collect successes/failures; print a summary; return non‑zero if any failures.

Functions & Types
-----------------
- `def is_ttf(path: Path) -> bool`
  - Returns True if `path` has extension `.ttf` (case-insensitive).

- `def discover_ttf(inputs: list[Path]) -> list[Path]`
  - Pure discovery over provided files/dirs. Returns sorted, de‑duplicated `.ttf` files that exist.

- `def parse_weight(value: str) -> float`
  - Parses the CLI `weight` to `float`; raises `argparse.ArgumentTypeError` on invalid input (NaN/inf/negative).

- `def read_wght_range(ttf_path: Path) -> tuple[float, float] | None`
  - Attempts to open the font with FontTools and read the `fvar` axis range for `wght`. Returns `(min, max)` or `None` if not a variable font / axis missing.

- `def build_mutator_argv(font: Path, weight: float, out_path: Path, py_exe: str = sys.executable) -> list[str]`
  - Returns `[py_exe, "-m", "fontTools.varLib.mutator", str(font), f"wght={weight}", "-o", str(out_path)]`.

- `def run_mutator(argv: list[str]) -> CompletedProcess`
  - Executes the command via `subprocess.run(..., capture_output=True, text=True)`; returns the completed process.

- `def adjust_font_weight(font: Path, weight: float, out_dir: Path, runner: Callable[[list[str]], CompletedProcess]) -> None`
  - Orchestrates per-font validation, argv construction, execution, and error handling.

- `def main(argv: list[str] | None = None) -> int`
  - CLI entry; wires everything together, prints summary, and returns exit code.

Implementation Notes
--------------------
- Weight parsing: allow floats to support fractional weights; format weight for filenames without trailing `.0` (e.g., `400`, `425.5`).
- Range validation: If `read_wght_range` yields a range and `weight` is outside, either:
  - Default behavior: error for that font with message "weight X outside [min, max] for font" and continue others.
  - Future flag: `--clamp` could clamp to range instead of erroring.
- Logging: one line per font with status; on failure, print stderr snippet from mutator.
- Determinism: process fonts in sorted order for reproducible output.

Error Handling
--------------
- No inputs found after discovery:
  - Exit with code 1 and message: "No .ttf files found under provided paths.".
- Missing `wght` axis:
  - If `fvar`/axis missing, either skip with warning or attempt mutator and relay error. Prefer skip with actionable warning: "No `wght` axis found; <font> is not a variable font.".
- Mutator non‑zero exit:
  - Raise `RuntimeError` in `adjust_font_weight` with stdout/stderr included; main catches, records failure, and continues.
- Filesystem:
  - Create `out_dir` if missing; fail fast on unwritable directories with a clear message.

Font Discovery
--------------
- Inputs: mix of files and directories; non‑existent paths log a warning and are ignored.
- Recursion: `Path.rglob('*.ttf')` for directories; case-insensitive match by normalizing suffix.
- De‑duplication: resolve paths and return a sorted unique list.

Weight Execution
----------------
- Command:
  - `python -m fontTools.varLib.mutator "<font>" wght=<weight> -o "<OUTPUT_DIR>/<stem>-<weight>.ttf"`
- Rationale for module form:
  - More portable across environments than depending on the `fonttools` console script name.

Testing Plan
------------
- Unit tests (pytest):
  - `is_ttf`: extensions permutations.
  - `discover_ttf`: files/dirs mix, missing paths, deterministic ordering.
  - `parse_weight`: valid/invalid inputs; integer vs float formatting for names.
  - `read_wght_range`: mocked `TTFont` to yield ranges; missing axis returns `None`.
  - `build_mutator_argv`: exact argv formatting and paths.
  - `adjust_font_weight`: runner success and failure paths; out path resolution.
- Isolation:
  - No actual font processing in tests; mock FontTools and subprocess; use `tmp_path` for FS.

Usage Examples
--------------
- Adjust a single font to weight 400 into the current directory:
  - `python weightadjust.py 400 ./fonts/MyVarFont.ttf`
- Adjust all `.ttf` under a directory into `./out`:
  - `python weightadjust.py 700 ./fonts -o ./out`

Security & Privacy
------------------
- Do not use shell=True; pass argv as a list to `subprocess.run`.
- Sanitize/resolve paths; write only to the explicit output directory.
- Surface errors verbosely without leaking environment secrets.

Future Enhancements
-------------------
- `--clamp`: clamp weight to axis range instead of erroring.
- `--suffix`: customize output filename suffix pattern.
- `--jobs N`: parallel processing for large batches.
- Support additional axes (e.g., `wdth`) with syntax like `--axis wght=400,wdth=90`.

