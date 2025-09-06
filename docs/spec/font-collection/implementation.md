Font Collection Creator — Implementation Plan
=============================================

Overview
--------
- Goal: Implement `createcollection.py`, a Python CLI that creates a TTC/OTC from a set of fonts, following the Spec (`./spec.md`). Naming normalization is handled by `nameadjust.py`; this tool does not infer weight/style from names.
- Approach: Keep discovery, minimal basename inference, and OS/2-based sorting pure and testable; isolate FontTools I/O and writing. Prefer explicit validation and clear, actionable errors.

CLI Design
----------
- Command: `python createcollection.py [PATHS ...] [-o OUTDIR] [--type {ttc,otc}] [--name NAME] [--dry-run] [-q|-v]`
- Inputs: mix of files/dirs; recursive discovery; supports `.ttf` and `.otf`.
- Options:
  - `-o, --output OUTDIR`: Output directory (default: `.`).
  - `--type {ttc,otc}`: Force output container type; otherwise inferred from inputs.
  - `--name NAME`: Override base filename (no extension).
  - `--dry-run`: Print plan only; do not write files.
  - `-q, --quiet` and `-v, --verbose`: Adjust verbosity.
- Exit codes: `0` success; `1` usage/environment issue; `2` runtime failure (write/IO or FontTools errors).

Dependencies
------------
- Python: `fonttools` (see `requirements.txt`).
- No external binaries. Use `fontTools.ttLib.TTFont` and `fontTools.ttLib.ttCollection.TTCollection` to write collections.

Constants & Types
-----------------
- `ITALIC_TOKENS: set[str]` — `{ "italic", "oblique" }` (used only for minimal basename fallback).
- `SUPPORTED_EXTS = {".ttf", ".otf"}`.

Core Functions
--------------
- `def is_ttf(path: Path) -> bool` / `def is_otf(path: Path) -> bool`
  - Case-insensitive suffix checks.

- `def discover_fonts(inputs: Iterable[Path]) -> list[Path]`
  - Pure: resolve, deduplicate, sort; filter to supported extensions.

- `def sniff_sfnt_type(path: Path) -> Literal["ttf", "otf"]`
  - Read first 4 bytes: `b"OTTO"` → `"otf"`; `b"\x00\x01\x00\x00"` or `b"true"` → `"ttf"`; else raise `ValueError("unrecognized sfnt header")`.
  - Used to validate consistency with suffix and to enforce collection type.

- `def infer_collection_type(paths: Sequence[Path], forced: str | None) -> Literal["ttc", "otc"]`
  - If `forced` given, return it after validating all inputs match (`ttf` for `ttc`, `otf` for `otc`). Else infer from uniform `sniff_sfnt_type` over inputs; raise on mixed.

- `def read_family_and_subfamily(path: Path) -> tuple[str | None, str | None]`
  - Lazy-import `TTFont`; open with `lazy=True`; prefer Typographic IDs 16 (Family) and 17 (Subfamily); fallback to Legacy IDs 1/2. Prefer Windows (3,1,0x409) then Mac (1,0,0). Normalize whitespace; return `None` if unavailable.

- `def tokenize_stem(stem: str) -> list[str]`
  - Split on `-` and `_`, collapse empties; lowercase tokens.

- `def _strip_nonfamily_tokens(tokens: list[str]) -> list[str]`
  - Remove only obvious non-family tokens for basename inference: Italic/Oblique; `VF`/`Variable`/`Var`; version-like tokens.

- `def common_token_prefix(list_of_tokens: Sequence[list[str]]) -> list[str]`
  - Compute the longest common prefix over lists of tokens.

- `def sanitize_filename(name: str) -> str`
  - Replace spaces with `-`, drop chars outside `[A-Za-z0-9._-]`, collapse `-`, trim edges.

- `def derive_collection_basename(fonts: Sequence[Path]) -> str`
  - Attempt internal Family consensus: collect Typographic Families (ID 16); if a single non-empty normalized family exists, use it. Else, use filename path: tokenize stems → drop only non-family tokens → `common_token_prefix`; if empty, fallback to parent directory name of first font (or stem). Sanitize final.

- `def read_weight_and_italic(path: Path) -> tuple[int | None, bool]`
  - Read `OS/2.usWeightClass` for weight; read `OS/2.fsSelection` bit 0 for Italic with `head.macStyle` bit 1 fallback.

- `def sort_fonts(fonts: Sequence[Path]) -> list[Path]`
  - Build tuples `(OS/2 weight or 1000, italic flag, filename)` and sort.

- `def write_collection(fonts: Sequence[Path], out_path: Path, kind: Literal["ttc", "otc"]) -> None`
  - Validate with `sniff_sfnt_type` against `kind` (`ttc`→`ttf`, `otc`→`otf`).
  - Lazy-import `TTFont` and `TTCollection`; open each font `TTFont(path, lazy=True, recalcTimestamp=False)`.
  - Create `TTCollection(fonts=list_of_ttfonts)` and `save(out_path)`.
  - Ensure all files closed on error (try/finally close).

- `def main(argv: list[str] | None = None) -> int`
  - Parse args; discover fonts; error if none. Infer `kind`; derive base name unless `--name`. Compose `out_path`. If `--dry-run`, print planned name, type, count, and include list; return 0. Else call `write_collection`. Print summary, return 0 on success.

Implementation Notes
--------------------
- Purity & testability: keep discovery, minimal basename logic, tokenization, and sorting pure. Hide FontTools behind `read_family_and_subfamily`, `read_weight_and_italic`, and `write_collection` for easy mocking. Ensure name reads prefer ID 16.
- Performance: use `lazy=True` when opening TTFont to avoid parsing entire tables. Collection writing remains I/O bound; inputs typically small N.
- Determinism: sort inputs deterministically before any processing; use consistent tokenization and normalization.
- Formatting: retain original Family case when used as filename base; only sanitize for filesystem safety.

Error Handling
--------------
- No inputs after discovery: exit 1 with "No supported fonts found (.ttf/.otf).".
- Mixed TTF/OTF without `--type`: exit 1 with guidance to filter inputs or pass `--type`.
- `fonttools` missing: raise `RuntimeError("fonttools not installed; see requirements.txt")` from the FontTools-using functions; main catches and reports.
- Write failure: propagate exception with context including `out_path`.

Testing Plan
------------
- Unit tests (pytest):
  - `discover_fonts`: files/dirs mix, suffix filter, de-dupe, sorted outputs.
  - `sniff_sfnt_type`: header bytes classification; error on unknown header (use temp files with minimal bytes).
  - `infer_collection_type`: ttf-only→ttc, otf-only→otc, mixed→error; forced type validation.
  - `tokenize_stem` / `_strip_nonfamily_tokens` / `common_token_prefix` / `sanitize_filename`: tokenization and minimal basename logic.
  - `derive_collection_basename`: internal-name consensus vs filename fallback; sanitization; fallback to parent dir name.
  - `read_weight_and_italic` and `sort_fonts`: deterministic order; italic precedence.
  - `write_collection`: monkeypatch `TTFont` and `TTCollection` to capture calls, validate open order and `save` path; ensure files are closed on error.
- CLI smoke tests: parse-only with `--dry-run` over temp dummy files; validate printed plan and exit code.

Usage Examples
--------------
- `python createcollection.py ./patched -o ./out`
- `python createcollection.py A-Regular.otf A-Bold.otf --type otc --name AFamily -o ./out`
- `python createcollection.py ./fonts --dry-run`

Security & Privacy
------------------
- No shell execution; only local file I/O through FontTools.
- Sanitize output filename; write only into user-specified `--output` or current directory.

Future Enhancements
-------------------
- `--name-from`: choose between `family`, `filename`, or `directory` strategies explicitly.
- `--include-italic-first`: flip Roman/Italic precedence for custom workflows.
- Support sub-collections by axis/style grouping, or multiple collections from a directory tree.
