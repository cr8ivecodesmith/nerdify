# Nerdify Toolkit

Automations for working with fonts: patch fonts with Nerd Fonts glyphs, normalize font name tables from filenames, adjust variable font weights, and bundle fonts into TTC/OTC collections. The tools are small, testable Python CLIs designed for predictable, scriptable workflows.

## Background

- Patching fonts with Nerd Fonts by hand requires installing FontForge and running the Font Patcher script for every file. It’s repetitive and easy to misplace outputs.
- Fonts often have noisy filenames and inconsistent internal name tables, which makes organizing and collecting them harder.
- Creating consistent weight variants or bundling families into TTC/OTC collections is tedious without clear conventions.

This repo provides focused CLIs to make those tasks reliable and repeatable, with minimal external dependencies.

Included tools
- `nerdify.py`: Patch fonts with Nerd Fonts glyphs using Font Patcher.
- `nameadjust.py`: Normalize filename → internal name table (Family/Subfamily, Full, PostScript).
- `weightadjust.py`: Generate standard weight instances from variable TTFs (with optional offset).
- `createcollection.py`: Build a TrueType/OpenType collection (TTC/OTC) from multiple fonts.

See detailed specs under `docs/spec/` organized by feature: `nerdify/`, `name-adjust/`, `weight-adjust/`, `font-collection/`.

## Installation

Prerequisites
- Python 3.x and `pip`.
- `fonttools` (Python) for name and collection utilities.
- `fontforge` (system binary) only for `nerdify.py` (Font Patcher requires it).

Steps
1) Install Python dependencies:
   - `pip install -r requirements.txt`
   - For development: `pip install -r requirements_dev.txt`
2) Install FontForge (needed for `nerdify.py` only):
   - Debian/Ubuntu: run `./requirements.sh` (uses `apt install fontforge`).
   - macOS (Homebrew): `brew install fontforge`.
   - Windows: install FontForge from the official distribution.

Optional cache/config
- `nerdify.py` downloads `FontPatcher.zip` on first run by default. You can point to an existing patcher with `--fontpatcher-dir /path/to/FontPatcher` to avoid network access.

## Workflow Usage

End‑to‑end example from raw fonts to a collection:

1) Normalize internal names from filenames
   - Command: `python nameadjust.py ./fonts -o ./out/named`
   - Effect: writes copies of `.ttf` files with cleaned internal names and filename stems like `Family-Style.ttf`.

2) Patch with Nerd Fonts glyphs
   - Command: `python nerdify.py ./out/named -o ./out/patched`
   - Notes: requires `fontforge`. Downloads and caches `FontPatcher.zip` unless you pass `--fontpatcher-dir`.

3) Generate standard weight instances (variable TTFs)
   - Command: `python weightadjust.py ./out/patched -w +10 -o ./out/weights`
   - Behavior: produces nine standard weights (Thin→Black). With `--weight-offset`, shifts numeric values while clamping to the font’s supported `wght` range.

4) Create a TTC/OTC collection
   - Command (auto type): `python createcollection.py ./out/weights -o ./out`
   - Command (forced type/name): `python createcollection.py ./out/weights --type ttc --name MyFamily -o ./out`
   - Output: `./out/MyFamily.ttc` (or OTC for OTF inputs), with fonts ordered by OS/2 weight (ascending) and Roman before Italic.

## CLI Reference (concise)

`nerdify.py`
- Description: Patch fonts with Nerd Fonts glyphs via Font Patcher.
- Usage: `python nerdify.py [PATHS ...] -o OUTDIR [--fontpatcher-dir DIR] [--cache-dir DIR]`
- Notes: Supports `.ttf`, `.otf`, `.ttc`; traverses directories recursively; requires `fontforge`.

`nameadjust.py`
- Description: Humanize filename → update name table (IDs 1/2/4/6).
- Usage: `python nameadjust.py [PATHS ...] [-o OUTDIR]`
- Notes: `.ttf` only; without `-o` updates in place (renaming the file to `Family-Style.ttf` if needed).

`weightadjust.py`
- Description: Produce standard weights from variable TTFs; optional numeric offset.
- Usage: `python weightadjust.py [PATHS ...] [-w OFFSET] [-o OUTDIR]`
- Notes: `.ttf` only; clamps to the font’s supported `wght` range; rewrites internal names in outputs.
  - Output names: `<stem>-<WeightName>.ttf`; with offset: `<stem>-<WeightName>-<Resolved>.ttf`.
  - Weights table comes from `fontweights.toml` (see `docs/spec/fontweights/spec.md`).

`createcollection.py`
- Description: Create TTC/OTC from `.ttf` or `.otf` inputs.
- Usage: `python createcollection.py [PATHS ...] [-o OUTDIR] [--type {ttc,otc}] [--name NAME] [--dry-run]`
- Notes: Infers type from inputs (all TTF → TTC, all OTF → OTC), or force with `--type`. Expects inputs to have names normalized by `nameadjust.py`; when not unanimous, uses a minimal filename-based basename heuristic.

## Development

- Tests: `pytest -q` (configured for coverage and parallel collection).
- Lint: `ruff check <files>` and `flake8 <files>`.
- Format: `black <files>`.
- Specs: see `docs/spec/` for human‑readable specs and implementation notes.

## Safety & Behavior

- Commands write only to the specified `-o/--output` directories (or in place where documented).
- Network access is only used by `nerdify.py` to fetch `FontPatcher.zip` unless `--fontpatcher-dir` is provided.
- Filenames and internal names are sanitized conservatively for cross‑platform safety.
