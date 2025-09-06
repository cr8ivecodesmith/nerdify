Create Collection — Implementation
=================================

Integration with fontweights
----------------------------
- Load config with `common.fontweights.load_config()` when parsing names or tokens.
- Replace the hardcoded `WEIGHT_MAP` with lookups via `lookup_value(cfg, phrase)`.
- In `strip_style_tokens`, drop tokens that form recognized weight phrases (single or two-word) based on the config, as well as `Italic/Oblique` tokens.
- In `weight_and_style_from_names`, prefer subfamily, then family, then filename tokens; use config to resolve numeric weight and detect italic tokens as before.

Error Handling
--------------
- If config cannot be loaded, raise `RuntimeError` and abort.

Testing
-------
- Add unit tests to ensure that alias phrases (e.g., "Ultra Light") resolve to the expected numeric weight and that token stripping removes weight and italic markers using a temp `fontweights.toml`.

