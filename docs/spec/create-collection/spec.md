Create Collection
=================

Description
-----------
Create a TTC/OTC collection from a set of fonts. Inputs are expected to have already had their internal names normalized by the adjust‑naming step.

Config Dependency
-----------------
- None. This tool does not parse or infer weight/style from names or filenames.

Behavior
--------
- Determines collection type (TTC/OTC) from inputs.
 - Derives collection basename from a consensus Typographic Family (name ID 16). If no single non‑empty family is shared across inputs, applies a minimal filename heuristic: tokenize stems, drop only obvious non‑family markers (Italic/Oblique, VF/Variable/Var, version‑like tokens), take the common token prefix, and join preserving the first filename’s casing. If that yields nothing, fall back to the parent directory name of the first font (or its stem). `--name` overrides both.
- Sorts fonts by OS/2 `usWeightClass` (ascending), then Roman before Italic (using OS/2 `fsSelection` or head `macStyle`), then by filename as a tiebreaker.

Constraints
-----------
- This tool does not modify name tables and does not apply naming heuristics. Run adjust naming beforehand for consistent names.
