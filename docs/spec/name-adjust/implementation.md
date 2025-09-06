Name Adjust Implementation Plan
================================

Overview
--------
- Goal: Provide a Python CLI (`nameadjust.py`) that normalizes and updates a font’s internal names (name table) based on a Humanized form of its filename, matching the Spec (`./spec.md`).
- Approach: Keep the transformation from filename → Humanized name pure and well‑tested; isolate font I/O to a small function using FontTools. Default behavior updates in place; optional `-o` writes a copy with updated internals.

CLI Design
----------
- Command: `python nameadjust.py [PATHS ...] [-o OUTPUT_DIR]`
- Inputs:
  - One or more file or directory paths. Directories are traversed recursively.
  - Supported: `.ttf` only (case‑insensitive).
- Options:
  - `-o, --output OUTDIR`: Write adjusted copies into this directory (default: in‑place update).
- Exit codes:
  - `0` success; `1` usage/environment issue; `2` runtime failure (per‑font errors).

Dependencies
------------
- Python package: `fonttools` (see `requirements.txt`).
- No subprocesses; pure Python with FontTools.

Core Flow
---------
1. Parse arguments and discover `.ttf` files recursively from inputs (deterministic ordering).
2. For each font path:
   - Derive the filename stem and compute a Humanized name using the rules below.
   - Split the Humanized name into Family/Subfamily (best‑effort heuristics).
   - Open the font with FontTools and update name records:
     - Family (nameID 1), Subfamily (nameID 2), Full name (nameID 4), PostScript name (nameID 6).
     - Write both Windows (3,1,0x409) and Mac (1,0,0) platform records.
   - Determine a cleaned output filename based on the computed Family/Subfamily:
     - Build `<Family>-<Subfamily>` as the stem, then replace spaces with underscores; retain the hyphen between Family and Subfamily.
   - Save in place (renaming the file to the cleaned stem when necessary), or to `OUTDIR/<cleaned-filename>` when `-o` is provided.
3. Print per‑font `OK/FAIL` summaries and a final count.

Humanization Rules
------------------
- Tokenize: split the filename stem on underscores (`_`) and hyphens (`-`).
- Preserve CamelCase: leave tokens that contain an internal capital sequence unchanged (e.g., `PragmataProMono`, `NerdFont`).
- Title‑case lower/uppercase words: `extra-bold` → `Extra Bold`, `italic` → `Italic`, `regular` → `Regular`.
- Remove version tokens: drop tokens that look like a version number from the Humanized name. A token is considered a version when it matches `^(?:v)?\d+(?:[._]\d+)*$` (e.g., `0902`, `v1`, `1.0`, `v1.2.3`). Tokens with mixed alnum (e.g., `H2`) are preserved.
- Drop common variable‑font markers: remove standalone `VF` (case‑insensitive). Optionally drop `VAR`/`Variable` if present as a standalone token.
- Join with single spaces; collapse multiple delimiters and trim edges.

Family/Subfamily Heuristics
---------------------------
- Recognized style/weight tokens (case‑insensitive):
  - `Thin`, `Extra Light`, `Light`, `Regular`, `Medium`, `Semi Bold`, `Bold`, `Extra Bold`, `Black`, `Italic` (and combinations like `Bold Italic`).
- If the trailing tokens form a recognized style phrase, assign that phrase to Subfamily and the preceding tokens to Family.
- Otherwise, set Family to the entire Humanized string and Subfamily to `Regular`.

Name Table Updates
------------------
- Family (ID 1): set to computed Family.
- Subfamily (ID 2): set to computed Subfamily (default `Regular`).
- Full (ID 4): `<Family> <Subfamily>` (strip extra spaces).
- PostScript (ID 6): `<Family>-<Subfamily>` with spaces removed in each part and only allowed characters `[A-Za-z0-9-]` (strip/replace others). Ensure non‑empty and <= 63 chars when possible.
- Platforms: write Windows (3,1,0x409) and Mac (1,0,0) variants for all above IDs.

Filename Normalization
----------------------
- Build the output filename from computed names, not the original:
  - Stem: `<Family>-<Subfamily>`; replace spaces with underscores; retain the hyphen between Family and Subfamily.
  - Extension: preserve original extension (currently `.ttf`).
- In-place mode: rename the file to the cleaned filename before writing, when the stem differs.
- Output dir mode (`-o`): write to `OUTDIR/<cleaned-filename>`.

Functions & Types
-----------------
- `def is_ttf(path: Path) -> bool`:
  - Suffix check for `.ttf`.

- `def discover_ttf(inputs: Iterable[Path]) -> list[Path]`:
  - Reuse pattern from `weightadjust.py`: resolve deduped, sorted `.ttf` files from files/dirs.

- `def humanize_stem(stem: str) -> str`:
  - Pure transformation from filename stem → Humanized string (implements tokenization, version filtering, casing, and join).

- `def make_clean_stem(family: str, subfamily: str) -> str`:
  - Returns `<Family>-<Subfamily>` with spaces replaced by underscores.

- `def split_family_subfamily(humanized: str) -> tuple[str, str]`:
  - Returns `(family, subfamily)` using the heuristics above.

- `def ps_name(family: str, subfamily: str) -> str`:
  - Returns PostScript name: `<Family>-<Subfamily>` with spaces removed and characters normalized to `[A-Za-z0-9-]`.

- `def rewrite_name_table(ttf_in: Path, *, out_path: Path | None, family: str, subfamily: str) -> Path`:
  - Opens the font, updates IDs 1/2/4/6 for Windows/Mac, saves in place or to `out_path`; returns the written path.

- `def process_font(path: Path, out_dir: Path | None) -> Path`:
  - Orchestrates: compute Humanized, split family/subfamily, call `rewrite_name_table`, return written path.

- `def main(argv: list[str] | None = None) -> int`:
  - Parse args, discover fonts, run sequentially, print summary.

Implementation Notes
--------------------
- Title‑casing: use `str.title()` for simple lower/upper tokens, but retain original token for CamelCase (detect via `[a-z][A-Z]`).
- Token filtering: drop tokens that are exactly `VF` case‑insensitively; consider extending to `VAR`/`Variable` if needed.
- Version detection: treat tokens as versions when they match `^(?:v)?\d+(?:[._]\d+)*$`.
- Style phrase detection: normalize spaces and dashes, then match against a small set of known phrases; support two‑word combos like `Extra Bold`, `Semi Bold`, and `Bold Italic`.
- PostScript constraints: strip characters outside `[A-Za-z0-9-]`; collapse repeated hyphens; trim edges.
- In‑place vs copy: when `-o` is provided, open the original and write a cleaned copy to `<OUTDIR>/<cleaned-filename>`.
- Determinism: process fonts in sorted order; print consistent OK/FAIL lines.

Error Handling
--------------
- Missing `fonttools`: raise a clear `RuntimeError("fonttools not installed; see requirements.txt")` at runtime when attempting to open a font.
- Invalid/unsupported fonts: propagate FontTools exceptions with context: `"failed to open '<path>': <reason>"`.
- Write failures: surface path and underlying error; skip file and continue.
- No inputs found: exit code 1 with message `"No .ttf files found under provided paths."`.

Testing Plan
------------
- Unit tests (pytest):
  - `humanize_stem`: token splits, title‑case, CamelCase preservation, numeric handling, `VF` removal, multi‑delimiter collapsing.
  - `split_family_subfamily`: trailing style recognition, default Regular, multi‑word styles.
  - `ps_name`: character filtering and formatting.
  - `discover_ttf`: mix of files/dirs, case‑insensitive suffix, determinism.
  - End‑to‑end (light): create a minimal TTFont programmatically with a name table, write to temp `.ttf`, run `rewrite_name_table`, and assert IDs 1/2/4/6 for both platforms.

Usage Examples
--------------
- Update names in place:
  - `python nameadjust.py ./patched/PragmataProMonoVF_liga_0902-Extra-bold-NerdFont.ttf`
- Write copies to `./out`:
  - `python nameadjust.py ./fonts -o ./out`

Security & Privacy
------------------
- No shell execution; only local file I/O.
- Write only to the specified output directory or in place. Do not traverse outside the intended paths.

Future Enhancements
-------------------
- `--dry-run` to preview computed Family/Subfamily and Full names without writing.
- Support `.otf` where FontTools permits safe name rewriting.
- Optional mapping file to customize token normalization and style detection.
