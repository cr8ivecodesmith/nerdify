Font Collection Creator
===

## Description

A CLI tool (`createcollection.py`) that builds a TrueType Collection (TTC) or OpenType Collection (OTC) from a given set of compatible fonts. It expects inputs that have already had their internal names normalized (e.g., via `nameadjust.py`) in line with the Collection Naming Playbook (`docs/spec/font-collection/spec-naming.md`), but does not enforce or verify that step.

## Usage

createcollection.py [font files or dirs ...] [-o OUTDIR] [--type {ttc,otc}] [--name NAME] [--dry-run]

## Behavior

- Discovers fonts from provided files and directories (recursive), filters supported types, and assembles them into a single collection file.
- Determines the collection container format automatically unless overridden:
  - If `--type` is specified, enforce it (`ttc` for TrueType, `otc` for CFF/OpenType).
  - If not specified, infer from inputs: all TTF → TTC; all OTF → OTC; mixed types → error.
- Orders fonts deterministically in the collection using a weight/style heuristic:
  - Sort by recognized weight (100–900 Thin→Black), then Roman before Italic.
  - When weight/style cannot be determined from internal names, fall back to filename heuristics.
- Names the output collection file based on internal names when possible, with a clear fallback:
  - Preferred: use the common Typographic Family (nameID 16) shared by all fonts: `<Family>.ttc|.otc`.
  - If nameID 16 is missing or inconsistent, fall back to a common Legacy Family (nameID 1) when consistent.
  - If internal families still differ or are missing, compute a base name from filename stems by removing trailing weight/style tokens and taking the longest common non-empty prefix of tokens: `<BaseName>.ttc|.otc`.
  - Normalize the final filename to safe characters (A–Z, a–z, 0–9, dash, underscore, dot); convert spaces to underscores, retain dashes, and collapse repeats.
  - Allow explicit override via `--name NAME` (filename becomes `NAME.ttc|.otc`).
- Validates compatibility constraints to avoid creating invalid collections:
  - All inputs must share the same SFNT flavor: TrueType (`\x00\x01\x00\x00`) for TTC, or CFF/CFF2 (`OTTO`) for OTC.
  - Reject mixed outline types (e.g., mixing TTF and OTF) unless the user forces `--type` and all fonts actually match the enforced type; otherwise, error with guidance.
- Writes the collection into `OUTDIR` (default: current working directory). Does not modify original fonts.
- Prints a concise summary: discovered, included, skipped (with reasons), output path.

## Inputs

- Supported file types: `.ttf` for TTC, `.otf` for OTC (case-insensitive). Others are ignored with a warning.
- Directories are traversed recursively; non-existent inputs are warned and skipped.

## Options

- `-o, --output OUTDIR`: Output directory (default: `.`). Created if missing.
- `--type {ttc,otc}`: Force output container type. When omitted, inferred from inputs.
- `--name NAME`: Override the auto-generated collection filename (without extension).
- `--dry-run`: Do not write any files; print what would be included and the resulting name/type.
- `-q, --quiet` / `-v, --verbose`: Adjust log verbosity.

## Naming Rules (Details)

1) Internal-name path (preferred):
   - Read Typographic Family (nameID 16) of each font. If all share the same normalized family string, use it.
   - Fallback: if 16 is unavailable or inconsistent, read Legacy Family (nameID 1) and use it when consistent.
   - Normalization: strip extra whitespace; map multiple spaces to one; keep original case; do not inject style tokens.

2) Filename path (fallback):
   - Derive humanized stems by splitting on `_` and `-`, removing known style/weight tokens (e.g., Regular, Bold, Italic, Thin… Extra Bold), markers like `VF`/`VAR`, and version tokens that look like `^(?:v)?\d+(?:[._]\d+)*$` (e.g., `0902`, `v1`, `1.0`, `v1.2.3`); then join remaining tokens with spaces.
   - Compute the longest common prefix by tokens; if empty, use the immediate parent directory name.

3) Filesystem-safe conversion:
   - Replace spaces with `_`, remove characters outside `[A-Za-z0-9._-]`, collapse repeated `_` and `-`, trim leading/trailing separators.

Examples:
- Fonts with Typographic Family (ID 16) `Cool Font`: `Cool_Font.ttc` or `Cool_Font.otc`.
- If ID 16 is missing but Legacy Family (ID 1) matches `Cool Font`, use `Cool_Font`.
- Mixed families or missing internals, filenames like `CoolFont-Regular.ttf`, `CoolFont-Bold.ttf`: `CoolFont.ttc`.

## Sorting Heuristic

- Use the following weight order when determinable: 100 Thin, 200 Extra Light, 300 Light, 400 Regular, 500 Medium, 600 Semi Bold, 700 Bold, 800 Extra Bold, 900 Black.
- Roman precedes Italic for the same weight.
- Source of truth for style/italic and weight:
  - Prefer Typographic Subfamily (nameID 17); fallback to Legacy Subfamily (nameID 2); finally filename tokens.
  - Treat “Bold” strictly for bold-only styles (do not infer bold from Medium/600).
- If no internal name-based weight is detected, infer from filename tokens; otherwise, leave relative order but maintain deterministic sort by filename as a final tiebreaker.

## Constraints & Scope

- No cross-type mixing in a single collection (TTF with OTF) — error with guidance.
- Does not de-duplicate or merge incompatible table graphs beyond what FontTools supports for collections; relies on FontTools to produce valid TTC/OTC containers from the given fonts.
- Only local file I/O; no network access.

## Dependencies

- Python: `fonttools` (see `requirements.txt`).
- No external binaries. Uses FontTools to open fonts and write a TTC/OTC container.

## Core Flow

1. Parse args; resolve and validate `OUTDIR`.
2. Discover input fonts from files/dirs; filter supported suffixes; resolve to absolute paths; sort deterministically.
3. Determine container type (`ttc`/`otc`) from `--type` or from inputs; validate consistency.
4. Extract naming signals (internal Family, Style/Subfamily) and build the collection base name unless overridden with `--name`.
5. Order fonts using the sorting heuristic.
6. Open fonts with FontTools (`TTFont`) in a memory-efficient mode.
7. Assemble and write a collection using FontTools’ collection writer to `OUTDIR/<name>.<ext>`.
8. Print summary and exit with non-zero status if no valid fonts or on write error.

## Functions & Types (Sketch)

- `def is_ttf(path: Path) -> bool` / `def is_otf(path: Path) -> bool`
  - Suffix checks; case-insensitive.

- `def discover_fonts(inputs: Iterable[Path]) -> list[Path]`
  - Pure discovery: resolve, deduplicate, sort; filter to `.ttf`/`.otf` only.

- `def detect_sfnt_type(font: Path) -> Literal["ttf", "otf"]`
  - Open minimal header (or use FontTools) to distinguish TrueType vs CFF/CFF2.

- `def infer_collection_type(paths: list[Path], forced: str | None) -> Literal["ttc", "otc"]`
  - From `forced` or uniform input types; raise on mixed inputs.

- `def read_family_and_style(path: Path) -> tuple[str | None, str | None]`
  - Returns `(family, subfamily)` from the name table, preferring Typographic IDs (16/17) with Legacy IDs (1/2) fallback.

- `def humanize_stem(stem: str) -> list[str]`
  - Tokenizes and removes style/weight tokens (aligned with the playbook); returns remaining tokens for naming.

- `def derive_collection_basename(fonts: list[Path]) -> str`
  - Uses internal names if consistent; else longest common token prefix of humanized stems; filesystem-sanitized.

- `def sort_fonts(fonts: list[Path]) -> list[Path]`
  - Applies weight/style ordering with filename as deterministic tiebreaker.

- `def write_collection(fonts: list[Path], out_path: Path, kind: Literal["ttc", "otc"]) -> None`
  - Opens each font with FontTools and writes a TTC/OTC. Raises `RuntimeError` on failure.

- `def main(argv: list[str] | None = None) -> int`
  - CLI entry; wires pieces; prints summary; returns exit code.

## Error Handling

- No fonts discovered: exit 1 with message "No supported fonts found (.ttf/.otf).".
- Mixed inputs without `--type`: clear error explaining to filter inputs or specify `--type`.
- FontTools missing: raise actionable error "fonttools not installed; see requirements.txt".
- Write failure: include output path and underlying exception.

## Testing Plan

- Unit tests (pytest):
  - `discover_fonts`: files/dirs mix, suffix filtering, stable ordering.
  - `infer_collection_type`: ttf-only → ttc; otf-only → otc; mixed → error; forced overrides.
  - `derive_collection_basename`: internal-name agreement, filename fallback, sanitization.
  - `sort_fonts`: weight/style precedence and deterministic order.
  - `write_collection`: mock FontTools TTFont/collection writer; assert call order and output path; error propagation.
- No network, no real font processing: use temporary directories and mocks.

## Usage Examples

- Build a TTC from TTFs under a folder:
  - `python createcollection.py ./patched -o ./out`

- Build an OTC from explicit OTFs with a fixed name:
  - `python createcollection.py A-Regular.otf A-Bold.otf --type otc --name AFamily -o ./out`

- Preview without writing:
  - `python createcollection.py ./fonts --dry-run`

## Notes

- This tool assumes (but does not require) that inputs have been run through `nameadjust.py` so internal names are clean and consistent per `spec-naming.md` (IDs 16/17/1/2/4/6 aligned; style flags consistent).
- The collection file’s name is a filesystem artifact; the TTC/OTC container itself does not carry a single unified display name; individual fonts retain their internal names.
