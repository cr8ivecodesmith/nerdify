Name Adjust — Implementation
===========================

Integration with fontweights
----------------------------
- Load config with `common.fontweights.load_config()` at operation time.
- Build a base style phrase set from canonical names and aliases, normalizing hyphens to spaces for matching against humanized tokens.
- Use this set in `split_family_subfamily` to detect the rightmost weight phrase; append "Italic" when present.
- Use `lookup_value(cfg, phrase)` in `_infer_weight_and_italic_from_subfamily` (after stripping "Italic"). If no match, weight is `None`; italic detection remains unchanged.

API Changes
-----------
- Keep public function signatures stable; resolve config internally to avoid wide refactors.
- Keep functions pure where feasible; only the parts that require config will read it on demand.

Error Handling
--------------
- If config cannot be loaded, raise `RuntimeError` and abort.

Testing
-------
- Add tests to ensure alias phrases (e.g., "Ultra Light") are recognized for both splitting and weight inference when a temp `fontweights.toml` is provided.

