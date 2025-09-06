from __future__ import annotations

from pathlib import Path
import pytest


def _write_cfg(tmp_path: Path):
    (tmp_path / "fontweights.toml").write_text(
        """
        [weights]
        Thin = 100
        "Extra-Light" = 200
        Regular = 400
        Bold = 700

        [aliases]
        "Ultra Light" = "Extra-Light"
        """,
        encoding="utf-8",
    )


def test_strip_style_tokens_and_weight_lookup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    import createcollection as cc

    monkeypatch.chdir(tmp_path)
    _write_cfg(tmp_path)

    tokens = ["cool", "ultra", "light", "italic"]
    stripped = cc.strip_style_tokens(tokens)
    assert stripped == ["cool"]

    # weight from names
    w, it = cc.weight_and_style_from_names("Cool", "Ultra Light Italic", "Cool-Ultra-Light-Italic")
    assert w == 200 and it is True

    # fallback to tokens if names missing
    w2, it2 = cc.weight_and_style_from_names(None, None, "Cool-Ultra-Light-Italic")
    assert w2 == 200 and it2 is True

