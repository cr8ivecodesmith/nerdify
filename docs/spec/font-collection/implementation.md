Font Collection Creator — Implementation Plan
=============================================

Overview
--------
- Goal: Implement `createcollection.py`, a Python CLI that creates a TTC/OTC from a set of fonts, following the Spec (`./spec.md`).
- Approach: Keep discovery, naming, and sorting pure and testable; isolate FontTools I/O and writing to one place. Prefer explicit validation and clear, actionable errors.

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
- `WEIGHT_MAP: dict[str, int]` — maps canonical weight keywords to numeric values (e.g., `"thin":100`, `"extra light":200`, ..., `"black":900`). Include synonyms (`"extrabold" → 800`, `"semi bold" → 600`).
- `ITALIC_TOKENS: set[str]` — `{ "italic", "oblique" }`.
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
  - Lazy-import `TTFont`; open with `lazy=True`; read nameIDs 1 (Family) and 2 (Subfamily) preferring Windows (3,1,0x409) then Mac (1,0,0). Normalize whitespace; return `None` if unavailable.

- `def tokenize_stem(stem: str) -> list[str]`
  - Split on `-` and `_`, collapse empties; lowercase tokens; keep alnum and words.

- `def strip_style_tokens(tokens: list[str]) -> list[str]`
  - Remove tokens matching weight keywords and italic markers; keep others for base-name derivation.

- `def common_token_prefix(list_of_tokens: Sequence[list[str]]) -> list[str]`
  - Compute the longest common prefix over lists of tokens.

- `def sanitize_filename(name: str) -> str`
  - Replace spaces with `-`, drop chars outside `[A-Za-z0-9._-]`, collapse `-`, trim edges.

- `def derive_collection_basename(fonts: Sequence[Path]) -> str`
  - Attempt internal Family consensus: collect families; if a single non-empty normalized family exists, use it. Else, use filename path: humanize stems via `tokenize_stem` → `strip_style_tokens`, compute `common_token_prefix`; if empty, fallback to parent directory name of first font (or stem of first font). Sanitize final.

- `def weight_and_style_from_names(family: str | None, subfamily: str | None, stem: str) -> tuple[int | None, bool]`
  - Determine weight (numeric) and italic flag from subfamily first; fallback to family/stem tokens using `WEIGHT_MAP` and `ITALIC_TOKENS`.

- `def sort_fonts(fonts: Sequence[Path]) -> list[Path]`
  - Build tuples `(weight or 1000, italic as int (0 for roman, 1 for italic), normalized_stem)` and sort.

- `def write_collection(fonts: Sequence[Path], out_path: Path, kind: Literal["ttc", "otc"]) -> None`
  - Validate with `sniff_sfnt_type` against `kind` (`ttc`→`ttf`, `otc`→`otf`).
  - Lazy-import `TTFont` and `TTCollection`; open each font `TTFont(path, lazy=True, recalcTimestamp=False)`.
  - Create `TTCollection(fonts=list_of_ttfonts)` and `save(out_path)`.
  - Ensure all files closed on error (try/finally close).

- `def main(argv: list[str] | None = None) -> int`
  - Parse args; discover fonts; error if none. Infer `kind`; derive base name unless `--name`. Compose `out_path`. If `--dry-run`, print planned name, type, count, and include list; return 0. Else call `write_collection`. Print summary, return 0 on success.

Implementation Notes
--------------------
- Purity & testability: keep discovery, naming, tokenization, sorting pure. Hide FontTools behind `read_family_and_subfamily` and `write_collection` for easy mocking.
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
  - `tokenize_stem` / `strip_style_tokens` / `common_token_prefix` / `sanitize_filename`: tokenization and naming edge cases.
  - `derive_collection_basename`: internal-name consensus vs filename fallback; sanitization; fallback to parent dir name.
  - `weight_and_style_from_names` and `sort_fonts`: mapping correctness and deterministic order; italic precedence.
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
