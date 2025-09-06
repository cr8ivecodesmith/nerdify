Name Adjust
===

## Description

A font name normalization tool that updates a TTF’s internal Full Name (and related name table records) based on a humanized form of its filename. Tokens are split on underscores and hyphens, converted to Title Case where appropriate, and common technical suffixes (e.g., "VF") are removed. Example:

- PragmataProMonoVF_liga_0902-Extra-bold-NerdFont → PragmataProMono Liga 0902 Extra Bold NerdFont

## Usage

nameadjust.py [font file or path to font files ...] [-o Output dir]

## Behavior

Essentially this script automates the following steps:

- Requires fonttools; if missing, instruct the user to install it (see: requirements.txt).
- Discovers `.ttf` files from provided files/dirs (recursive) and processes them deterministically.
- For each font file, computes a Humanized name from the filename stem and writes it into the font’s name table:
  - Full Name (nameID 4): set to the Humanized name.
  - PostScript Name (nameID 6): Humanized name with spaces removed and a hyphen between family and style when derivable.
  - Family (nameID 1) and Subfamily (nameID 2): best‑effort split where style/weight tokens are present; otherwise Subfamily defaults to Regular.
- Output location:
  - By default, updates the font file in place.
  - If `-o` is provided, writes a copy to the output directory using the original filename, but with updated internal names.

## Humanization Rules

- Split on underscores (`_`) and hyphens (`-`); join with single spaces in the result.
- Title‑case lower/uppercase words (e.g., `extra-bold` → `Extra Bold`).
- Preserve CamelCase tokens as‑is (e.g., `PragmataProMono`, `NerdFont`).
- Preserve numeric tokens (e.g., `0902`).
- Remove common variable‑font markers when standalone or trailing a family token: `VF`.
- Normalize known style synonyms to Title Case (e.g., `bold` → `Bold`, `regular` → `Regular`, `italic` → `Italic`).
- Collapse excess whitespace; strip leading/trailing spaces.

Heuristics for family vs subfamily (style):

- If the last one or two tokens are recognized style/weight words (e.g., Regular, Bold, Extra Bold, Italic), assign them to Subfamily and the preceding tokens to Family.
- Otherwise, Family is the entire Humanized name and Subfamily defaults to Regular.

## Examples

- Input filename: `PragmataProMonoVF_liga_0902-Extra-bold-NerdFont.ttf`
  - Humanized: `PragmataProMono Liga 0902 Extra Bold NerdFont`
  - Family/Subfamily (best‑effort): Family=`PragmataProMono Liga 0902 NerdFont`, Subfamily=`Extra Bold`

- Input filename: `CoolFont-regular.ttf`
  - Humanized: `CoolFont Regular`
  - Family/Subfamily: Family=`CoolFont`, Subfamily=`Regular`

- Input filename: `my_font-VF-italic.ttf`
  - Humanized: `My Font Italic`
  - Family/Subfamily: Family=`My Font`, Subfamily=`Italic`

## Notes

- Only `.ttf` files are supported.
- The script does not rename files; it updates internal font names. When `-o` is used, the filename is preserved and a copy is written to the output directory.
- The humanization is heuristic-based and intentionally conservative to avoid breaking CamelCase branding.

