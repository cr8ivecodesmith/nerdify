Weight Adjust Implementation
============================

Overview
--------
- Goal: Provide a Python CLI (`weightadjust.py`) that generates adjusted TrueType fonts for every standard weight using FontTools’ varLib.mutator, with an optional weight offset.
- Approach: Keep discovery and name composition pure; call FontTools as a module with explicit argv (no shell). Use `argparse` + `pathlib`, clear messages, and safe defaults.

CLI Design
----------
- Command: `python weightadjust.py [PATHS ...] [-w OFFSET] [-o OUTPUT_DIR]`
- Positional:
  - `PATHS`: One or more file or directory paths. Directories are traversed recursively.
- Options:
  - `-w, --weight-offset OFFSET`: Numeric offset applied to each standard weight. Accepts forms like `+10`, `-10`, `10`, `-12.5`. Default: `0`.
  - `-o, --output`: Output directory for adjusted fonts (default: current working directory).
- Exit codes:
  - `0` success; `1` no inputs found/usage issue; `2` runtime failures (per‑font errors with no outputs).

Constraints & Scope
-------------------
- Supported inputs: `.ttf` only (case-insensitive).
- Variable fonts: If a `wght` axis range is present, values are validated/clamped per behavior below.
- Output filename pattern:
  - No offset: `<stem>-<WeightName>.ttf` (e.g., `Cool-Regular.ttf`).
  - With offset: `<stem>-<WeightName>-<ResolvedWeight>.ttf` (e.g., `Cool-Regular-410.ttf`).

Dependencies
------------
- Python package: `fonttools` (see `requirements.txt`).
- Execution: invoke FontTools mutator via module: `python -m fontTools.varLib.mutator`.

Directory Layout
----------------
- `weightadjust.py`: CLI entry point and functions.

Core Flow
---------
1. Parse arguments.
2. Discover input fonts from files/dirs (filter `.ttf`).
3. For each font, iterate the standard weights (from `fontweights.toml`).
4. Compute `resolved = base + offset`; if the font exposes a `wght` range, clamp `resolved` into `[min, max]`.
5. Compose output basename per rules above; build argv `python -m FontTools.varLib.mutator <font> wght=<resolved> -o <out>`.
6. Run mutator; on success, update internal name records (subfamily/full/PostScript) to reflect weight and optional resolved number.
7. Print a summary; return non‑zero if a font produced no outputs.

Functions & Types
-----------------
- `def is_ttf(path: Path) -> bool`: True if `.ttf` extension (case-insensitive).
- `def discover_ttf(inputs: Iterable[Path]) -> list[Path]`: Pure discovery; returns sorted, de‑duplicated existing `.ttf` files.
- `def parse_weight(value: str) -> float`: Parses a numeric weight; used by internals and kept for compatibility.
- `def parse_weight_offset(value: str) -> float`: Parses `-w/--weight-offset`; accepts `+/-` forms; rejects NaN/inf.
- `def read_wght_range(ttf_path: Path) -> tuple[float, float] | None`: Reads the variable `wght` min/max if available.
- `def build_mutator_argv(font: Path, weight: float, out_path: Path, *, py_exe: str = sys.executable) -> list[str]`.
- `def run_mutator(argv: list[str]) -> CompletedProcess`.
- `def compose_weight_basename(font: Path, weight_name: str, base: int, resolved: float, offset: float) -> str`.
- `def adjust_font_weight(font: Path, weight: float, out_dir: Path, *, runner, out_basename: str | None = None) -> Path`.
- `def process_font_all_weights(font: Path, out_dir: Path, offset: float, *, runner) -> list[Path]`.
- `def main(argv: list[str] | None = None) -> int`.

Implementation Notes
--------------------
- Weight formatting: filenames drop trailing `.0` (e.g., `410` vs `410.0`).
- Range handling: when a `wght` range is available, clamp resolved weights so each font produces outputs for all standard weights.
- Determinism: process fonts and weights in sorted/numeric order.
- Logging: emit per‑font status lines and a final summary; include mutator stderr/stdout on failure.

Error Handling
--------------
- No inputs found: exit `1` with a clear message.
- Mutator failure: `adjust_font_weight` raises `RuntimeError` including stderr/stdout; `process_font_all_weights` logs per‑weight failures and continues.
- Filesystem: create output directories; surface permission errors clearly.

Testing Plan
------------
- Unit tests cover discovery, weight/offset parsing, range reading, argv building, per‑font adjustment, basename composition, and table processing. Use mocks and `tmp_path` to avoid real FontTools execution.

Security & Privacy
------------------
- Do not use `shell=True`; pass argv lists to `subprocess.run`.
- Write only to the user‑specified output directory.

Future Enhancements
-------------------
- Optional parallelism for large batches; custom suffix patterns; additional axis support (e.g., `wdth`).
