Name Adjust
===

## Description

A font name normalization tool that rewrites a font’s name table to align with the Collection Naming Playbook (`docs/spec/font-collection/spec-naming.md`). It derives a Humanized form of the filename and sets the key name IDs and style flags so apps group and link styles correctly. Example:

- PragmataProMonoVF_liga_0902-Extra-bold-NerdFont → PragmataProMono Liga Extra Bold NerdFont

## Usage

nameadjust.py [font file or path to font files ...] [-o Output dir]

## Behavior

Essentially this script automates the following steps:

- Requires fonttools; if missing, instruct the user to install it (see: requirements.txt).
- Discovers `.ttf` files from provided files/dirs (recursive) and processes them deterministically.
- For each font file, computes a Humanized name from the filename stem, splits it into Family and Subfamily, and updates name/flag fields:
  - Name table:
    - Typographic Family (nameID 16) = Family
    - Typographic Subfamily (nameID 17) = Subfamily
    - Legacy Family (nameID 1) = Family
    - Legacy Subfamily (nameID 2) = Subfamily (default `Regular` when no style tokens)
    - Full Name (nameID 4) = `Family Subfamily`
    - PostScript Name (nameID 6) = `Family-Subfamily` ASCII, spaces removed
    - Provide Windows/Unicode (3,1,0x409) records at minimum; may also write Mac (1,0,0)
  - Style flags and metrics:
    - OS/2.usWeightClass = 100–900 per Subfamily (Thin→Black)
    - OS/2.fsSelection bits: set ITALIC for italic styles; set BOLD only for “Bold”; set REGULAR only on upright Regular
    - head.macStyle bits: set Bold/Italic to match
- Output location:
  - By default, updates the font file in place.
  - If `-o` is provided, writes a copy to the output directory using the cleaned filename derived from `Family-Subfamily`.

## Humanization Rules

- Split on underscores (`_`) and hyphens (`-`); join with single spaces in the result.
- Title‑case lower/uppercase words (e.g., `extra-bold` → `Extra Bold`).
- Preserve CamelCase tokens as‑is (e.g., `PragmataProMono`, `NerdFont`).
- Preserve numeric tokens (e.g., `0902`).
- Remove common variable‑font markers when standalone or trailing a family token: `VF`.
- Normalize known style synonyms to Title Case (e.g., `bold` → `Bold`, `regular` → `Regular`, `italic` → `Italic`).
- Collapse excess whitespace; strip leading/trailing spaces.

Heuristics for family vs subfamily (style):

- Recognize typical weight/style phrases: `Thin`, `Extra Light`, `Light`, `Regular`, `Medium`, `Semi Bold`, `Bold`, `Extra Bold`, `Black`, and italic variants (e.g., `Italic`, `Bold Italic`).
- If the trailing tokens form a recognized style phrase, assign them to Subfamily and the preceding tokens to Family.
- Otherwise, Family is the entire Humanized name and Subfamily defaults to `Regular`.

## Examples

- Input filename: `PragmataProMonoVF_liga_0902-Extra-bold-NerdFont.ttf`
  - Humanized: `PragmataProMono Liga Extra Bold NerdFont` (drops version token `0902`)
  - Family/Subfamily (best‑effort): Family=`PragmataProMono Liga NerdFont`, Subfamily=`Extra Bold`

- Input filename: `CoolFont-regular.ttf`
  - Humanized: `CoolFont Regular`
  - Family/Subfamily: Family=`CoolFont`, Subfamily=`Regular`

- Input filename: `my_font-VF-italic.ttf`
  - Humanized: `My Font Italic`
  - Family/Subfamily: Family=`My Font`, Subfamily=`Italic`

## Notes

- Only `.ttf` files are supported.
- When `-o` is used, a cleaned filename is used for the copy: `<Family>-<Subfamily>.ttf` with spaces replaced by underscores.
- The humanization is heuristic-based and intentionally conservative to avoid breaking CamelCase branding.

Alignment with Playbook
-----------------------
- Mirrors the recommendations in `spec-naming.md`:
  - IDs 16/17/1/2/4/6 aligned and unique per face
  - Weight/italic flags consistent across OS/2.fsSelection and head.macStyle
  - Strict Bold detection (do not infer from Medium/600)
