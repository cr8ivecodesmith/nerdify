Nerdify Implementation Plan
===========================

Overview
--------
- Goal: Provide a Python CLI (`nerdify.py`) that patches one or more fonts with Nerd Fonts’ glyphs by automating Font Patcher setup and invocation.
- Approach: Keep core logic pure and testable; isolate I/O and subprocess calls. Use `argparse` + `pathlib`. Prefer explicit, predictable behavior and clear errors.

CLI Design
----------
- Command: `python nerdify.py [PATHS ...] [-o OUTPUT_DIR]`
- Inputs:
  - One or more file or directory paths. Directories are traversed recursively.
  - Supported font extensions: `.ttf`, `.otf`, `.ttc` (case-insensitive).
- Options:
  - `-o, --output`: Output directory for patched fonts (default: current working directory).
  - `--fontpatcher-dir`: Optional path to a prepared `FontPatcher/` directory (overrides download).
  - `--cache-dir`: Optional path for downloaded artifacts (default: `./FontPatcher` in repo).
  - `-q, --quiet`: Reduce logging to warnings/errors.
  - `-v, --verbose`: Increase logging verbosity.
- Exit codes:
  - `0` success; `1` usage or environment issue; `2` runtime failure (patching errors).

Dependencies
------------
- System: `fontforge` (CLI with Python bindings). Validate via `fontforge -version`.
- Bundled/External:
  - Font Patcher from Nerd Fonts (directory containing `font-patcher` and assets).
  - If not supplied via `--fontpatcher-dir`, download latest `FontPatcher.zip` from Nerd Fonts releases.
- Python runtime: Standard library only (prefer no extra deps). Use `requests` for downloading files.

Directory Layout
----------------
- `nerdify.py`: CLI entry point.
- `FontPatcher/`: Default location for the unpacked font patcher and assets.
- `fonts/`: Example fonts directory (input); not required by the tool.

Core Flow
---------
1. Parse arguments, resolve paths, configure logging.
2. Check environment: ensure `fontforge` is available (fail fast with guidance to run `requirements.sh`).
3. Ensure Font Patcher is available:
   - If `--fontpatcher-dir` is provided, validate it.
   - Else, if `./FontPatcher/font-patcher` exists, reuse it.
   - Else, download `FontPatcher.zip` into cache dir and extract to `./FontPatcher`.
4. Discover fonts by walking input paths and filtering by extension.
5. For each font, invoke `fontforge -script <font-patcher> <font>. Then move the file to <OUTPUT_DIR>`.
6. Report a concise summary: processed, succeeded, failed; return non‑zero if any fonts failed.

Functions & Types
-----------------
- `def is_font_file(path: Path) -> bool`
  - Returns True if file extension is one of the supported font types.

- `def discover_fonts(inputs: list[Path]) -> list[Path]`
  - Pure function: traverses files/dirs, returns sorted unique list of font files.

- `def check_fontforge_available(run: Callable[[list[str]], CompletedProcess]) -> None`
  - Runs `fontforge -version`; raises `RuntimeError` with actionable message if unavailable.

- `def ensure_font_patcher(patcher_dir: Path | None, cache_dir: Path) -> Path`
  - Returns the path to the `font-patcher` executable. Uses provided dir or downloads/extracts latest if missing.

- `def download_fontpatcher_zip(dest_zip: Path, opener: Callable[[str], io.BufferedReader]) -> None`
  - Downloads `https://github.com/ryanoasis/nerd-fonts/releases/latest/download/FontPatcher.zip` to `dest_zip`.

- `def extract_zip(zip_path: Path, target_dir: Path) -> None`
  - Extracts archive safely, creating `target_dir`.

- `def build_patch_command(fontforge_bin: str, patcher: Path, font: Path) -> list[str]`
  - Returns `[
      fontforge_bin,
      "-script",
      str(patcher),
      str(font)
    ]`.

- `def patch_font(cmd: list[str], run: Callable[[list[str]], out_dir: Path, CompletedProcess]) -> None`
  - Executes the command and raises `RuntimeError` on non‑zero exit.

- `def main(argv: list[str] | None = None) -> int`
  - CLI entry; wires all pieces together and returns an exit code.

Implementation Notes
--------------------
- Purity and testability:
  - Keep discovery, command building, and path logic pure.
  - Pass subprocess executor and network opener as injectable callables for tests.
- Path handling:
  - Use `pathlib.Path`. Normalize and resolve inputs; ensure output dir exists.
  - Sanitize and avoid destructive defaults; write only into specified output dir.
- Concurrency:
  - Initial version runs sequentially for simplicity and predictable logging.
  - Future: optional `--jobs N` to parallelize with `ProcessPoolExecutor`.
- Skipping already patched fonts:
  - Optional heuristic: skip files whose name already contains `Nerd Font`.
  - For v1 keep behavior simple (process all inputs).

Error Handling
--------------
- Missing `fontforge`:
  - Raise with message: "fontforge not found. Install via `requirements.sh` or your package manager.".
- Missing or invalid Font Patcher directory:
  - Clear message guiding to supply `--fontpatcher-dir` or allow auto‑download.
- Download/extract failures:
  - Surface cause with path and HTTP/IO error details.
- Per‑font failures:
  - Continue processing remaining fonts; collect errors and summarize at the end.

Downloading Font Patcher
------------------------
- Source: `https://github.com/ryanoasis/nerd-fonts/releases/latest/download/FontPatcher.zip`.
- Steps:
  - Create cache dir (default `./FontPatcher`).
  - Download to `FontPatcher/FontPatcher.zip` using `urllib.request.urlopen` with a short timeout.
  - Extract into `FontPatcher/` and validate presence of `font-patcher`.
- Idempotency:
  - If `FontPatcher/font-patcher` exists, skip download.
  - If `FontPatcher.zip` exists but is corrupt, re‑download.

Font Discovery
--------------
- Inputs: mix of files and directories; non‑existent paths cause a warning and are ignored.
- Recursion: depth‑first traversal with `rglob('*')` filtered by `is_font_file`.
- De‑duplication: resolve and de‑duplicate paths; stable sort for deterministic order.

Patching Execution
------------------
- Command: `fontforge -script <FontPatcher/font-patcher> <font> --outputdir <OUTPUT_DIR>`.
- Logging: print one line per font (START, OK/FAIL) and a final summary.
- Output: the Nerd Fonts script writes patched files into `<OUTPUT_DIR>`; do not post‑process.

Testing Plan
------------
- Unit tests (pytest):
  - `discover_fonts`: files/dirs mix, extension filtering, non‑existent inputs.
  - `build_patch_command`: exact argv built with given inputs.
  - `ensure_font_patcher`: prefers provided dir; handles existing local `FontPatcher`; download path mocked.
  - `check_fontforge_available`: handles success and failure (mocked subprocess).
  - `patch_font`: raises on non‑zero returncode; passes through stdout/stderr in message.
- No network, no fontforge required in tests:
  - Mock network opener and subprocess runner; use `tmp_path` for filesystem.

Usage Examples
--------------
- Patch a single file into the current directory:
  - `python nerdify.py ./fonts/SomeFont.ttf`
- Patch all fonts under a directory into `./out`:
  - `python nerdify.py ./fonts -o ./out`
- Use a pre‑downloaded Font Patcher directory:
  - `python nerdify.py ./fonts --fontpatcher-dir ./FontPatcher`

Security & Privacy
------------------
- Do not execute shell with untrusted strings; pass argv as a list to `subprocess.run`.
- Sanitize and resolve paths; write only into the explicit output directory.
- Timeouts on network operations; fail gracefully without retries for v1.

Future Enhancements
-------------------
- `--jobs` for parallel patching.
- `--skip-patched` to avoid reprocessing "Nerd Font" files.
- Optional inclusion/exclusion glob patterns for discovery.
- Progress bar for large batches when not in `--quiet` mode.

