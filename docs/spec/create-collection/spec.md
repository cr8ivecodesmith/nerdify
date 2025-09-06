Create Collection
=================

Description
-----------
Create a TTC/OTC collection from a set of fonts, ordering by weight and style using a configurable weight table.

Config Dependency
-----------------
- Requires `fontweights.toml`; see `docs/spec/fontweights/spec.md`.
- Uses canonical names and aliases to parse weight phrases from internal names or filename tokens.

Behavior
--------
- Determines collection type (TTC/OTC) from inputs.
- Derives collection basename from internal family names or filename token prefixes, stripping style tokens using the config.
- Sorts fonts by numeric weight (ascending), then Roman before Italic, then by name.

Constraints
-----------
- Missing/invalid `fontweights.toml`: fail with a clear error.

