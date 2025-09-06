Weight Adjust
===

## Description

A variable font weight adjustment tool.

## Usage

weightadjust.py [font file or path to font files...] [-w, --weight-offset Weight offset] [-o Output dir]

## Behavior

Essentially this script just automates the ff. manual steps:

- Requires fonttools installed or tells the user to install it (see: requirements.txt)
- Run the ff. command for each font file:
  ```
  fonttools varLib.mutator "<font file>" wght=<weight> -o "<font filename>-<weight name>-<weight>.<ext>"
  ```

However with this script we should be able to:

- Traverse several input directories for font files
- By default saves the re-weighed fonts where the script was run or in the
  set output dir.
- Font output filename will be "<primary name>-<weight name>-<weight>.<ext>"
  - The resolved `<weight>` value will only be appended if the weight offset is adjusted.
  - The weight offset allows for "+/-" of numeric values (i.e. +10, -10)
- Each font will be created for each weight types in the weights table.
  - If we find a font named `CoolFontRegular.ttf` then the ff. fonts will be
    created:
    - CoolFont-Thin.ttf
    - CoolFont-Extra-Light.ttf
    - CoolFont-Medium.ttf
    - CoolFont-Regular.ttf
    - etc

Weights Table:

| Numeric Value | Name (Common Usage)       | Notes                              |
| ------------- | ------------------------- | ---------------------------------- |
| **100**       | Thin                      | Ultra Light                        |
| **200**       | Extra-Light               | Slightly thicker than Thin         |
| **300**       | Light                     |                                    |
| **400**       | Regular                   | Sometimes called “Book” or “Roman” |
| **500**       | Medium                    |                                    |
| **600**       | Semi-Bold                 |                                    |
| **700**       | Bold                      | The most common “bold”             |
| **800**       | Extra-Bold                |                                    |
| **900**       | Black                     | Sometimes “Fat”                    |

Notes:

- Only ttf files are supported.
