Weight Adjust v3 (Destructive Spec2 Alignment)
==============================================

Overview
--------
- Goal: Replace the current CLI with the Spec2 behavior by default: generate fonts for each standard weight, support a weight offset, and adopt the specified filename pattern.
- Context: This is a destructive change. We drop the positional `<weight>` argument and no longer preserve the single‑weight output naming.

Current State (Summary)
-----------------------
- Inputs: Mix of files/dirs; discovers `.ttf` recursively; deterministic ordering.
- Operation: For each discovered font, runs `python -m fontTools.varLib.mutator <font> wght=<weight> -o <out>`.
- Validation: Reads the `wght` axis range when present and errors if the requested weight is out of bounds.
- Output: Writes `<stem>-<weight>.ttf` into `--output` (default: CWD).
- CLI: `python weightadjust.py <weight> [PATHS ...] [-o OUTPUT_DIR]` (current state; will be replaced).

Spec2 Requirements (Key Points)
-------------------------------
- Generate outputs for each entry in the weights table (100–900).
- Optional weight offset (`-w/--weight-offset`) that accepts "+N"/"-N" forms and is applied to each base weight.
- Output filename format: `<primary name>-<weight name>-<weight>.<ext>`.
  - Append the numeric `<weight>` only when the offset is non‑zero; otherwise omit.
  - Apply smart heuristics where you prevent duplicating the weight name from the final output
    font name. (i.e. if the font name contains the word "Regular" or "Thin", omit from the basename
    and prefer our convention. This can appear anywhere in the name or part of a whole word)
- Traverse input directories; default output location is the working directory or user‑provided `-o`.
- Support `.ttf` only; provide clear guidance if FontTools is not installed.

Gaps vs Spec2
-------------
- No multi‑weight generation: current CLI takes one target weight.
- No `--weight-offset` handling; no parsing for `+/-` relative forms.
- Filename pattern differs: lacks weight name and conditional numeric suffix.
- Import error messaging: script imports `fontTools` at module import time; missing dependency raises a raw ImportError instead of actionable guidance.

CLI Design (v3, Destructive)
----------------------------
- Replace the CLI to match Spec2 exactly; remove positional `<weight>`.

- Usage:
  - `python weightadjust.py [PATHS ...] [-w OFFSET] [-o OUT]`

- Options:
  - `-w, --weight-offset OFFSET`: Apply a numeric offset to every base weight.
    - Accepts forms: `+10`, `-10`, `10`, `-12.5`; default `0`.
  - `-o, --output OUTDIR`: Output directory (default: `.`).

- Output naming:
  - No offset: `<stem>-<WeightName>.ttf` (e.g., `CoolFont-Regular.ttf`).
  - With offset: `<stem>-<WeightName>-<ResolvedWeight>.ttf` (e.g., `CoolFont-Regular-410.ttf`).

Weights Table
-------------
Use the standard mapping from Spec2:

- 100: Thin
- 200: Extra-Light
- 300: Light
- 400: Regular
- 500: Medium
- 600: Semi-Bold
- 700: Bold
- 800: Extra-Bold
- 900: Black

Core Flow
---------
1. Parse args; determine if `--weight-offset` is provided.
2. Discover `.ttf` fonts from inputs (existing logic reused).
3. For each font:
   - Iterate the table in ascending order. For each base value and name:
     - Compute `resolved = base + offset` and clamp to `[min, max]` if a `wght` range is available.
     - Compose output file name per rules above (apply duplication heuristics where feasible).
     - Invoke the mutator at `resolved`, writing to the composed path.
     - Update internal name records in the output font:
       - Subfamily (ID 2): `<WeightName>` or `<WeightName>-<Resolved>` when offset != 0.
       - Full name (ID 4): `<Family> <Subfamily>`.
       - PostScript (ID 6): `<Family>-<Subfamily>` with spaces removed.
4. Print a summary of successes/failures.

Functions & Changes
-------------------
- New: `WEIGHT_TABLE: list[tuple[int, str]]` defining the mapping.
- New: `parse_weight_offset(value: str) -> float`
  - Validates numeric input; accepts `+`/`-` prefixes; rejects NaN/inf.
- New: `compose_weight_basename(font: Path, weight_name: str, base: int, resolved: float, offset: float) -> str`
  - Returns `<stem>-<WeightName>` when `offset == 0`, else `<stem>-<WeightName>-<resolved>` (weight formatted via `_weight_for_filename`).
- Change: `adjust_font_weight(...)` to accept an optional `out_basename: str | None = None`.
  - When provided, use `out_path = out_dir / f"{out_basename}.ttf"` instead of `<stem>-<weight>.ttf`.
- New: `process_font_all_weights(font: Path, out_dir: Path, offset: float, ...) -> list[Path]`
  - Iterates the table, validates ranges, calls `adjust_font_weight(..., out_basename=...)`, collects results, and returns created paths.
  - Calls `_rewrite_internal_names` to update subfamily, full name, and PostScript name.

Backward Compatibility
----------------------
- Not preserved. This version removes the positional `<weight>` argument and changes default output naming to include the weight name (and numeric suffix only when a non‑zero offset is applied).

Error Handling
--------------
- FontTools availability:
  - Catch `ImportError` for `fontTools.ttLib` and raise `RuntimeError("fonttools not installed; see requirements.txt")` with actionable guidance.
  - Prefer moving the `TTFont` import inside `read_wght_range` to enable a clearer runtime message.
- Out‑of‑range in table mode:
  - Clamp the resolved weight to the font’s supported `[min, max]` range when available, ensuring 9 outputs per font.
- Subprocess failures:
  - Preserve existing behavior: raise per weight; main aggregates counts and continues.

Testing Plan
------------
- Update or replace tests to reflect the new CLI and behavior:
  - Remove/replace tests that assume a positional `<weight>` and `<stem>-<weight>.ttf` naming.
  - Add tests for `parse_weight_offset` (valid/invalid, signs, floats).
  - Add tests for `compose_weight_basename` (offset/no offset, integer vs float formatting).
  - Add tests for `process_font_all_weights` (iterates table, range skips, created files count).
  - Keep existing unit tests for discovery, argv building, range checks, and per‑font execution where applicable.
  - Import fallback: simulate missing `fontTools` and assert friendly error from `read_wght_range`.

Usage Examples
--------------
- Generate all standard weights into `./out` without offset:
  - `python weightadjust.py ./fonts -o ./out`
- Generate all standard weights with `+10` offset:
  - `python weightadjust.py ./fonts -w +10 -o ./out`

Implementation Notes
--------------------
- Determinism: process weights in ascending numeric order; process fonts in sorted order (existing behavior).
- Formatting: reuse `_weight_for_filename` to avoid trailing `.0` in suffixes.
- Performance: sequential execution is fine; table mode multiplies work by up to 9 per font but remains I/O bound.
- Purity: keep discovery and name composition pure; isolate subprocess and FS effects.

Security & Privacy
------------------
- Continue to pass argv lists to `subprocess.run` (no shell).
- Write only into the user‑specified output directory.
- Do not traverse or write outside the output tree.

Migration Notes
---------------
- This change is breaking by design to align with Spec2. Users must remove the positional `<weight>` argument and adopt the new output naming.
