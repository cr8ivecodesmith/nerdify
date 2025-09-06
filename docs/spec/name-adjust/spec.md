Name Adjust
==========

Description
-----------
Rewrite internal font names (family/subfamily, PS name) based on a humanized filename and a configurable weight table.

Config Dependency
-----------------
- Requires `fontweights.toml`; see `docs/spec/fontweights/spec.md`.
- Uses canonical names and aliases to recognize base weight phrases when splitting Family/Subfamily and to infer numeric weight/italic flags.

Behavior
--------
- Humanizes the filename stem, then splits into Family and Subfamily where Subfamily is a recognized weight phrase with optional "Italic" modifier.
- Uses canonical weight names for composing output filenames and internal name records.
- Infers `usWeightClass` and italic flag from Subfamily via the fontweights mapping.

Constraints
-----------
- Input fonts: `.ttf`.
- Missing/invalid `fontweights.toml`: fail with a clear error.

