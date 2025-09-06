Font Patcher
===

## Description

A nerd font patcher script.

## Usage

nerdify.py [font file or path to font files...] [-o Output dir]

## Behavior

Essentially this script just automates the ff. manual steps:

- Requires fontforge installed or tells the user to install it (see: requirements.sh)
- Requires the FontPatcher.zip or downloads it
  (https://github.com/ryanoasis/nerd-fonts/releases/latest/download/FontPatcher.zip)
- Download and extract the FontPatcher.zip
- Run the ff. command for each font file:
  ```
  fontforge -script <path/to/FontPatcher/font-patcher> <path/to/font file>
  ```

However with this script we should be able to:

- Always have the latest FontPatcher.zip
- Traverse several input directories for font files
- By default saves the patched fonts where the script was run or in the
  set output dir
